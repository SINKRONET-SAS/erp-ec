"""Asistente de rotación de la clave maestra de secretos: inventario por clave y re-cifrado completo."""
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .. import secret_store


class SecretRotation(models.TransientModel):
    _name = 'erpec.secret.rotation'
    _description = 'Rotación de claves de secretos cifrados'

    key_source = fields.Char('Origen de la clave vigente', compute='_compute_inventory')
    current_key_id = fields.Char('Id de la clave vigente', compute='_compute_inventory')
    previous_keys = fields.Integer('Claves anteriores conocidas', compute='_compute_inventory')
    inventory = fields.Text('Secretos guardados por clave', compute='_compute_inventory')
    pending = fields.Integer('Secretos con una clave distinta de la vigente', compute='_compute_inventory')
    result = fields.Text('Resultado', readonly=True)

    def _check_admin(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Solo un administrador del sistema puede gestionar las claves de secretos.')

    def _inventory(self):
        """[(modelo, campo, {id de clave: cantidad})]; nunca lee ni muestra los secretos."""
        report = []
        for (model, field), _context in sorted(secret_store.REGISTRY.items()):
            if model not in self.env:
                continue
            table = self.env[model]._table
            self.env.cr.execute('SELECT %(f)s FROM %(t)s WHERE %(f)s IS NOT NULL AND %(f)s <> \'\'' % {'f': field, 't': table})
            counts = {}
            for (token,) in self.env.cr.fetchall():
                kid = secret_store.token_key_id(token) or 'inválido'
                counts[kid] = counts.get(kid, 0) + 1
            report.append((model, field, counts))
        return report

    @api.depends()
    def _compute_inventory(self):
        for wizard in self:
            current = secret_store.current_key_id()
            report = wizard._inventory() if self.env.user.has_group('base.group_system') else []
            wizard.key_source = secret_store.key_source()
            wizard.current_key_id = current
            wizard.previous_keys = len(secret_store.known_keys()) - 1
            wizard.pending = sum(count for _m, _f, counts in report for kid, count in counts.items() if kid != current)
            wizard.inventory = '\n'.join('%s.%s: %s' % (model, field, ', '.join(
                '%s%s = %d' % (kid, ' (vigente)' if kid == current else '', count) for kid, count in sorted(counts.items())) or 'sin datos')
                for model, field, counts in report) or 'No hay secretos registrados.'

    def reencrypt_all(self):
        """Re-cifra todos los secretos con la clave vigente. Antes descifra TODOS en memoria: si alguno no se puede
        descifrar (falta una clave anterior) no se modifica nada. Devuelve la cantidad re-cifrada."""
        self._check_admin()
        plans = []
        failures = []
        for (model, field), context in sorted(secret_store.REGISTRY.items()):
            if model not in self.env:
                continue
            table = self.env[model]._table
            self.env.cr.execute('SELECT id, %(f)s FROM %(t)s WHERE %(f)s IS NOT NULL AND %(f)s <> \'\'' % {'f': field, 't': table})
            for record_id, token in self.env.cr.fetchall():
                record = self.env[model].sudo().browse(record_id)
                try:
                    plans.append((table, field, record_id, secret_store.decrypt(token, context(record)), context(record)))
                except secret_store.SecretError as error:
                    failures.append('%s.%s #%d: %s' % (model, field, record_id, error))
        if failures:
            raise ValidationError('No se re-cifró nada porque hay secretos que no se pueden descifrar:\n' + '\n'.join(failures))
        for table, field, record_id, plain, context in plans:
            self.env.cr.execute('UPDATE %s SET %s=%%s WHERE id=%%s' % (table, field), [secret_store.encrypt(plain, context), record_id])
        self.env.invalidate_all()
        return len(plans)

    def action_reencrypt(self):
        count = self.reencrypt_all()
        self.result = 'Re-cifrados %d secretos con la clave vigente %s.' % (count, secret_store.current_key_id())
        return self._reopen()

    def action_generate_and_reencrypt(self):
        self._check_admin()
        try:
            new_id = secret_store.rotate_key_file()
        except secret_store.SecretError as error:
            raise ValidationError(str(error)) from error
        count = self.reencrypt_all()
        self.result = ('Clave nueva %s generada (la anterior quedó en %s solo para descifrar). Re-cifrados %d secretos. '
                       'Cuando compruebes que todo funciona y no queda nada con la clave anterior, puedes retirarla.') % (
            new_id, secret_store.PREVIOUS_FILE, count)
        return self._reopen()

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new'}
