"""Catálogo comercial: una cotización del servidor y condiciones congeladas por contrato."""
import math
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from .commercial import administrator

from odoo.addons.erpec_entitlements.capabilities import CAPABILITIES, missing_requirements


class Capability(models.Model):
    _name = 'erpec.capability'
    _description = 'Capacidad comercial ERP'
    name = fields.Char('Nombre', required=True)
    code = fields.Selection([(k, v[0]) for k, v in CAPABILITIES.items()], required=True, string='Capacidad')
    description = fields.Text('Descripción')
    _sql_constraints = [('code_unique', 'unique(code)', 'La capacidad ya existe.')]

    def write(self, values):
        administrator(self.env)
        if 'code' in values:
            raise ValidationError('El identificador técnico de una capacidad es inmutable.')
        return super().write(values)

class PlanOption(models.Model):
    _name = 'erpec.plan.option'
    _description = 'Módulo incluido o complemento del plan'
    plan_id = fields.Many2one('erpec.plan', required=True, ondelete='cascade', string='Plan')
    capability_id = fields.Many2one('erpec.capability', required=True, ondelete='restrict', string='Capacidad')
    kind = fields.Selection([('included', 'Incluido'), ('optional', 'Complemento opcional')], required=True, default='included', string='Modalidad')
    currency_id = fields.Many2one(related='plan_id.currency_id')
    monthly_price = fields.Monetary('Precio mensual', currency_field='currency_id')
    annual_price = fields.Monetary('Precio anual', currency_field='currency_id')
    _sql_constraints = [('plan_capability_unique', 'unique(plan_id, capability_id)', 'La capacidad ya está en este plan.')]

    def _lock_plans(self, plans):
        administrator(self.env)
        if plans:
            self.env.cr.execute('SELECT id FROM erpec_plan WHERE id IN %s ORDER BY id FOR UPDATE', [tuple(plans.ids)])
            if self.env['erpec.subscription'].sudo().search_count([('plan_id', 'in', plans.ids)]):
                raise ValidationError('El plan tiene contratos; crea otra versión para modificar sus módulos.')

    @api.model_create_multi
    def create(self, values_list):
        self._lock_plans(self.env['erpec.plan'].browse([v['plan_id'] for v in values_list if v.get('plan_id')]))
        return super().create(values_list)

    def write(self, values):
        plans = self.mapped('plan_id') | self.env['erpec.plan'].browse(values.get('plan_id', []))
        self._lock_plans(plans)
        return super().write(values)

    def unlink(self):
        self._lock_plans(self.mapped('plan_id'))
        plans=self.mapped('plan_id')
        result=super().unlink()
        plans._check_published_dependencies()
        return result

    @api.constrains('monthly_price', 'annual_price', 'kind', 'capability_id', 'plan_id')
    def _validate_prices(self):
        self.mapped('plan_id')._check_published_dependencies()
        for record in self:
            if any(not math.isfinite(p) or p < 0 for p in [record.monthly_price, record.annual_price]):
                raise ValidationError('Las tarifas deben ser importes finitos no negativos.')
            if record.kind == 'included' and (record.monthly_price or record.annual_price):
                raise ValidationError('Un módulo incluido no lleva un segundo precio.')

