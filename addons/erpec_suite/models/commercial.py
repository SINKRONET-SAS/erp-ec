"""Contratos versionados; no ejecuta cargos ni acredita conexiones externas."""
import logging
import uuid
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)

def administrator(env):
    if not env.user.has_group('base.group_system'):
        raise AccessError('Solo administración puede cambiar contratos de la suite.')

class Plan(models.Model):
    _name = 'erpec.plan'
    _description = 'Versión de plan comercial'
    _rec_name = 'display_label'
    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', required=True, index=True)
    version = fields.Integer('Versión', required=True, default=1)
    display_label = fields.Char(compute='_label')
    erp = fields.Boolean('ERP Community')
    payroll = fields.Boolean('SKNOMINA')
    invoicing = fields.Boolean('SINKRONET FACTURADOR')
    api_access = fields.Boolean('API externa incluida')
    max_connections = fields.Integer('Conexiones activas', default=1)
    requests_per_minute = fields.Integer('Solicitudes por minuto y conexión', default=60)
    max_users = fields.Integer('Usuarios ERP', default=5)
    max_companies = fields.Integer('Empresas ERP', default=1)
    terms = fields.Text('Condiciones y referencia de tarifa', required=True)
    _sql_constraints = [('version_unique', 'unique(code, version)', 'La versión del plan ya existe.')]

    @api.depends('name', 'version')
    def _label(self):
        for record in self:
            record.display_label = f'{record.name or "Nuevo plan"} · v{record.version}'

    @api.constrains('version', 'erp', 'payroll', 'invoicing', 'api_access', 'max_connections', 'requests_per_minute', 'max_users', 'max_companies')
    def _validate_limits(self):
        for record in self:
            if record.version < 1 or not (record.erp or record.payroll or record.invoicing):
                raise ValidationError('Selecciona al menos un producto y una versión positiva.')
            if record.max_users < 1 or record.max_companies < 1:
                raise ValidationError('Los límites de usuarios y empresas deben ser positivos.')
            if record.max_connections < 0 or record.requests_per_minute < 0:
                raise ValidationError('Las cuotas no pueden ser negativas.')
            if record.api_access and (record.max_connections < 1 or not 1 <= record.requests_per_minute <= 120):
                raise ValidationError('La API requiere conexiones positivas y entre 1 y 120 solicitudes por minuto.')

    def write(self, values):
        administrator(self.env)
        self.env.cr.execute('SELECT id FROM erpec_plan WHERE id IN %s ORDER BY id FOR UPDATE', [tuple(self.ids)])
        if self.env['erpec.subscription'].sudo().search_count([('plan_id', 'in', self.ids)]):
            raise ValidationError('El plan ya tiene contratos. Crea una nueva versión; los contratos existentes se conservan.')
        return super().write(values)

    def action_new_version(self):
        administrator(self.env)
        self.ensure_one()
        latest = self.search([('code', '=', self.code)], order='version desc', limit=1)
        new = self.copy({'version': latest.version + 1})
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': new.id, 'view_mode': 'form'}

