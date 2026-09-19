"""Emisión nativa real: firma XAdES + transmisión SOAP directa al SRI (ambiente PRUEBAS).
Segunda autoridad de emisión, independiente de erpec_fiscal_connector (que delega en un
servicio Facturador externo) — gobernada por la misma regla "una autoridad por comprobante"
que ya aplica en erpec_fiscal_native.models. Ver docs/PLAN_HAIKY_FACTURACION_NATIVA.md.

`_gather_native_data()` duplica intencionalmente una porción pequeña de la lógica de
`erpec_fiscal_native.models.Move.action_native_preview` (validación de líneas/IVA y armado del
diccionario para engine.generate()): ese archivo está en edición por otra sesión en paralelo al
escribir este incremento, así que no se pudo extraer a una función compartida. Consolidar en un
incremento posterior cuando el archivo esté libre.
"""
import base64
import hashlib
import re
import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.erpec_fiscal_native import xades
from odoo.addons.erpec_fiscal_native.engine import generate
from odoo.addons.erpec_fiscal_native import liquidacion_engine, notacredito_engine, notadebito_engine

from . import ride as ride_module
from . import secret_store

secret_store.register('erpec.fiscal.certificate', 'p12_encrypted', lambda record: 'cert:%d:p12' % record.id)
secret_store.register('erpec.fiscal.certificate', 'p12_password_encrypted', lambda record: 'cert:%d:password' % record.id)
from . import sri_client

NATIVE_MOVE_TYPES = ('out_invoice', 'out_refund')

_INTERNAL = object()
MAX_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 60
POLL_DELAY_SECONDS = 30

# Autoservicio de carga del .p12 (adaptado de sinkroniq-mobile, backend/src/services/certificados/
# certificateLifecycleService.js: allowlist de CAs conocidas para el SRI, tope de tamaño de
# archivo y límite de intentos de verificación). Odoo no tiene un servicio de firma separado ni
# Redis en este proyecto, así que el límite de intentos se guarda en el propio registro en vez de
# un contador externo, y la "vista previa" se resuelve con un @api.onchange (corre en el cliente
# antes de guardar) en vez de un endpoint aparte.
MAX_P12_BYTES = 262144
MAX_VERIFY_ATTEMPTS = 5
VERIFY_WINDOW_MINUTES = 15
TRUSTED_CA_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    r'security\s*data', r'banco\s*central\s*del?\s*ecuador', r'\bbce\b', r'\banf\s*ac\b',
    r'uanataca', r'datil', r'consejo\s*de\s*la\s*judicatura',
)]
SIGNATURE_PROBE_XML = (
    b'<factura id="comprobante" version="2.1.0"><infoTributaria><ambiente>1</ambiente>'
    b'<tipoEmision>1</tipoEmision><razonSocial>PRUEBA FIRMA ELECTRONICA</razonSocial>'
    b'<ruc>%(ruc)s</ruc><claveAcceso>' + b'0' * 49 + b'</claveAcceso><codDoc>01</codDoc>'
    b'<estab>001</estab><ptoEmi>001</ptoEmi><secuencial>000000000</secuencial>'
    b'<dirMatriz>PRUEBA</dirMatriz></infoTributaria></factura>'
)


class Journal(models.Model):
    _inherit = 'account.journal'

    ec_sri_ambiente = fields.Selection(
        [('1', 'Pruebas'), ('2', 'Producción')], string='Ambiente SRI', default='1', required=True,
        help='El SRI lleva secuenciales independientes por ambiente: los comprobantes de pruebas y de producción '
             'no pueden compartir numeración. Cada ambiente usa su propio diario (y por tanto su propio consecutivo).')
    ec_point_id = fields.Many2one('erpec.fiscal.point', string='Punto de emisión SRI', check_company=True, ondelete='restrict',
                                  help='Establecimiento y punto de emisión al que pertenece este diario.')

    @api.constrains('ec_point_id', 'l10n_ec_entity', 'l10n_ec_emission')
    def _check_point_numbers(self):
        for journal in self.filtered('ec_point_id'):
            point = journal.ec_point_id
            if journal.type == 'sale' and (journal.l10n_ec_entity, journal.l10n_ec_emission) != (point.establishment, point.emission):
                raise ValidationError('El establecimiento y el punto de emisión del diario deben coincidir con los del punto de emisión SRI.')

    def _sri_check_ambiente(self):
        """Ambiente en el que puede emitir este diario, o error. Producción solo desde un punto de
        emisión habilitado explícitamente; el ambiente del diario debe coincidir con el del punto."""
        self.ensure_one()
        ambiente = self.ec_sri_ambiente or '1'
        point = self.ec_point_id
        if point and point.ambiente != ambiente:
            raise ValidationError('Este diario es de %s pero el punto de emisión %s-%s está en %s; usa el diario de %s.' % (
                AMBIENTE_NAMES[ambiente], point.establishment, point.emission, AMBIENTE_NAMES[point.ambiente], AMBIENTE_NAMES[point.ambiente]))
        if ambiente == '2' and not (point and point.production_acknowledged):
            raise ValidationError('La emisión en producción requiere un punto de emisión habilitado para producción '
                                  '(Facturación electrónica > Establecimientos y puntos de emisión).')
        return ambiente


AMBIENTE_NAMES = {'1': 'pruebas', '2': 'producción'}
_POINT_INTERNAL = object()


class Establishment(models.Model):
    """Establecimiento (local o sucursal registrado en el RUC). Modelo padre de los puntos de emisión (cajas):
    la dirección se registra una sola vez y sale como dirEstablecimiento en los comprobantes. Diseño alineado con
    Establishment/EmissionPoint de sinkroniq-mobile (principal, activo, protección de borrado)."""
    _name = 'erpec.fiscal.establishment'
    _description = 'Establecimiento (SRI)'
    _check_company_auto = True
    _order = 'company_id, code'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict')
    code = fields.Char('Código', size=3, required=True, help='Código de 3 dígitos del establecimiento registrado en el RUC (001 es normalmente la matriz).')
    name = fields.Char('Nombre', required=True, help='Por ejemplo: PRINCIPAL o Sucursal Norte.')
    address = fields.Char('Dirección', required=True, help='Se imprime como dirEstablecimiento en los comprobantes de sus puntos de emisión.')
    is_principal = fields.Boolean('Establecimiento principal', help='Se propone por defecto cuando el usuario no tiene punto de emisión.')
    active = fields.Boolean(default=True)
    point_ids = fields.One2many('erpec.fiscal.point', 'establishment_id', string='Puntos de emisión')
    _sql_constraints = [('code_unique', 'unique(company_id,code)', 'Ya existe un establecimiento con este código en la empresa.')]

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if not re.fullmatch(r'[0-9]{3}', record.code or '') or int(record.code) == 0:
                raise ValidationError('El código del establecimiento requiere tres dígitos (001 a 999).')

    def _unset_other_principals(self):
        for record in self.filtered('is_principal'):
            others = self.search([('company_id', '=', record.company_id.id), ('is_principal', '=', True), ('id', '!=', record.id)])
            if others:
                others.with_context(_fiscal_establishment_internal=True).write({'is_principal': False})

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            company = values.get('company_id') or self.env.company.id
            if 'is_principal' not in values and not self.search_count([('company_id', '=', company)]):
                values['is_principal'] = True
        records = super().create(values_list)
        records._unset_other_principals()
        return records

    def write(self, values):
        if 'code' in values and any(record.point_ids and record.code != values['code'] for record in self):
            raise ValidationError('El código no se cambia cuando el establecimiento ya tiene puntos de emisión (los números de comprobante lo incluyen).')
        result = super().write(values)
        if values.get('is_principal') and not self.env.context.get('_fiscal_establishment_internal'):
            self._unset_other_principals()
        return result


