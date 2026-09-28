"""Altas y renovaciones: referencias explícitas, cotización del servidor y progreso derivado."""
from odoo.addons.erpec_entitlements.capabilities import missing_requirements
import re
import uuid
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, Command
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.addons.erpec_suite.models.commercial import administrator

RUC_RE=re.compile(r'\d{13}')
EMAIL_RE=re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
REGIME_OPTIONS=[('general','General'),('rimpe_negocio_popular','RIMPE Negocio Popular'),('rimpe_emprendedor','RIMPE Emprendedor')]
SIGNUP_FIELDS={'company_name','company_vat','company_regime','street','contact_name','contact_email','contact_phone','plan_id','period','user_quantity','option_ids','request_key'}

class Customer(models.Model):
    _inherit='erpec.customer'
    subscription_ids=fields.One2many('erpec.subscription','customer_id',string='Contratos')
    provision_ids=fields.One2many('erpec.provision','customer_id',string='Instancia')

class SelfserviceRequest(models.Model):
    _name='erpec.selfservice.request'
    _description='Solicitud de alta por autoservicio'
    _inherit=['mail.thread']
    _order='id desc'
    reference=fields.Char('Referencia',required=True,copy=False,readonly=True,default=lambda self:uuid.uuid4().hex)
    request_key=fields.Char('Clave de solicitud',readonly=True,copy=False,default=lambda self:uuid.uuid4().hex,index=True)
    company_name=fields.Char('Razón social',required=True)
    company_vat=fields.Char('RUC',required=True)
    company_regime=fields.Selection(REGIME_OPTIONS,string='Régimen declarado',required=True)
    street=fields.Char('Dirección',required=True)
    contact_name=fields.Char('Nombre de contacto',required=True)
    contact_email=fields.Char('Correo de contacto',required=True)
    contact_phone=fields.Char('Teléfono')
    plan_id=fields.Many2one('erpec.plan',required=True,ondelete='restrict',string='Plan')
    customer_id=fields.Many2one('erpec.customer',readonly=True,copy=False,string='Cliente')
    subscription_id=fields.Many2one('erpec.subscription',readonly=True,copy=False,string='Contrato')
    payment_id=fields.Many2one('erpec.payphone.payment',readonly=True,copy=False,string='Pago')
    company_id=fields.Many2one(related='plan_id.company_id',store=True)
    state=fields.Selection([('draft','Registrada'),('awaiting_payment','Esperando pago'),('paid','Pagada, preparando acceso'),
        ('scheduled','Pagada, próxima renovación'),('provisioned','Instancia lista'),('failed','Requiere revisión')],compute='_compute_state',string='Estado')
    _sql_constraints=[('reference_unique','unique(reference)','Referencia duplicada.'),('request_key_unique','unique(request_key)','La solicitud ya está registrada.')]

    @api.depends('payment_id.state','payment_id.reconciled','subscription_id.activated_at','subscription_id.starts_on','customer_id.provision_ids.state','customer_id.provision_ids.subscription_id')
    def _compute_state(self):
        for record in self:
            payment=record.payment_id
            job=record.customer_id.provision_ids[:1]
            if payment.state in ('review','canceled') or (job.state=='failed' and job.subscription_id==record.subscription_id):
                record.state='failed'
            elif payment.state=='approved':
                record.state='scheduled' if record.subscription_id.starts_on>fields.Date.today() else 'provisioned' if job.state=='ready' and job.subscription_id==record.subscription_id else 'paid'
            else:
                record.state='awaiting_payment' if payment else 'draft'

    @api.constrains('company_vat','contact_email')
    def _validate_contact(self):
        for record in self:
            if not RUC_RE.fullmatch(record.company_vat or '') or not EMAIL_RE.fullmatch(record.contact_email or ''):
                raise ValidationError('Indica un RUC de 13 dígitos y un correo válido.')

    @api.model
    def create_from_signup(self,values):
        return self._create_signup(values)

    @api.model
    def _create_signup(self,values,owner_user=None,customer=None,previous=None):
        administrator(self.env)
        if set(values)-SIGNUP_FIELDS:
            raise ValidationError('Solicitud con campos no permitidos.')
        key=values.get('request_key') or uuid.uuid4().hex
        if not re.fullmatch('[a-f0-9]{32}',key):
            raise ValidationError('La clave de solicitud no es válida.')
        self.env.cr.execute('UPDATE res_company SET write_date=write_date WHERE id=%s RETURNING id',[self.env.company.id])
        self.env.cr.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',[key])
        existing=self.search([('request_key','=',key)],limit=1)
        if existing:
            if owner_user and existing.customer_id.portal_user_id!=owner_user:
                raise AccessError('La solicitud pertenece a otro titular.')
            return existing
        plan=self.env['erpec.plan'].browse(values.get('plan_id')).exists()
        if not plan or not plan.published or plan.company_id!=self.env.company:
            raise ValidationError('Selecciona un plan publicado del operador.')
        if owner_user and (not plan.erp or not plan.option_ids or not plan.fiscal_reviewed):
            raise ValidationError('La oferta todavía no está habilitada para contratación comercial.')
        quote=plan._quote(values.get('period','monthly'),values.get('user_quantity'),values.get('option_ids'))
        if quote['total']<=0:
            raise ValidationError('El importe a pagar debe ser positivo.')
        provider=self.env['erpec.payphone.provider'].search([('company_id','=',self.env.company.id)],limit=1)
        if not provider:
            raise UserError('El autoservicio no está configurado todavía: falta PayPhone.')
        if customer:
            if customer.company_id!=self.env.company or not owner_user or customer.portal_user_id!=owner_user:
                raise AccessError('La renovación pertenece a otro cliente.')
            self.env.cr.execute('UPDATE erpec_customer SET write_date=write_date WHERE id=%s RETURNING id',[customer.id])
            if not previous or previous.customer_id!=customer or not previous.activated_at:
                raise ValidationError('Selecciona el contrato autorizado que deseas renovar.')
            pending=self.search([('customer_id','=',customer.id),('subscription_id.renewal_of_id','=',previous.id)],limit=1)
            if pending and pending.payment_id.state!='canceled':
                return pending
        else:
            customer=self.env['erpec.customer'].create({'name':values['company_name'],'vat':values['company_vat'],
                'street':values['street'],'contact_name':values['contact_name'],'email':values['contact_email'],
                'phone':values.get('contact_phone'),'regime':values['company_regime'],'portal_user_id':owner_user.id if owner_user else False})
        request_values={k:v for k,v in values.items() if k in SIGNUP_FIELDS-{'period','user_quantity','option_ids','request_key'}}
        request_values.update(customer_id=customer.id,request_key=key)
        signup=self.create(request_values)
        today=fields.Date.today()
        start=max(today,previous.ends_on+timedelta(days=1)) if previous else today
        contract=self.env['erpec.subscription'].create({'name':'Autoservicio '+signup.reference,'company_id':self.env.company.id,'customer_id':customer.id,
            'plan_id':plan.id,'starts_on':start,'ends_on':start+relativedelta(months=quote['months'])-timedelta(days=1),
            'starts_on_activation':True,'renewal_of_id':previous.id if previous else False,
            'period':quote['period'],'user_quantity':quote['users'],'selected_option_ids':[Command.set(quote['option_ids'])],
            'billing_owner':'payphone_test','billing_reference':'Autoservicio web','authorization':'Solicitud '+signup.reference})
        payment=self.env['erpec.payphone.payment'].create({'subscription_id':contract.id,'provider_id':provider.id,
            'amount_without_tax':quote['untaxed'] if not quote['tax'] else 0,
            'amount_with_tax':quote['untaxed'] if quote['tax'] else 0,'tax':quote['tax']})
        signup.write({'subscription_id':contract.id,'payment_id':payment.id})
        payment.action_prepare()
        # El cron prepara después del commit HTTP. No procesa ni confirma otros pagos dentro de esta petición.
        return signup


class Plan(models.Model):
    _inherit='erpec.plan'

    @api.model
    def _public_offers(self,company):
        return self.sudo().search([('company_id','=',company.id),('published','=',True),('erp','=',True),
            ('fiscal_reviewed','=',True),('option_ids','!=',False),('price','>',0)],order='price,id').filtered(lambda plan: not missing_requirements(plan.option_ids.filtered(lambda line:line.kind=='included').mapped('capability_id.code')))

    @api.model
    def _retire_demo_offer(self):
        plans=self.sudo().search([('code','=','SS-DEMO'),('published','=',True)])
        if plans:
            plans.write({'published':False})
        return True
