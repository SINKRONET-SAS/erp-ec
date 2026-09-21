"""Regularización de un documento de exención entregado después del 15 de enero (DI25-03, D2).

El pronunciamiento fija el procedimiento: validación, fecha de efecto, recálculo de las retenciones futuras
y conciliación en la declaración anual; sin aplicación retroactiva sobre nóminas cerradas y sin excepciones
sin fundamento. Este expediente es ese procedimiento: registra el fundamento (criterio formal del responsable
tributario o pronunciamiento del SRI), la validación realizada y la fecha desde la que surte efecto, que nunca
puede caer en un mes ya contabilizado. Lo verifica una persona distinta de quien lo registra. Verificado y vigente,
el documento tardío se trata como entregado en plazo desde esa fecha; el recálculo de las retenciones futuras
lo hace la reliquidación acumulada (D6) y la conciliación anual queda visible en el anexo RDEP.
"""
from calendar import monthrange
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .engine import EXEMPTION_DEADLINE
from .models import _INTERNAL, manager

FROZEN = {'company_id', 'employee_id', 'year', 'document_ref', 'delivered_date', 'validation_note', 'effect_date', 'criterion_reference'}
GUARDED = {'state', 'verified_by', 'verified_at'}


class ExemptionRegularization(models.Model):
    _name = 'erpec.payroll.exemption.regularization'
    _description = 'Regularización de documento de exención tardío'
    _inherit = ['mail.thread']
    _order = 'year desc, employee_id, effect_date'

    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company, index=True)
    employee_id = fields.Many2one('hr.employee', 'Trabajador', required=True, index=True)
    year = fields.Integer('Ejercicio fiscal', required=True)
    document_ref = fields.Char('Referencia del documento tardío', required=True,
                               help='Debe coincidir con la referencia registrada en la ficha del trabajador.')
    delivered_date = fields.Date('Fecha de entrega al empleador', required=True,
                                 help='Debe coincidir con la fecha de la ficha y ser posterior al 15 de enero del ejercicio.')
    validation_note = fields.Text('Validación realizada', required=True,
                                  help='Qué se verificó del documento y con quién; sin diagnósticos ni datos de salud.')
    criterion_reference = fields.Char('Fundamento de la regularización', required=True,
                                      help='Criterio formal del responsable tributario o pronunciamiento del SRI que la respalda.')
    effect_date = fields.Date('Surte efecto desde', required=True,
                              help='Primer día desde el que se aplica. Debe ser posterior al último mes contabilizado: nunca es retroactivo.')
    state = fields.Selection([('draft', 'Borrador'), ('verified', 'Verificada'), ('revoked', 'Revocada')], 'Estado',
                             default='draft', readonly=True, copy=False, index=True)
    verified_by = fields.Many2one('res.users', 'Verificada por', readonly=True, copy=False)
    verified_at = fields.Datetime('Verificada el', readonly=True, copy=False)
    revoked_reason = fields.Text('Motivo de la revocación', copy=False)

    @api.model
    def _last_closed_day(self, employee, year):
        """Último día del último mes ya contabilizado para el trabajador en el ejercicio (None si no hay)."""
        lines = self.env['erpec.payroll.line'].sudo().search([
            ('employee_id', '=', employee.id), ('period_id.state', '=', 'posted'), ('period_id.year', '=', year)])
        if not lines:
            return None
        month = max(lines.mapped('period_id.month'))
        return date(year, month, monthrange(year, month)[1])

    @api.constrains('year', 'delivered_date', 'effect_date', 'employee_id', 'company_id')
    def _check_regularization(self):
        for record in self:
            if not 2000 <= record.year <= 2100:
                raise ValidationError('El ejercicio de la regularización no es válido.')
            if record.employee_id.company_id != record.company_id:
                raise ValidationError('El trabajador pertenece a otra empresa.')
            if (record.delivered_date.month, record.delivered_date.day) <= EXEMPTION_DEADLINE and record.delivered_date.year == record.year:
                raise ValidationError('El documento se entregó en plazo (hasta el 15 de enero): no requiere regularización.')
            if record.delivered_date.year != record.year or (record.delivered_date > fields.Date.today() and record.year <= fields.Date.today().year):
                raise ValidationError('La entrega debe ser del ejercicio %s y no puede ser futura.' % record.year)  # ejercicios futuros solo en ensayos
            if record.effect_date < record.delivered_date or record.effect_date.year != record.year:
                raise ValidationError('La fecha de efecto va desde la entrega hasta el cierre del ejercicio %s.' % record.year)
            if record.state == 'draft':
                closed = self._last_closed_day(record.employee_id, record.year)
                if closed and record.effect_date <= closed:
                    raise ValidationError('La regularización no es retroactiva: debe surtir efecto después de %s, último mes contabilizado.' % closed)

    # ── Inmutabilidad ─────────────────────────────────────────────────────
    def write(self, values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            if any(record.state != 'draft' for record in self) and set(values) & (FROZEN | {'state'}):
                raise ValidationError('Una regularización verificada o revocada no se edita: revócala y registra otra.')
            guarded = set(GUARDED)
            if not all(record.state == 'verified' for record in self):
                guarded.add('revoked_reason')
            if set(values) & guarded:
                raise ValidationError('El estado y la verificación se cambian solo con sus acciones.')
        return super().write(values)

    @api.model_create_multi
    def create(self, values_list):
        manager(self.env)
        if any(set(values) & (GUARDED | {'revoked_reason'}) for values in values_list):
            raise ValidationError('El estado y la verificación se cambian solo con sus acciones.')
        return super().create(values_list)

    def unlink(self):
        if any(record.state != 'draft' for record in self):
            raise ValidationError('Una regularización verificada o revocada no se elimina; revócala con su motivo.')
        return super().unlink()

    # ── Verificación ─────────────────────────────────────────────────────
    def action_verify(self):
        manager(self.env)
        for record in self:
            if record.state != 'draft':
                raise ValidationError('Solo se verifica una regularización en borrador.')
            if record.create_uid == self.env.user:
                raise ValidationError('La verificación la hace otra persona distinta de quien registró la regularización (segregación de funciones).')
            employee = record.employee_id.sudo()
            if employee.ec_rdep_exemption_ref != record.document_ref or employee.ec_rdep_exemption_date != record.delivered_date \
                    or employee.ec_rdep_exemption_year != record.year:
                raise ValidationError('El documento, su fecha de entrega o el ejercicio no coinciden con los de la ficha del trabajador.')
            closed = self._last_closed_day(record.employee_id, record.year)
            if closed and record.effect_date <= closed:
                raise ValidationError('La regularización ya no es válida: debe surtir efecto después de %s, último mes contabilizado.' % closed)
            record.with_context(_erpec_payroll_token=_INTERNAL).write({'state': 'verified', 'verified_by': self.env.user.id, 'verified_at': fields.Datetime.now()})
            record.message_post(body='Regularización verificada por %s; surte efecto desde %s. Fundamento: %s.' % (
                self.env.user.name, record.effect_date, record.criterion_reference))
        return True

    def action_revoke(self):
        manager(self.env)
        for record in self:
            if record.state != 'verified':
                raise ValidationError('Solo se revoca una regularización verificada.')
            reason = (record.revoked_reason or '').strip() or 'Revocada por %s.' % self.env.user.name
            record.with_context(_erpec_payroll_token=_INTERNAL).write({'state': 'revoked', 'revoked_reason': reason})
            record.message_post(body='Regularización revocada: ' + reason)
        return True

    # ── Consulta para el motor ───────────────────────────────────────────
    @api.model
    def standing(self, employee, year, as_of=None):
        """Situación del documento tardío: 'effective' si ya surte efecto, 'pending' si está verificado pero surte efecto
        después de la fecha de corte, None si no hay regularización verificada de ese documento."""
        cutoff = as_of or date(year, 12, 31)
        records = self.search([
            ('employee_id', '=', employee.id), ('year', '=', year), ('state', '=', 'verified'),
            ('document_ref', '=', employee.ec_rdep_exemption_ref), ('delivered_date', '=', employee.ec_rdep_exemption_date)])
        if not records:
            return None
        return 'effective' if any(record.effect_date <= cutoff for record in records) else 'pending'