class Plan(models.Model):
    _inherit = 'erpec.plan'
    company_id = fields.Many2one('res.company', string='Operador', required=True, default=lambda self: self.env.company)
    option_ids = fields.One2many('erpec.plan.option', 'plan_id', string='Módulos y complementos', copy=True)
    annual_enabled = fields.Boolean('Ofrecer pago anual')
    annual_price = fields.Monetary('Precio anual', currency_field='currency_id')
    additional_user_price = fields.Monetary('Usuario adicional mensual', currency_field='currency_id')
    additional_user_annual_price = fields.Monetary('Usuario adicional anual', currency_field='currency_id')
    user_limit = fields.Integer('Máximo de usuarios contratables', default=500)
    tax_ids = fields.Many2many('account.tax', string='Impuestos de la oferta', domain="[('type_tax_use','=','sale'),('company_id','=',company_id)]")
    fiscal_reviewed = fields.Boolean('Tratamiento tributario revisado', help='El responsable verifica los impuestos aplicables; no se fija una tasa en el código.')

    @api.constrains('price', 'annual_price', 'additional_user_price', 'additional_user_annual_price', 'annual_enabled', 'user_limit', 'max_users', 'currency_id', 'tax_ids', 'company_id')
    def _validate_catalog(self):
        for record in self:
            amounts = [record.price, record.annual_price, record.additional_user_price, record.additional_user_annual_price]
            if any(not math.isfinite(p) or p < 0 for p in amounts):
                raise ValidationError('Las tarifas deben ser importes finitos no negativos.')
            if record.annual_enabled and record.annual_price <= 0:
                raise ValidationError('Define un precio anual positivo antes de ofrecerlo.')
            if record.user_limit < record.max_users:
                raise ValidationError('El máximo debe incluir los usuarios del plan.')
            if record.currency_id.name != 'USD':
                raise ValidationError('El catálogo de PayPhone se configura en USD.')
            if any(t.company_id != record.company_id or t.type_tax_use != 'sale' for t in record.tax_ids):
                raise ValidationError('Los impuestos deben ser de ventas y del operador del plan.')

    @api.constrains('published', 'option_ids')
    def _check_published_dependencies(self):
        for plan in self.filtered('published'):
            if missing_requirements(plan.option_ids.filtered(lambda x:x.kind=='included').mapped('capability_id.code')):
                raise ValidationError('Para publicar Fabricación incluida, incluye también Inventario.')

    def _quote(self, period='monthly', users=None, option_ids=None):
        self.ensure_one()
        self.check_access('read')
        self.env.cr.execute('SELECT id FROM erpec_plan WHERE id=%s FOR SHARE', [self.id])
        self.invalidate_recordset()
        if period not in ('monthly', 'annual') or (period == 'annual' and not self.annual_enabled):
            raise ValidationError('El periodo solicitado no está disponible.')
        users = self.max_users if users is None else users
        if type(users) is not int or not self.max_users <= users <= self.user_limit:
            raise ValidationError('La cantidad de usuarios debe estar entre los incluidos y el máximo del plan.')
        option_ids = option_ids or []
        if not isinstance(option_ids, (list, tuple)) or any(type(x) is not int for x in option_ids) or len(set(option_ids)) != len(option_ids):
            raise ValidationError('Selección de complementos inválida.')
        selected = self.option_ids.filtered(lambda x: x.id in option_ids)
        if set(selected.ids) != set(option_ids) or any(x.kind != 'optional' for x in selected):
            raise ValidationError('El complemento no pertenece a esta oferta o ya está incluido.')
        included = self.option_ids.filtered(lambda x: x.kind == 'included')
        annual = period == 'annual'
        base = self.annual_price if annual else self.price
        per_user = self.additional_user_annual_price if annual else self.additional_user_price
        extras = sum(selected.mapped('annual_price' if annual else 'monthly_price'))
        subtotal = self.currency_id.round(base + extras + (users - self.max_users) * per_user)
        result = self.tax_ids.compute_all(subtotal, currency=self.currency_id, quantity=1)
        tax = self.currency_id.round(result['total_included'] - result['total_excluded'])
        capabilities = sorted((included | selected).mapped('capability_id.code'))
        missing=missing_requirements(capabilities)
        if missing:
            raise ValidationError('La combinación requiere incluir: '+', '.join(CAPABILITIES[key][0] for key in missing))
        return {'schema': 1, 'plan_id': self.id, 'code': self.code, 'version': self.version,
                'period': period, 'months': 12 if annual else 1, 'currency': 'USD',
                'users': users, 'included_users': self.max_users, 'additional_users': users-self.max_users,
                'base_price': base, 'per_user_price': per_user, 'options_price': extras,
                'option_ids': selected.ids, 'capabilities': capabilities,
                'modules': sorted({m for key in capabilities for m in CAPABILITIES[key][1]}),
                'max_companies': self.max_companies, 'max_connections': self.max_connections if self.api_access else 0,
                'requests_per_minute': self.requests_per_minute if self.api_access else 0,
                'untaxed': result['total_excluded'], 'tax': tax, 'total': result['total_included'],
                'taxes': [{'id': t['id'], 'name': t['name'], 'amount': t['amount'], 'base': t['base']} for t in result['taxes']]}

class Subscription(models.Model):
    _inherit = 'erpec.subscription'
    renewal_of_id = fields.Many2one('erpec.subscription', string='Renueva contrato', ondelete='restrict', copy=False)
    starts_on_activation = fields.Boolean('Inicio al confirmar el pago', default=False, copy=False)
    period = fields.Selection([('monthly', 'Mensual'), ('annual', 'Anual')], default='monthly', required=True, string='Periodo')
    user_quantity = fields.Integer('Usuarios contratados', default=0)
    selected_option_ids = fields.Many2many('erpec.plan.option', string='Complementos contratados', copy=True)
    commercial_snapshot = fields.Json('Condiciones contratadas', readonly=True, copy=False)
    quoted_total = fields.Float('Total contratado USD', compute='_compute_quoted_total')

    @api.depends('commercial_snapshot')
    def _compute_quoted_total(self):
        for record in self:
            record.quoted_total = (record.commercial_snapshot or {}).get('total', 0)

    @api.constrains('renewal_of_id', 'customer_id', 'company_id', 'plan_id')
    def _validate_renewal(self):
        for record in self:
            previous=record.renewal_of_id
            if record.plan_id.company_id != record.company_id:
                raise ValidationError('El plan debe pertenecer al operador del contrato.')
            if previous and (previous==record or previous.customer_id!=record.customer_id or previous.company_id!=record.company_id or not previous.activated_at):
                raise ValidationError('La renovación debe conservar el cliente y operador de un contrato autorizado.')

    def _freeze_quote(self):
        for record in self:
            users = record.user_quantity or record.plan_id.max_users
            snapshot = record.plan_id._quote(record.period, users, record.selected_option_ids.ids)
            super(Subscription, record).write({'commercial_snapshot': snapshot, 'user_quantity': users})

    @api.model_create_multi
    def create(self, values_list):
        if any('commercial_snapshot' in v for v in values_list):
            raise AccessError('Las condiciones se calculan en el servidor.')
        records = super().create(values_list)
        records._freeze_quote()
        return records

    def write(self, values):
        if 'commercial_snapshot' in values:
            raise AccessError('Las condiciones contratadas son inmutables.')
        result = super().write(values)
        if set(values) & {'plan_id', 'period', 'user_quantity', 'selected_option_ids'}:
            self._freeze_quote()
        return result

    def check_capacity(self, resource, requested):
        self.ensure_one()
        if self.commercial_snapshot and resource == 'users':
            self.check_access('read')
            self.invalidate_recordset(['state'])
            if self.state != 'active' or type(requested) is not int or requested < 0 or requested > self.commercial_snapshot['users']:
                raise AccessError('La operación supera los usuarios contratados o el contrato no está vigente.')
            return True
        return super().check_capacity(resource, requested)