class Subscription(models.Model):
    _name = 'erpec.subscription'
    _description = 'Contrato de productos de la suite'
    name = fields.Char('Referencia del contrato', required=True)
    company_id = fields.Many2one('res.company', string='Organización Odoo', required=True, default=lambda self: self.env.company, index=True)
    plan_id = fields.Many2one('erpec.plan', string='Versión contratada', required=True, ondelete='restrict')
    starts_on = fields.Date('Inicio', required=True, default=fields.Date.today)
    ends_on = fields.Date('Fin', required=True)
    billing_owner = fields.Selection([('existing', 'Conservar contrato y cobrador existentes'), ('manual', 'Alta comercial administrada, sin cargo automático')], string='Autoridad de cobro', required=True)
    billing_reference = fields.Char('Responsable de cobro y contrato de origen', required=True)
    authorization = fields.Char('Referencia de autorización comercial', required=True)
    activated_at = fields.Datetime('Alta autorizada', readonly=True, copy=False)
    activated_by = fields.Many2one('res.users', string='Autorizado por', readonly=True, copy=False)
    suspended = fields.Boolean('Suspendido', readonly=True, copy=False)
    state = fields.Selection([('draft', 'Borrador'), ('future', 'Aún no vigente'), ('active', 'Vigente'), ('expired', 'Vencido'), ('suspended', 'Suspendido')], string='Estado', compute='_compute_rights')
    rights = fields.Text('Derechos efectivos', compute='_compute_rights')
    correlation_id = fields.Char('Referencia de auditoría', default=lambda self: str(uuid.uuid4()), readonly=True, copy=False)
    _sql_constraints = [('contract_company_unique', 'unique(company_id, name)', 'La referencia de contrato ya existe en esta organización.')]

    @api.depends('activated_at', 'starts_on', 'ends_on', 'suspended', 'plan_id')
    def _compute_rights(self):
        today = fields.Date.today()
        for record in self:
            record.state = 'draft' if not record.activated_at else 'suspended' if record.suspended else 'future' if record.starts_on > today else 'expired' if record.ends_on < today else 'active'
            plan = record.plan_id
            if record.state != 'active':
                record.rights = 'Sin acceso efectivo. Revisa autorización, vigencia y suspensión.'
            else:
                products = [label for flag, label in [(plan.erp, 'ERP'), (plan.payroll, 'SKNOMINA'), (plan.invoicing, 'FACTURADOR')] if flag]
                api_text = f'{plan.max_connections} conexiones; {plan.requests_per_minute} solicitudes/min por conexión' if plan.api_access else 'API no incluida'
                record.rights = ', '.join(products) + '. ' + api_text + '. Conexiones externas pendientes de verificación; este contrato no modifica otros productos.'

    @api.constrains('starts_on', 'ends_on', 'company_id')
    def _validate_contract(self):
        for record in self:
            if record.ends_on < record.starts_on:
                raise ValidationError('La fecha final debe ser igual o posterior al inicio.')
            if record.company_id not in self.env.companies:
                raise AccessError('La organización no está autorizada en esta sesión.')

    @api.model_create_multi
    def create(self, values_list):
        administrator(self.env)
        for values in values_list:
            if any(key in values for key in ['activated_at', 'activated_by', 'suspended', 'correlation_id']):
                raise AccessError('Usa las acciones autorizadas para cambiar el estado del contrato.')
            if values.get('plan_id'):
                self.env.cr.execute('SELECT id FROM erpec_plan WHERE id = %s FOR UPDATE', [values['plan_id']])
        return super().create(values_list)

    def write(self, values):
        administrator(self.env)
        if any(key in values for key in ['activated_at', 'activated_by', 'suspended', 'correlation_id']):
            raise AccessError('Usa las acciones autorizadas para cambiar el estado del contrato.')
        self.env.cr.execute('SELECT id FROM erpec_subscription WHERE id IN %s ORDER BY id FOR UPDATE', [tuple(self.ids)])
        self.invalidate_recordset()
        if any(self.mapped('activated_at')):
            raise ValidationError('El contrato autorizado es inmutable. Crea una sustitución explícita y suspende el anterior.')
        if values.get('plan_id'):
            self.env.cr.execute('SELECT id FROM erpec_plan WHERE id = %s FOR UPDATE', [values['plan_id']])
        return super().write(values)

    def _lock_organization(self):
        self.ensure_one()
        administrator(self.env)
        self.check_access('write')
        self.env.cr.execute('SELECT id FROM res_company WHERE id = %s FOR UPDATE', [self.company_id.id])
        self.env.cr.execute('SELECT id FROM erpec_subscription WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()

    def _check_overlap(self):
        if self.search_count([('company_id', '=', self.company_id.id), ('id', '!=', self.id), ('activated_at', '!=', False), ('suspended', '=', False), ('starts_on', '<=', self.ends_on), ('ends_on', '>=', self.starts_on)]):
            raise ValidationError('Existe otro contrato autorizado para estas fechas. Revisa la migración para evitar doble contratación.')

    def action_activate(self):
        self._lock_organization()
        if self.activated_at:
            _logger.info('Alta repetida sin cambios correlationId=%s userId=%s', self.correlation_id, self.env.uid)
            return True
        if not (self.authorization or '').strip() or not (self.billing_reference or '').strip():
            raise ValidationError('Registra evidencia de autorización y responsable de cobro.')
        self._check_overlap()
        super(Subscription, self).write({'activated_at': fields.Datetime.now(), 'activated_by': self.env.uid})
        _logger.info('Contrato autorizado sin generar cargo correlationId=%s userId=%s', self.correlation_id, self.env.uid)
        return True

    def action_suspend(self):
        self._lock_organization()
        super(Subscription, self).write({'suspended': True})
        _logger.info('Contrato suspendido sin borrar datos correlationId=%s userId=%s', self.correlation_id, self.env.uid)

    def action_resume(self):
        self._lock_organization()
        if not self.activated_at:
            raise ValidationError('El contrato todavía no ha sido autorizado.')
        self._check_overlap()
        super(Subscription, self).write({'suspended': False})
        _logger.info('Contrato reactivado correlationId=%s userId=%s', self.correlation_id, self.env.uid)

    def check_capacity(self, resource, requested):
        self.ensure_one()
        self.check_access('read')
        self.invalidate_recordset(['state', 'rights'])
        if self.state != 'active':
            raise AccessError('El contrato no está vigente.')
        if isinstance(requested, bool) or not isinstance(requested, int) or requested < 0:
            raise ValidationError('La cantidad solicitada debe ser un entero no negativo.')
        plan = self.plan_id
        limits = {'users': plan.max_users if plan.erp else 0, 'companies': plan.max_companies if plan.erp else 0, 'connections': plan.max_connections if plan.api_access else 0}
        if resource not in limits or requested > limits[resource]:
            raise AccessError('La operación supera los derechos contratados.')
        return True

class ProductLink(models.Model):
    _name = 'erpec.product.link'
    _description = 'Vinculación autorizada con producto externo'
    company_id = fields.Many2one('res.company', string='Organización Odoo', required=True, default=lambda self: self.env.company)
    product = fields.Selection([('payroll', 'SKNOMINA'), ('invoicing', 'SINKRONET FACTURADOR')], string='Producto', required=True)
    external_id = fields.Char('Identificador externo de la organización', required=True)
    authorization = fields.Char('Referencia de autorización del administrador externo', required=True)
    status = fields.Selection([('pending', 'Conexión pendiente de verificación')], string='Conectividad', default='pending', readonly=True)
    _sql_constraints = [('company_product_unique', 'unique(company_id, product)', 'Ya existe una vinculación para este producto.'), ('external_product_unique', 'unique(product, external_id)', 'La organización externa ya está vinculada.')]

    @api.constrains('company_id', 'external_id', 'authorization')
    def _check_link(self):
        for record in self:
            if record.company_id not in self.env.companies:
                raise AccessError('No puedes vincular una organización ajena.')
            if not record.external_id.strip() or not record.authorization.strip():
                raise ValidationError('Indica el identificador exacto y la evidencia de autorización. Un correo o RUC no acredita la vinculación.')