class EmissionPoint(models.Model):
    _name = 'erpec.fiscal.point'
    _description = 'Establecimiento y punto de emisión (SRI)'
    _check_company_auto = True
    _order = 'company_id, establishment, emission'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict')
    establishment_id = fields.Many2one('erpec.fiscal.establishment', string='Establecimiento', check_company=True, ondelete='restrict',
                                       help='Local o sucursal al que pertenece la caja. Puedes crearlo desde aquí con su nombre y dirección.')
    establishment = fields.Char(related='establishment_id.code', store=True, readonly=True, string='Código de establecimiento')
    establishment_name = fields.Char(related='establishment_id.name', string='Nombre del establecimiento')
    establishment_address = fields.Char(related='establishment_id.address', string='Dirección del establecimiento')
    emission = fields.Char('Punto de emisión', size=3, required=True, help='Código de 3 dígitos de la caja o punto de venta dentro del establecimiento.')
    name = fields.Char('Nombre del punto de emisión', required=True, help='Por ejemplo: Caja 1.')
    ambiente = fields.Selection([('1', 'Pruebas'), ('2', 'Producción')], default='1', required=True, readonly=True,
                                string='Ambiente vigente', help='Se cambia con los botones de habilitación, no se edita directamente.')
    production_acknowledged = fields.Boolean('Producción habilitada por el responsable', readonly=True, copy=False)
    production_by = fields.Many2one('res.users', readonly=True, copy=False, string='Habilitado por')
    production_at = fields.Datetime(readonly=True, copy=False, string='Habilitado el')
    active = fields.Boolean(default=True)
    journal_ids = fields.One2many('account.journal', 'ec_point_id', string='Diarios (un consecutivo por ambiente)')
    notice = fields.Text(readonly=True, copy=False)
    _sql_constraints = [('point_unique', 'unique(company_id,establishment,emission)', 'Ya existe este establecimiento y punto de emisión en la empresa.')]

    @api.constrains('establishment_id')
    def _check_establishment(self):
        for point in self:
            if not point.establishment_id:
                raise ValidationError('Selecciona el establecimiento del punto de emisión.')

    @api.constrains('establishment', 'emission')
    def _check_codes(self):
        for point in self:
            for value in (point.establishment, point.emission):
                if not re.fullmatch(r'[0-9]{3}', value or '') or int(value) == 0:
                    raise ValidationError('Establecimiento y punto de emisión requieren tres dígitos (001 a 999).')

    def write(self, values):
        if any(key in values for key in ('ambiente', 'production_acknowledged', 'production_by', 'production_at', 'company_id')) \
                and self.env.context.get('_fiscal_point_internal') is not _POINT_INTERNAL:
            raise ValidationError('El ambiente se cambia con las acciones de habilitación.')
        if ('establishment_id' in values or 'emission' in values) and any(point.journal_ids for point in self):
            raise ValidationError('El establecimiento y el punto de emisión no se cambian cuando ya tienen diarios; crea un punto nuevo.')
        return super().write(values)

    def _next_sequence(self, kind):
        """Siguiente secuencial (9 dígitos) del punto para un tipo de comprobante propio (p. ej. 'liquidation'),
        en el ambiente vigente: pruebas y producción nunca comparten numeración."""
        self.ensure_one()
        code = 'erpec.fiscal.point.%s.%s.%s.%s' % (kind, self.ambiente, self.establishment, self.emission)
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', code), ('company_id', '=', self.company_id.id)], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': '%s %s-%s (%s)' % (kind, self.establishment, self.emission, AMBIENTE_NAMES[self.ambiente]),
                'code': code, 'company_id': self.company_id.id, 'padding': 9, 'number_next': 1, 'implementation': 'no_gap'})
        return '%s-%s-%s' % (self.establishment, self.emission, sequence.next_by_id())

    def _internal_write(self, values):
        return self.with_context(_fiscal_point_internal=_POINT_INTERNAL).write(values)

    def _ensure_journal(self):
        """Un diario de ventas por punto y ambiente: el consecutivo de pruebas nunca se reutiliza en producción.
        Antes de crear uno nuevo se ADOPTA un diario de ventas existente sin punto con el mismo establecimiento,
        punto de emisión y ambiente (así no se duplican diarios ni se pierde el historial de numeración)."""
        self.ensure_one()
        Journal = self.env['account.journal'].with_context(active_test=False)
        journal = Journal.search([('ec_point_id', '=', self.id), ('ec_sri_ambiente', '=', self.ambiente), ('type', '=', 'sale')], limit=1)
        if not journal:
            journal = Journal.search([('company_id', '=', self.company_id.id), ('type', '=', 'sale'), ('ec_point_id', '=', False),
                                      ('l10n_ec_entity', '=', self.establishment), ('l10n_ec_emission', '=', self.emission),
                                      ('ec_sri_ambiente', '=', self.ambiente)], limit=1)
            if journal:
                journal.write({'ec_point_id': self.id, 'l10n_latam_use_documents': True})
        if journal:
            if not journal.active:
                journal.active = True
            return journal
        prefix = 'FP' if self.ambiente == '1' else 'FR'
        number = 1
        while Journal.search_count([('company_id', '=', self.company_id.id), ('code', '=', '%s%03d' % (prefix, number))]):
            number += 1
        return self.env['account.journal'].create({
            'name': 'Facturación %s-%s %s (%s)' % (self.establishment, self.emission, self.name, AMBIENTE_NAMES[self.ambiente]),
            'code': '%s%03d' % (prefix, number), 'type': 'sale', 'company_id': self.company_id.id,
            'l10n_latam_use_documents': True, 'l10n_ec_entity': self.establishment, 'l10n_ec_emission': self.emission,
            'ec_point_id': self.id, 'ec_sri_ambiente': self.ambiente})

    def action_create_liquidation_journal(self):
        self.ensure_one()
        journal = self._ensure_liquidation_journal()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.journal', 'res_id': journal.id, 'view_mode': 'form'}

    def _ensure_liquidation_journal(self):
        """Diario de compras dedicado a las liquidaciones de compra del punto y ambiente vigente (el
        consecutivo lo asigna el sistema, a diferencia de las facturas de proveedores)."""
        self.ensure_one()
        Journal = self.env['account.journal'].with_context(active_test=False)
        journal = Journal.search([('ec_point_id', '=', self.id), ('ec_sri_ambiente', '=', self.ambiente), ('type', '=', 'purchase')], limit=1)
        if not journal:
            prefix = 'LP' if self.ambiente == '1' else 'LR'
            number = 1
            while Journal.search_count([('company_id', '=', self.company_id.id), ('code', '=', '%s%03d' % (prefix, number))]):
                number += 1
            journal = self.env['account.journal'].create({
                'name': 'Liquidaciones de compra %s-%s (%s)' % (self.establishment, self.emission, AMBIENTE_NAMES[self.ambiente]),
                'code': '%s%03d' % (prefix, number), 'type': 'purchase', 'company_id': self.company_id.id,
                'l10n_latam_use_documents': True, 'ec_point_id': self.id, 'ec_sri_ambiente': self.ambiente})
        elif not journal.active:
            journal.active = True
        return journal

    @api.model
    def migrate_journals(self, dry_run=True):
        """Lleva los diarios de ventas existentes (con establecimiento y punto de emisión) a puntos SRI, sin tocar
        comprobantes. Con dry_run=True solo informa. Casos: (1) sin punto equivalente: crea el punto si la empresa
        tiene dirección, si no queda 'requiere datos'; (2) punto existente cuyo diario propio está vacío: lo archiva y
        adopta el diario con historial; (3) ambos con movimientos: conflicto, no se toca."""
        if not self.env.user.has_group('account.group_account_manager'):
            raise ValidationError('Solo un responsable contable puede migrar diarios a puntos de emisión.')
        Journal = self.env['account.journal'].with_context(active_test=False)
        Move = self.env['account.move'].with_context(active_test=False)
        report = []
        candidates = Journal.search([('type', '=', 'sale'), ('ec_point_id', '=', False), ('l10n_ec_entity', '!=', False),
                                     ('l10n_ec_emission', '!=', False), ('l10n_latam_use_documents', '=', True)])
        for journal in candidates:
            entry = {'journal': '%s %s' % (journal.code, journal.name), 'company': journal.company_id.name,
                     'point': '%s-%s' % (journal.l10n_ec_entity, journal.l10n_ec_emission)}
            if not (re.fullmatch(r'[0-9]{3}', journal.l10n_ec_entity) and re.fullmatch(r'[0-9]{3}', journal.l10n_ec_emission)):
                report.append(dict(entry, action='omitido', detail='establecimiento o punto de emisión inválidos'))
                continue
            point = self.with_context(active_test=False).search([('company_id', '=', journal.company_id.id),
                                                                  ('establishment', '=', journal.l10n_ec_entity),
                                                                  ('emission', '=', journal.l10n_ec_emission)], limit=1)
            if not point:
                if not journal.company_id.street:
                    report.append(dict(entry, action='requiere datos', detail='la empresa no tiene dirección; crea el punto manualmente con su dirección de establecimiento'))
                    continue
                report.append(dict(entry, action='crear punto y adoptar diario', detail='dirección tomada de la empresa; revísala en el punto'))
                if not dry_run:
                    self.create({'company_id': journal.company_id.id, 'establishment': journal.l10n_ec_entity, 'emission': journal.l10n_ec_emission,
                                 'establishment_name': 'Establecimiento %s' % journal.l10n_ec_entity, 'establishment_address': journal.company_id.street,
                                 'name': 'Punto %s' % journal.l10n_ec_emission, 'ambiente': journal.ec_sri_ambiente})
                continue
            if point.ambiente != journal.ec_sri_ambiente:
                report.append(dict(entry, action='omitido', detail='el diario es de %s y el punto está en %s' % (AMBIENTE_NAMES[journal.ec_sri_ambiente], AMBIENTE_NAMES[point.ambiente])))
                continue
            own = Journal.search([('ec_point_id', '=', point.id), ('ec_sri_ambiente', '=', point.ambiente), ('type', '=', 'sale')], limit=1)
            if own and Move.search_count([('journal_id', '=', own.id)]):
                if Move.search_count([('journal_id', '=', journal.id)]):
                    report.append(dict(entry, action='conflicto', detail='el diario %s y el %s del punto tienen movimientos; requiere decisión manual' % (journal.code, own.code)))
                    continue
                report.append(dict(entry, action='omitido', detail='el punto ya tiene el diario %s con historial; %s queda sin punto' % (own.code, journal.code)))
                continue
            report.append(dict(entry, action='adoptar diario' + (' y archivar %s (sin movimientos)' % own.code if own else ''),
                               detail='se conservan los comprobantes y su numeración'))
            if not dry_run:
                if own:
                    own.write({'ec_point_id': False, 'active': False})
                journal.write({'ec_point_id': point.id})
        return report

    def action_import_from_journals(self):
        report = self.migrate_journals(dry_run=False)
        lines = ['%s [%s]: %s' % (item['journal'], item['point'], item['action']) for item in report] or ['No hay diarios de ventas por migrar.']
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Importación de diarios', 'message': '\n'.join(lines), 'sticky': True, 'type': 'info', 'next': {'type': 'ir.actions.client', 'tag': 'reload'}}}

    @api.model_create_multi
    def create(self, values_list):
        Establishment = self.env['erpec.fiscal.establishment']
        for values in values_list:
            # Compatibilidad: se acepta el código/nombre/dirección del establecimiento y se busca o crea el registro.
            if 'establishment_id' not in values and values.get('establishment'):
                company = values.get('company_id') or self.env.company.id
                establishment = Establishment.with_context(active_test=False).search([('company_id', '=', company), ('code', '=', values['establishment'])], limit=1)
                if not establishment:
                    establishment = Establishment.create({
                        'company_id': company, 'code': values['establishment'],
                        'name': values.get('establishment_name') or 'Establecimiento %s' % values['establishment'],
                        'address': values.get('establishment_address') or '-'})
                values['establishment_id'] = establishment.id
            for legacy in ('establishment', 'establishment_name', 'establishment_address'):
                values.pop(legacy, None)
        points = super().create(values_list)
        for point in points:
            point._ensure_journal()
        return points

    @api.model
    def audit_integrity(self):
        """Verificación de integridad de la configuración (equivalente a la auditoría de establecimientos de
        sinkroniq-mobile). Solo lectura: devuelve una lista de hallazgos, vacía si todo está bien."""
        Journal = self.env['account.journal'].with_context(active_test=False)
        findings = []
        for journal in Journal.search([('type', '=', 'sale'), ('active', '=', True), ('ec_point_id', '=', False), ('l10n_ec_entity', '!=', False),
                                       ('l10n_ec_emission', '!=', False), ('l10n_latam_use_documents', '=', True)]):
            findings.append('Diario de ventas %s (%s) con %s-%s sin punto de emisión SRI.' % (journal.code, journal.company_id.name, journal.l10n_ec_entity, journal.l10n_ec_emission))
        for point in self.with_context(active_test=False).search([]):
            active = Journal.search([('ec_point_id', '=', point.id), ('ec_sri_ambiente', '=', point.ambiente), ('type', '=', 'sale'), ('active', '=', True)])
            if not active:
                findings.append('El punto %s-%s (%s) no tiene diario de ventas activo en %s.' % (point.establishment, point.emission, point.company_id.name, AMBIENTE_NAMES[point.ambiente]))
            if len(active) > 1:
                findings.append('El punto %s-%s tiene %d diarios de ventas activos en el mismo ambiente.' % (point.establishment, point.emission, len(active)))
            if not point.establishment_id:
                findings.append('El punto %s (%s) no tiene establecimiento.' % (point.emission, point.company_id.name))
        for company in self.env['res.company'].search([]):
            establishments = self.env['erpec.fiscal.establishment'].search([('company_id', '=', company.id)])
            if establishments and not establishments.filtered('is_principal'):
                findings.append('La empresa %s tiene establecimientos pero ninguno principal.' % company.name)
        return findings

    def action_enable_production(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise ValidationError('Solo un responsable contable puede habilitar producción.')
        if self.ambiente == '2':
            return True
        certificate = self.env['erpec.fiscal.certificate'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not certificate or not certificate.verified or not certificate.issuer_trusted:
            raise ValidationError('Producción requiere el certificado de firma verificado y emitido por una entidad certificadora reconocida.')
        self._internal_write({'ambiente': '2', 'production_acknowledged': True, 'production_by': self.env.user.id,
                              'production_at': fields.Datetime.now(),
                              'notice': 'Producción habilitada: los comprobantes se numeran con el diario de producción y son documentos fiscales reales.'})
        self._ensure_journal()
        return True

    def action_enable_testing(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise ValidationError('Solo un responsable contable puede cambiar el ambiente.')
        if self.ambiente == '1':
            return True
        self._internal_write({'ambiente': '1', 'production_acknowledged': False,
                              'notice': 'Vuelto a pruebas: se usa el diario de pruebas con su propio consecutivo.'})
        self._ensure_journal()
        return True


class Users(models.Model):
    _inherit = 'res.users'

    ec_point_id = fields.Many2one('erpec.fiscal.point', string='Punto de emisión predeterminado', check_company=True,
                                  help='Se propone al crear guías de remisión y otros comprobantes de este usuario.')

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['ec_point_id']


class Certificate(models.Model):
    _name = 'erpec.fiscal.certificate'
    _description = 'Certificado de firma electrónica (SRI)'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict')
    # Autoservicio: la empresa (cliente) del propio inquilino puede cargar y reemplazar su
    # certificado -- ampliado de solo base.group_system a incluir account.group_account_user.
    # Cambio de postura deliberado: mismo nivel de protección de reposo que la credencial de
    # PayPhone (sin cifrado adicional, solo permisos), pero ahora el grupo con acceso incluye al
    # cliente dueño de la empresa, no solo administración interna -- es el requisito explícito de
    # este incremento (autoservicio real para clientes, modelo multi-tenant de OP08).
    # El archivo y la contraseña NUNCA se guardan en claro: p12_file/p12_password son solo de entrada (se leen siempre
    # vacíos) y su inverso los cifra (ver secret_store.py). Solo el servidor los descifra, al firmar.
    p12_file = fields.Binary('Cargar o reemplazar archivo .p12', compute='_compute_secret_inputs', inverse='_inverse_p12_file',
                             groups='base.group_system,account.group_account_user', attachment=False)
    p12_password = fields.Char('Contraseña del .p12 (se guarda cifrada)', compute='_compute_secret_inputs', inverse='_inverse_p12_password',
                               groups='base.group_system,account.group_account_user')
    p12_encrypted = fields.Char('Archivo .p12 cifrado', groups='base.group_system', copy=False, readonly=True)
    p12_password_encrypted = fields.Char('Contraseña cifrada', groups='base.group_system', copy=False, readonly=True)
    p12_loaded = fields.Boolean('Certificado cargado (cifrado)', readonly=True, copy=False)
    p12_fingerprint = fields.Char('Huella del archivo (SHA-256)', readonly=True, copy=False)
    verified = fields.Boolean('Verificado', readonly=True, copy=False)
    subject_summary = fields.Char('Titular (según certificado)', readonly=True, copy=False)
    issuer_summary = fields.Char('Entidad certificadora', readonly=True, copy=False)
    issuer_trusted = fields.Boolean('Entidad certificadora reconocida', readonly=True, copy=False)
    not_valid_before = fields.Datetime('Vigente desde', readonly=True, copy=False)
    not_valid_after = fields.Datetime('Vigente hasta', readonly=True, copy=False)
    checked_at = fields.Datetime('Última comprobación', readonly=True, copy=False)
    signature_tested = fields.Boolean('Firma de prueba realizada', readonly=True, copy=False)
    signature_tested_at = fields.Datetime('Última prueba de firma', readonly=True, copy=False)
    verify_attempts = fields.Integer('Intentos de verificación', readonly=True, copy=False, default=0)
    verify_window_start = fields.Datetime('Inicio de ventana de intentos', readonly=True, copy=False)
    notice = fields.Text('Estado', readonly=True, default='Cargar el archivo .p12 y su contraseña, luego verificar.')
    _sql_constraints = [('one_company', 'unique(company_id)', 'Ya existe un certificado para esta empresa.')]

    def _compute_secret_inputs(self):
        self.p12_file = False
        self.p12_password = False

    def _secret_context(self, name):
        self.ensure_one()
        return 'cert:%d:%s' % (self.id, name)

    def _inverse_p12_file(self):
        for record in self:
            if not record.p12_file:
                continue
            raw = base64.b64decode(record.p12_file)
            if len(raw) > MAX_P12_BYTES:
                raise ValidationError('El archivo .p12 supera el tamaño máximo permitido (%d KB).' % (MAX_P12_BYTES // 1024))
            record.sudo().write({
                'p12_encrypted': secret_store.encrypt(raw, record._secret_context('p12')),
                'p12_loaded': True, 'p12_fingerprint': hashlib.sha256(raw).hexdigest(),
                'verified': False, 'signature_tested': False, 'signature_tested_at': False,
                'notice': 'Certificado cargado y cifrado. Verifícalo para usarlo.'})

    def _inverse_p12_password(self):
        for record in self:
            if not record.p12_password:
                continue
            record.sudo().write({
                'p12_password_encrypted': secret_store.encrypt(record.p12_password.encode('utf-8'), record._secret_context('password')),
                'verified': False, 'signature_tested': False, 'signature_tested_at': False,
                'notice': 'Contraseña guardada cifrada. Verifica el certificado para usarlo.'})

    def _signing_material(self):
        """(bytes del .p12, contraseña en bytes), descifrados solo en memoria y solo para firmar o verificar."""
        self.ensure_one()
        record = self.sudo()
        if not record.p12_encrypted or not record.p12_password_encrypted:
            raise ValidationError('Carga el archivo .p12 y su contraseña.')
        try:
            return (secret_store.decrypt(record.p12_encrypted, record._secret_context('p12')),
                    secret_store.decrypt(record.p12_password_encrypted, record._secret_context('password')))
        except secret_store.SecretError as error:
            raise ValidationError(str(error)) from error

    @api.onchange('p12_file', 'p12_password')
    def _onchange_p12_preview(self):
        """Vista previa sin persistir: valida en memoria al elegir el archivo/clave, antes de
        guardar -- equivalente al endpoint separado de "preview" de sinkroniq-mobile, pero
        resuelto con el ciclo de onchange propio de Odoo (no llega a la base de datos)."""
        if not self.p12_file or not self.p12_password:
            return
        try:
            p12_bytes = base64.b64decode(self.p12_file)
        except (TypeError, ValueError):
            self.notice = 'El archivo .p12 no es válido.'
            return
        ruc = self.company_id.vat or ''
        try:
            _key, cert, _chain = xades.credentials(p12_bytes, self.p12_password.encode('utf-8'), ruc)
            trusted = self._issuer_trusted(cert.issuer.rfc4514_string())
            preview = 'Vista previa: certificado válido para %s, vigente hasta %s.' % (
                cert.subject.rfc4514_string(), cert.not_valid_after_utc.date().isoformat())
            if not trusted:
                preview += ' Advertencia: la entidad certificadora no está en el catálogo local de CAs reconocidas por el SRI; verifícala manualmente.'
            self.notice = preview
        except ValueError as error:
            self.notice = 'Vista previa: ' + str(error)

    @staticmethod
    def _issuer_trusted(issuer_text):
        return any(pattern.search(issuer_text or '') for pattern in TRUSTED_CA_PATTERNS)

    def _check_verify_rate(self):
        self.ensure_one()
        now = fields.Datetime.now()
        window_start = self.verify_window_start
        if not window_start or now - window_start > timedelta(minutes=VERIFY_WINDOW_MINUTES):
            self.write({'verify_attempts': 0, 'verify_window_start': now})
            return
        if self.verify_attempts >= MAX_VERIFY_ATTEMPTS:
            raise UserError('Demasiados intentos de verificación. Espera %d minutos e inténtalo de nuevo.' % VERIFY_WINDOW_MINUTES)

    def action_verify(self):
        self.ensure_one()
        self.check_access('write')
        self._check_verify_rate()
        p12_bytes, password = self._signing_material()
        ruc = self.company_id.vat or ''
        try:
            _key, cert, _chain = xades.credentials(p12_bytes, password, ruc)
            issuer_text = cert.issuer.rfc4514_string()
            trusted = self._issuer_trusted(issuer_text)
            notice = 'Certificado verificado: firma RSA válida, vigente, y coincide con el RUC de la empresa.'
            if not trusted:
                notice += ' Advertencia: la entidad certificadora no está en el catálogo local de CAs reconocidas por el SRI; verifícala manualmente antes de usarla en producción.'
            values = {
                'verified': True,
                'subject_summary': cert.subject.rfc4514_string(),
                'issuer_summary': issuer_text,
                'issuer_trusted': trusted,
                'not_valid_before': cert.not_valid_before_utc.replace(tzinfo=None),
                'not_valid_after': cert.not_valid_after_utc.replace(tzinfo=None),
                'notice': notice,
                'signature_tested': False,
                'signature_tested_at': False,
            }
        except ValueError as error:
            values = {'verified': False, 'notice': 'No se pudo verificar: ' + str(error)}
        self.write(dict(values, checked_at=fields.Datetime.now(), verify_attempts=self.verify_attempts + 1))
        return True

    def action_test_signature(self):
        """Firma un XML sintético mínimo (no un comprobante real ni un envío al SRI) para
        confirmar que el certificado puede firmar de verdad -- credentials() solo confirma que el
        .p12 abre y coincide con el RUC, no que xades.sign() completa sin error sobre un documento
        real. Mismo objetivo que probarFirma()/probeCertificateSignature() de sinkroniq-mobile,
        sin necesitar un servicio de firma aparte ni tocar la red."""
        self.ensure_one()
        self.check_access('write')
        if not self.verified:
            raise UserError('Verifica el certificado antes de probar la firma.')
        p12_bytes, password = self._signing_material()
        ruc = self.company_id.vat or ''
        probe_xml = SIGNATURE_PROBE_XML % {b'ruc': ruc.encode('utf-8')}
        try:
            signed = xades.sign(probe_xml, p12_bytes, password, ruc)
            xades.verify(signed, xades.credentials(p12_bytes, password, ruc)[1])
            self.write({
                'signature_tested': True,
                'signature_tested_at': fields.Datetime.now(),
                'notice': 'Certificado verificado y firma de prueba exitosa: el certificado puede firmar comprobantes.',
            })
        except ValueError as error:
            self.write({'signature_tested': False, 'notice': 'La prueba de firma falló: ' + str(error)})
        return True


class Emission(models.Model):
    _name = 'erpec.fiscal.emission'
    _description = 'Emisión nativa (firma XAdES + transmisión SOAP directa al SRI)'
    _rec_name = 'access_key'
    _order = 'id desc'
    _check_company_auto = True

    move_id = fields.Many2one('account.move', string='Comprobante', check_company=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', compute='_compute_company_id', store=True, index=True)
    ambiente = fields.Selection([('1', 'Pruebas'), ('2', 'Producción')], default='1', required=True, readonly=True)
    access_key = fields.Char('Clave de acceso', readonly=True)
    xml_unsigned = fields.Binary('XML sin firmar', readonly=True, attachment=False)
    xml_signed = fields.Binary('XML firmado', readonly=True, attachment=False)
    xml_authorized = fields.Binary('XML autorizado por el SRI', readonly=True, attachment=False)
    ride_pdf = fields.Binary('RIDE', readonly=True, attachment=False)
    authorization_number = fields.Char('Número de autorización SRI', readonly=True)
    authorization_date = fields.Char('Fecha de autorización SRI', readonly=True)
    state = fields.Selection([
        ('draft', 'Preparando'),
        ('signed', 'Firmada'),
        ('sent', 'Enviada a Recepción'),
        ('waiting', 'Esperando autorización'),
        ('authorized', 'Autorizada'),
        ('rejected', 'No autorizada'),
        ('returned', 'Devuelta en recepción'),
        ('blocked', 'Revisión requerida'),
    ], default='draft', required=True, readonly=True)
    attempts = fields.Integer('Intentos', readonly=True)
    next_attempt = fields.Datetime('Próximo intento', readonly=True)
    message = fields.Text('Estado y siguiente acción', readonly=True, default='Solicitud preparada. Procesar la cola para firmar y transmitir.')
    _sql_constraints = [('one_invoice', 'unique(move_id)', 'El comprobante ya tiene una emisión nativa.')]

    @api.depends('move_id.company_id')
    def _compute_company_id(self):
        for emission in self:
            emission.company_id = emission.move_id.company_id

    def _has_source(self):
        # Otros módulos (p. ej. retenciones) amplían la fuente del comprobante sobreescribiendo este método.
        return bool(self.move_id)

    @api.constrains('move_id')
    def _check_source(self):
        for emission in self:
            if not emission._has_source():
                raise ValidationError('La emisión requiere un documento de origen.')

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_fiscal_sri_internal') is not _INTERNAL:
            raise ValidationError('Prepara la emisión desde el comprobante contabilizado.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_fiscal_sri_internal') is not _INTERNAL:
            raise ValidationError('La emisión nativa se actualiza mediante sus acciones.')
        return super().write(values)

    def unlink(self):
        raise ValidationError('Conserva la emisión nativa para conciliación y auditoría.')

    def _save(self, **values):
        return self.with_context(_fiscal_sri_internal=_INTERNAL).write(values)

    def action_process(self):
        for emission in self:
            emission.check_access('write')
            self.env.cr.execute('SELECT id FROM erpec_fiscal_emission WHERE id=%s FOR UPDATE', [emission.id])
            emission.invalidate_recordset()
            if emission.state in ('authorized', 'rejected'):
                continue
            if emission.next_attempt and emission.next_attempt > fields.Datetime.now():
                raise UserError('Espera al próximo intento indicado para no saturar el servicio.')
            if emission.attempts >= MAX_ATTEMPTS:
                emission._save(state='blocked', message='Se agotaron %d intentos. Revisar y reabrir explícitamente.' % MAX_ATTEMPTS)
                continue
            try:
                emission._save(attempts=emission.attempts + 1)
                if emission.state in ('draft', 'signed'):
                    emission._transmit()
                elif emission.state in ('sent', 'waiting'):
                    emission._poll()
            except sri_client.SriError as error:
                delay = RETRY_DELAY_SECONDS * max(1, emission.attempts)
                emission._save(
                    state='blocked' if not error.retry else emission.state,
                    message=error.code,
                    next_attempt=fields.Datetime.now() + timedelta(seconds=delay) if error.retry else False,
                )
        return True

    def _transmit(self):
        self.ensure_one()
        xml_signed = base64.b64decode(self.xml_signed)
        estado, mensajes = sri_client.enviar_recepcion(xml_signed, ambiente=self.ambiente)
        if estado == 'DEVUELTA':
            self._save(state='returned', message='DEVUELTA en Recepción: ' + str(mensajes))
            return
        self._save(state='waiting', message='RECIBIDA; esperando autorización.',
                    next_attempt=fields.Datetime.now() + timedelta(seconds=POLL_DELAY_SECONDS))

    @api.model
    def _cron_process(self):
        emissions = self.search([('state', 'not in', ['authorized', 'rejected']),
                                  '|', ('next_attempt', '=', False), ('next_attempt', '<=', fields.Datetime.now())], limit=10)
        for emission in emissions:
            emission.action_process()

    def _poll(self):
        self.ensure_one()
        estado, autorizacion, mensajes = sri_client.consultar_autorizacion(self.access_key, ambiente=self.ambiente)
        if estado in ('PENDIENTE', 'EN PROCESO'):
            self._save(message='Aún sin autorización (%s).' % estado,
                        next_attempt=fields.Datetime.now() + timedelta(seconds=POLL_DELAY_SECONDS))
            return
        if estado == 'NO AUTORIZADO':
            self._save(state='rejected', message='NO AUTORIZADO: ' + str(mensajes))
            return
        # El tipo de comprobante (codDoc) va en la clave de acceso (posiciones 9-10, índice
        # 8:10) -- fuente única de verdad, no se guarda por separado ni se infiere del move_id.
        doc_type = self.access_key[8:10]
        builder = {'04': ride_module.build_ride_notacredito, '05': ride_module.build_ride_notadebito, '07': ride_module.build_ride_retencion,
                    '06': ride_module.build_ride_guiaremision,
                    '03': ride_module.build_ride_liquidacion}.get(doc_type, ride_module.build_ride)
        ride_pdf = builder(autorizacion['comprobante'], autorizacion['numero'], autorizacion['fecha'])
        self._save(state='authorized', xml_authorized=base64.b64encode(autorizacion['comprobante']), ride_pdf=base64.b64encode(ride_pdf),
                    authorization_number=autorizacion['numero'], authorization_date=autorizacion['fecha'],
                    message='Autorizada por el SRI.')


class Reimbursement(models.Model):
    _name = 'erpec.fiscal.reimbursement'
    _description = 'Comprobante de sustento de reembolso (factura de reembolso)'
    _check_company_auto = True
    _order = 'id'

    move_id = fields.Many2one('account.move', required=True, ondelete='cascade', check_company=True, domain=[('move_type', '=', 'out_invoice')])
    company_id = fields.Many2one(related='move_id.company_id', store=True, index=True)
    provider_type = fields.Selection([('04', 'RUC'), ('05', 'Cédula'), ('06', 'Pasaporte'), ('08', 'Identificación del exterior')],
                                     string='Tipo de identificación del proveedor', required=True, default='04')
    provider_vat = fields.Char('Identificación del proveedor', required=True)
    provider_kind = fields.Selection([('01', 'Persona natural'), ('02', 'Sociedad')], string='Tipo de proveedor', required=True, default='02')
    country_code = fields.Char('País de pago (código)', size=3, default='593', required=True)
    doc_type = fields.Selection([('01', 'Factura'), ('02', 'Nota o boleta de venta'), ('03', 'Liquidación de compra'),
                                 ('08', 'Boletos de espectáculos públicos'), ('09', 'Tiquetes de máquinas registradoras'), ('12', 'Documentos de instituciones financieras')],
                                string='Tipo de comprobante', required=True, default='01')
    doc_number = fields.Char('Número del comprobante (001-001-000000001)', required=True)
    doc_date = fields.Date('Fecha de emisión', required=True)
    authorization = fields.Char('Número de autorización (10 a 49 dígitos)', required=True)
    base_amount = fields.Monetary('Base imponible', required=True, currency_field='currency_id')
    tax_kind = fields.Selection([('vat15', 'IVA 15%'), ('zero', 'IVA 0%'), ('no_object', 'No objeto de IVA'), ('exempt', 'Exento de IVA')],
                                string='Impuesto del comprobante', required=True, default='vat15')
    tax_amount = fields.Monetary('IVA', compute='_compute_tax_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='move_id.currency_id')

    @api.depends('base_amount', 'tax_kind', 'currency_id')
    def _compute_tax_amount(self):
        for line in self:
            line.tax_amount = line.currency_id.round(line.base_amount * 0.15) if line.tax_kind == 'vat15' and line.currency_id else 0.0

    @api.constrains('base_amount', 'doc_number', 'authorization', 'provider_vat')
    def _check_values(self):
        for line in self:
            if line.base_amount <= 0:
                raise ValidationError('La base del comprobante de reembolso debe ser positiva.')
            if not re.fullmatch(r'[0-9]{3}-[0-9]{3}-[0-9]{9}', line.doc_number or ''):
                raise ValidationError('El número del comprobante requiere el formato 001-001-000000001.')
            if not re.fullmatch(r'[0-9]{10,49}', line.authorization or ''):
                raise ValidationError('La autorización del comprobante requiere de 10 a 49 dígitos.')

    def _check_editable(self):
        if any(move.ec_fiscal_emission_ids for move in self.mapped('move_id')):
            raise ValidationError('La factura ya fue firmada; sus sustentos de reembolso no se modifican.')

    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list)
        records._check_editable()
        return records

    def write(self, values):
        self._check_editable()
        return super().write(values)

    def unlink(self):
        self._check_editable()
        return super().unlink()

    def _engine_data(self):
        self.ensure_one()
        rate_code, rate = {'vat15': ('4', 15), 'zero': ('0', 0), 'no_object': ('6', 0), 'exempt': ('7', 0)}[self.tax_kind]
        return {'provider_type': self.provider_type, 'provider_vat': self.provider_vat, 'provider_kind': self.provider_kind,
                'country': self.country_code, 'doc_type': self.doc_type, 'doc_number': self.doc_number, 'doc_date': str(self.doc_date),
                'authorization': self.authorization,
                'taxes': [{'rate_code': rate_code, 'rate': rate, 'base': self.base_amount, 'amount': self.tax_amount}]}


class Move(models.Model):
    _inherit = 'account.move'

    ec_sri_reimbursement_ids = fields.One2many('erpec.fiscal.reimbursement', 'move_id', string='Sustentos de reembolso (SRI)', copy=False)

    ec_fiscal_emission_ids = fields.One2many('erpec.fiscal.emission', 'move_id', string='Emisiones nativas SRI', copy=False)

    def _gather_native_common(self, allow_special_vat=False):
        """Datos compartidos entre factura y nota de crédito: identificación del emisor/
        comprador y líneas con impuesto. Duplicado intencional de la validación/armado de
        datos de erpec_fiscal_native.models.Move.action_native_preview — ver docstring del
        módulo."""
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id.commercial_partner_id
        identification = ('04' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_ruc')
                          else '05' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_dni')
                          else '06' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_passport') else '')
        items = []
        for line in self.invoice_line_ids.filtered(lambda row: row.display_type == 'product'):
            tax = line.tax_ids
            special = {'not_charged_vat': 'no_object', 'exempt_vat': 'exempt'}.get(tax.tax_group_id.l10n_ec_type) if len(tax) == 1 else None
            if (len(tax) != 1 or tax.amount_type != 'percent' or tax.price_include or tax.include_base_amount
                    or not ((tax.tax_group_id.l10n_ec_type, tax.amount) in [('zero_vat', 0), ('vat15', 15)] or (allow_special_vat and special and tax.amount == 0))):
                raise ValidationError('Revisar IVA: se admite una tarifa 0 o 15 por línea (y no objeto/exento solo en facturas), sin impuestos incluidos ni compuestos.')
            items.append({'code': line.product_id.default_code or str(line.id), 'description': line.name,
                          'quantity': line.quantity, 'unit': line.price_unit, 'discount': line.discount,
                          'rate': special if (allow_special_vat and special) else tax.amount, 'subtotal': line.price_subtotal,
                          'tax': line.price_total - line.price_subtotal})
        return {'date': str(self.invoice_date), 'number': self.l10n_latam_document_number, 'issuer_vat': company.vat,
                'issuer_name': company.name, 'issuer_address': company.street, 'buyer_type': identification,
                'buyer_vat': partner.vat, 'buyer_name': partner.name, 'buyer_address': partner.street,
                'accounting': company.ec_native_accounting, 'total': self.amount_total, 'items': items,
                'ambiente': self.journal_id.ec_sri_ambiente or '1',
                'establishment_address': self.journal_id.ec_point_id.establishment_address or False}

    def _gather_native_data(self):
        data = self._gather_native_common(allow_special_vat=True)
        data['payment'] = self.ec_fiscal_payment_code
        data['reimbursements'] = [line._engine_data() for line in self.ec_sri_reimbursement_ids]
        return data

    def _gather_native_credit_note_data(self):
        self.ensure_one()
        original = self.reversed_entry_id
        if not original or original.move_type != 'out_invoice':
            raise ValidationError('La nota de crédito debe generarse desde "Añadir nota de crédito" sobre la factura que modifica.')
        if not original.l10n_latam_document_number or original.l10n_latam_document_type_id.code != '01':
            raise ValidationError('La factura modificada debe tener secuencial asignado y ser de tipo Factura (código 01).')
        data = self._gather_native_common()
        data['modified_type'] = '01'
        data['modified_number'] = original.l10n_latam_document_number
        data['modified_date'] = str(original.invoice_date)
        data['reason'] = (self.ref or self.narration or 'Nota de crédito').strip()[:300]
        return data

    ec_is_liquidation = fields.Boolean(compute='_compute_ec_is_liquidation')

    @api.depends('move_type', 'l10n_latam_document_type_id')
    def _compute_ec_is_liquidation(self):
        for move in self:
            move.ec_is_liquidation = move.move_type == 'in_invoice' and move.l10n_latam_document_type_id.code == '03'

    def _gather_native_liquidation_data(self):
        self.ensure_one()
        data = self._gather_native_common()
        data['provider_type'] = data.pop('buyer_type')
        data['provider_vat'] = data.pop('buyer_vat')
        data['provider_name'] = data.pop('buyer_name')
        data['provider_address'] = data.pop('buyer_address')
        data['payment'] = self.ec_fiscal_payment_code
        return data

    def action_native_emit_liquidation(self):
        """Liquidación de compra (codDoc 03): la emite el comprador a un proveedor que no factura. El número
        sale del consecutivo del punto de emisión del diario (por ambiente) y se asigna antes de contabilizar."""
        self.ensure_one()
        self.check_access('write')
        if not self.ec_is_liquidation or self.state == 'cancel' or self.currency_id.name != 'USD' or self.company_id.country_id.code != 'EC':
            raise ValidationError('Se requiere una factura de proveedor con tipo documental Liquidación de compra (03), en USD, de una empresa de Ecuador.')
        if self.ec_fiscal_emission_ids:
            return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission',
                    'res_id': self.ec_fiscal_emission_ids[0].id, 'view_mode': 'form'}
        certificate = self.env['erpec.fiscal.certificate'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not certificate or not certificate.verified:
            raise ValidationError('Configura y verifica primero el certificado de firma electrónica de esta empresa.')
        self.company_id._check_regime_supported()
        point = self.journal_id.ec_point_id
        if not point:
            raise ValidationError('Asigna un punto de emisión SRI al diario de compras que emite liquidaciones.')
        self.journal_id._sri_check_ambiente()
        if not self.l10n_latam_document_number:
            if self.state != 'draft':
                raise ValidationError('La liquidación contabilizada requiere su número; emítela desde el borrador para que se asigne el consecutivo.')
            self.l10n_latam_document_number = point._next_sequence('liquidation')
        elif not self.l10n_latam_document_number.startswith('%s-%s-' % (point.establishment, point.emission)):
            raise ValidationError('El número no corresponde al establecimiento y punto de emisión del diario (%s-%s).' % (point.establishment, point.emission))
        if self.state == 'draft':
            self.action_post()
        data = self._gather_native_liquidation_data()
        data['numeric'] = str(secrets.randbelow(10**8)).zfill(8)
        try:
            access_key, xml_unsigned = liquidacion_engine.generate(data)
            xml_signed = xades.sign(xml_unsigned, *certificate._signing_material(), self.company_id.vat)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        emission = self.env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=_INTERNAL).create({
            'move_id': self.id, 'access_key': access_key, 'ambiente': data['ambiente'],
            'xml_unsigned': base64.b64encode(xml_unsigned), 'xml_signed': base64.b64encode(xml_signed),
            'state': 'signed', 'message': 'Firmada. Procesar la cola para transmitir al SRI.'})
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission', 'res_id': emission.id, 'view_mode': 'form'}

    def _gather_native_debit_note_data(self):
        self.ensure_one()
        original = self.debit_origin_id
        if not original or original.move_type != 'out_invoice':
            raise ValidationError('La nota de débito debe generarse desde "Añadir nota de débito" sobre la factura que modifica.')
        if not original.l10n_latam_document_number or original.l10n_latam_document_type_id.code != '01':
            raise ValidationError('La factura modificada debe tener secuencial asignado y ser de tipo Factura (código 01).')
        if self.l10n_latam_document_type_id.code != '05':
            raise ValidationError('La nota de débito debe tener el tipo documental Nota de débito (código 05).')
        data = self._gather_native_common()
        data['modified_type'] = '01'
        data['modified_number'] = original.l10n_latam_document_number
        data['modified_date'] = str(original.invoice_date)
        data['payment'] = self.ec_fiscal_payment_code
        return data

    def action_native_emit(self):
        self.ensure_one()
        self.check_access('write')
        if self.state != 'posted' or self.move_type not in NATIVE_MOVE_TYPES or self.currency_id.name != 'USD' or self.company_id.country_id.code != 'EC':
            raise ValidationError('Se requiere una factura, nota de crédito o nota de débito de venta contabilizada en USD de una empresa de Ecuador.')
        if self.ec_fiscal_job_ids:
            raise ValidationError('Este comprobante ya está asignado al Facturador externo; conserva su autoridad y trazabilidad.')
        if self.ec_fiscal_emission_ids:
            return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission',
                    'res_id': self.ec_fiscal_emission_ids[0].id, 'view_mode': 'form'}
        certificate = self.env['erpec.fiscal.certificate'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not certificate or not certificate.verified:
            raise ValidationError('Configura y verifica primero el certificado de firma electrónica de esta empresa.')
        self.company_id._check_regime_supported()
        self.journal_id._sri_check_ambiente()
        point = self.journal_id.ec_point_id
        if point and not (self.l10n_latam_document_number or '').startswith('%s-%s-' % (point.establishment, point.emission)):
            raise ValidationError('El número del comprobante no corresponde al establecimiento y punto de emisión del diario (%s-%s).' % (point.establishment, point.emission))
        is_credit_note = self.move_type == 'out_refund'
        is_debit_note = self.move_type == 'out_invoice' and bool(self.debit_origin_id)
        if is_credit_note:
            data, engine_module = self._gather_native_credit_note_data(), notacredito_engine
        elif is_debit_note:
            data, engine_module = self._gather_native_debit_note_data(), notadebito_engine
        else:
            data, engine_module = self._gather_native_data(), None
        numeric_code = str(secrets.randbelow(10**8)).zfill(8)
        data['numeric'] = numeric_code
        try:
            access_key, xml_unsigned = (engine_module.generate(data) if engine_module else generate(data))
        except ValueError as error:
            raise ValidationError(str(error)) from error
        p12_bytes, password = certificate._signing_material()
        try:
            xml_signed = xades.sign(xml_unsigned, p12_bytes, password, self.company_id.vat)
        except ValueError as error:
            raise ValidationError('No se pudo firmar: ' + str(error)) from error
        emission = self.env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=_INTERNAL).create({
            'move_id': self.id, 'access_key': access_key, 'ambiente': data['ambiente'],
            'xml_unsigned': base64.b64encode(xml_unsigned), 'xml_signed': base64.b64encode(xml_signed),
            'state': 'signed', 'message': 'Firmada. Procesar la cola para transmitir al SRI.',
        })
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission', 'res_id': emission.id, 'view_mode': 'form'}
