"""Autoservicio de altas: formulario público que registra una solicitud y prepara un pago
PayPhone. La persona visitante nunca obtiene sesión ni permisos Odoo: toda escritura ocurre
en el controlador bajo el usuario administrador (sudo), igual que ya hace
`/payment/payphone/return`. A partir de un pago preparado, el camino ya probado y sin cambios
(`_receive_return` -> `_confirm` -> `_reconcile` -> `action_activate` ->
`erpec.provision._request`) se encarga de activar el contrato y encolar el aprovisionamiento.

Supuesto explícito de este primer incremento, no verificado contra ningún acuerdo comercial:
la suscripción de autoservicio dura un mes calendario desde la solicitud (`starts_on` a
`ends_on`). El proyecto no tiene hoy un campo de periodicidad en `erpec.plan`; si se decide
otra periodicidad, ajustar aquí.
"""
import re
import uuid

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

RUC_RE = re.compile(r'\d{13}')
EMAIL_RE = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')

REGIME_OPTIONS = [
    ('general', 'General'),
    ('rimpe_negocio_popular', 'RIMPE Negocio Popular'),
    ('rimpe_emprendedor', 'RIMPE Emprendedor'),
]

SIGNUP_FIELDS = {'company_name', 'company_vat', 'company_regime', 'street',
                  'contact_name', 'contact_email', 'contact_phone', 'plan_id'}


class SelfserviceRequest(models.Model):
    _name = 'erpec.selfservice.request'
    _description = 'Solicitud de alta por autoservicio'
    _inherit = ['mail.thread']
    _order = 'id desc'

    reference = fields.Char('Referencia', required=True, copy=False, readonly=True,
                             default=lambda self: uuid.uuid4().hex)
    company_name = fields.Char('Razón social', required=True)
    company_vat = fields.Char('RUC', required=True)
    company_regime = fields.Selection(REGIME_OPTIONS, string='Régimen tributario declarado', required=True,
                                       help='Declarado por quien completa el formulario; no se valida contra el SRI.')
    street = fields.Char('Dirección', required=True)
    contact_name = fields.Char('Nombre de contacto', required=True)
    contact_email = fields.Char('Correo de contacto', required=True)
    contact_phone = fields.Char('Teléfono de contacto')
    plan_id = fields.Many2one('erpec.plan', string='Plan solicitado', required=True, ondelete='restrict',
                               domain=[('published', '=', True)])
    subscription_id = fields.Many2one('erpec.subscription', readonly=True, copy=False)
    payment_id = fields.Many2one('erpec.payphone.payment', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Registrada'),
        ('awaiting_payment', 'Esperando pago'),
        ('paid', 'Pagada'),
        ('provisioned', 'Instancia lista'),
        ('failed', 'Requiere revisión'),
    ], default='draft', required=True, tracking=True)
    _sql_constraints = [('reference_unique', 'unique(reference)', 'Referencia de solicitud duplicada.')]

    @api.constrains('company_vat')
    def _check_vat(self):
        for record in self:
            if not RUC_RE.fullmatch(record.company_vat or ''):
                raise ValidationError('El RUC debe tener 13 dígitos numéricos.')

    @api.constrains('contact_email')
    def _check_email(self):
        for record in self:
            if not EMAIL_RE.fullmatch(record.contact_email or ''):
                raise ValidationError('Indica un correo de contacto válido.')

    @api.model
    def create_from_signup(self, values):
        """Único punto de entrada desde el controlador público. `values` debe venir ya
        saneado (regex de RUC/correo, campos no vacíos); aquí se revalida de todas formas
        como defensa adicional contra un uso directo del ORM que se salte el controlador."""
        if set(values) - SIGNUP_FIELDS:
            raise ValidationError('Solicitud con campos no permitidos.')
        plan = self.env['erpec.plan'].browse(values.get('plan_id')).exists()
        if not plan or not plan.published:
            raise ValidationError('Selecciona un plan publicado.')
        provider = self.env['erpec.payphone.provider'].search([('company_id', '=', self.env.company.id)], limit=1)
        if not provider:
            raise UserError('El autoservicio no está configurado todavía: falta la configuración de PayPhone.')
        signup_request = self.create(dict(values, plan_id=plan.id))
        today = fields.Date.today()
        subscription = self.env['erpec.subscription'].create({
            'name': 'Autoservicio %s' % signup_request.reference,
            'company_id': self.env.company.id,
            'plan_id': plan.id,
            'starts_on': today,
            'ends_on': today + relativedelta(months=1),
            'billing_owner': 'payphone_test',
            'billing_reference': 'Autoservicio web',
            'authorization': 'Autoservicio web, solicitud %s' % signup_request.reference,
        })
        payment = self.env['erpec.payphone.payment'].create({
            'subscription_id': subscription.id,
            'provider_id': provider.id,
            'amount_without_tax': plan.price,
        })
        signup_request.write({'subscription_id': subscription.id, 'payment_id': payment.id, 'state': 'awaiting_payment'})
        payment.action_prepare()
        # Fuerza el Prepare ahora en vez de esperar el minuto del cron, para poder
        # redirigir de inmediato al checkout dentro de la misma solicitud HTTP.
        self.env['erpec.payphone.payment']._cron_process()
        payment.invalidate_recordset(['state', 'checkout_url', 'last_error'])
        if payment.state != 'prepared':
            signup_request.state = 'failed'
            raise UserError('No se pudo iniciar el pago; inténtalo de nuevo en unos minutos.')
        return signup_request
