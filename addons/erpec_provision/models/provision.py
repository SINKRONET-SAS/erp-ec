"""Cola persistente con arrendamientos; solo el operador administra infraestructura.

Cada cliente listo corre en el servidor Odoo COMPARTIDO (scripts/shared-tenant-server.py),
no en un proceso ni puerto propio: un servicio dedicado por cliente en Render se cobra de
forma continua sin importar el uso. El servidor compartido rutea por subdominio
(`db_filter = ^erp_%d$`, ver docs/PLAN_HAIKY_MULTITENANT.md); ENDPOINT_SCHEME construye ese
subdominio en local (`*.localtest.me` resuelve públicamente a 127.0.0.1). En producción sería
`https://{instancia}.<dominio real>` sin puerto, detrás de Cloudflare.
"""
import hashlib
import hmac
import logging
import secrets
import uuid
import json
from urllib.parse import urlsplit
from odoo.addons.erpec_secrets import secret_store
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.erpec_suite.models.commercial import administrator

_logger = logging.getLogger(__name__)
ENDPOINT_SCHEME = 'http://{}.localtest.me:8200'
secret_store.register('erpec.provision','activation_encrypted',lambda record:'provision:%d:activation' % record.id)

class Subscription(models.Model):
    _inherit = 'erpec.subscription'

    def action_provision(self):
        self._lock_organization()
        self.check_capacity('companies', 1)
        job = self.env['erpec.provision']._request(self)
        return {'type':'ir.actions.act_window', 'res_model':'erpec.provision', 'res_id':job.id, 'view_mode':'form'}

class Provision(models.Model):
    _name = 'erpec.provision'
    _description = 'Instancia y trabajo durable'
    name = fields.Char('Identificador de instancia', readonly=True)
    company_id = fields.Many2one('res.company', string='Organización', required=True, readonly=True)
    customer_id = fields.Many2one('erpec.customer', string='Cliente', readonly=True, ondelete='restrict', index=True)
    subscription_id = fields.Many2one('erpec.subscription', string='Contrato', required=True, readonly=True, ondelete='restrict')
    state = fields.Selection([('queued','En cola'),('running','Preparando'),('ready','Disponible localmente'),('suspended','Suspendida'),('failed','Fallo: revisar y reintentar')], string='Estado', default='queued', readonly=True)
    attempts = fields.Integer('Intentos', readonly=True)
    lease_until = fields.Datetime('Reserva del trabajador hasta', readonly=True)
    lease_hash = fields.Char(readonly=True, groups='base.group_system')
    desired = fields.Selection([('start','Iniciar'),('stop','Suspender')], readonly=True)
    endpoint = fields.Char('Acceso local', readonly=True)
    last_error = fields.Char('Último error', readonly=True)
    applied_revision = fields.Char('Condiciones aplicadas',readonly=True)
    leased_revision = fields.Char(readonly=True)
    activation_encrypted = fields.Char(readonly=True,groups='base.group_system',copy=False)
    activation_expires = fields.Datetime('Activación válida hasta',readonly=True,copy=False)
    access_requested = fields.Boolean(readonly=True,copy=False)
    observed_users = fields.Integer('Usuarios internos observados',readonly=True)
    next_action = fields.Text('Siguiente acción', readonly=True, default='Ejecutar el trabajador Windows desde el equipo operador. Pendiente para nube: servidor y dominio/HTTPS, más proveedor y ambiente de verificación de pagos. Un alta manual no acredita un pago.')
    _sql_constraints = [('one_instance_customer','unique(customer_id)','Ya existe una instancia para este cliente.'),('instance_unique','unique(name)','El identificador de instancia ya existe.')]

    def init(self):
        # Compatibilidad: la instancia histórica sin cliente conserva su identidad y compañía.
        self.env.cr.execute('ALTER TABLE erpec_provision DROP CONSTRAINT IF EXISTS erpec_provision_one_instance_company')
        self.env.cr.execute('CREATE UNIQUE INDEX IF NOT EXISTS erpec_provision_legacy_company ON erpec_provision(company_id) WHERE customer_id IS NULL')

    @api.model_create_multi
    def create(self, values_list):
        raise AccessError('Solicita la instancia desde un contrato autorizado.')

    def write(self, values):
        raise AccessError('El estado de infraestructura solo se modifica mediante las acciones del trabajador.')

    def _update(self, values):
        return super().write(values)

    @api.model
    def _request(self, subscription):
        administrator(self.env)
        subscription.check_capacity('companies', 1)
        existing = self.search([('company_id','=',subscription.company_id.id), ('customer_id','=',subscription.customer_id.id or False)], limit=1)
        if existing:
            if existing.state == 'running':
                raise ValidationError('La instancia se está preparando. Espera al resultado antes de cambiar el contrato.')
            if existing.subscription_id != subscription:
                existing._update({'subscription_id':subscription.id,'attempts':0})
            _logger.info('Solicitud repetida conserva instancia correlationId=%s userId=%s', existing.name, self.env.uid)
            return existing
        return super(Provision, self).create({'name':uuid.uuid4().hex, 'company_id':subscription.company_id.id, 'customer_id':subscription.customer_id.id or False, 'subscription_id':subscription.id})

    def _desired_state(self):
        self.subscription_id.invalidate_recordset(['state','rights'])
        return 'start' if self.subscription_id.state == 'active' and self.subscription_id.plan_id.erp else 'stop'

    def _revision(self):
        self.ensure_one()
        contract=self.subscription_id
        return hashlib.sha256(json.dumps([contract.id,contract.commercial_snapshot,str(contract.ends_on)],sort_keys=True).encode()).hexdigest()

    def _activation_url(self):
        self.ensure_one()
        administrator(self.env)
        if not self.activation_encrypted or not self.activation_expires or self.activation_expires<fields.Datetime.now():
            raise ValidationError('El enlace de activación caducó; solicita uno nuevo desde el portal.')
        return secret_store.decrypt(self.activation_encrypted,'provision:%d:activation' % self.id).decode()

    def action_refresh_access(self):
        self.ensure_one()
        administrator(self.env)
        self.check_access('write')
        if self.state!='ready' or not self.customer_id:
            raise ValidationError('La instancia debe estar disponible para renovar el acceso.')
        self._update({'access_requested':True,'attempts':0})
        return True

    @api.model
    def _sync_current_contracts(self):
        today=fields.Date.today()
        contracts=self.env['erpec.subscription'].search([('customer_id','!=',False),('activated_at','!=',False),
            ('suspended','=',False),('starts_on','<=',today),('ends_on','>=',today),('plan_id.erp','=',True)])
        for contract in contracts:
            job=self.search([('customer_id','=',contract.customer_id.id)],limit=1)
            if not job or (job.state!='running' and job.subscription_id!=contract):
                self._request(contract)

    @api.model
    def claim_next(self):
        administrator(self.env)
        self._sync_current_contracts()
        now = fields.Datetime.now()
        # La búsqueda aplica reglas de compañía antes de tomar el bloqueo de fila.
        for job in self.search([], order='id'):
            self.env.cr.execute('SELECT id FROM erpec_provision WHERE id=%s FOR UPDATE SKIP LOCKED', [job.id])
            if not self.env.cr.fetchone():
                _logger.debug('Trabajo reservado por otro proceso correlationId=%s', job.name)
                continue
            job.invalidate_recordset()
            desired = job._desired_state()
            revision=job._revision()
            settled = (job.state == 'ready' and desired == 'start' and job.applied_revision==revision and not job.access_requested) or (job.state == 'suspended' and desired == 'stop')
            leased = job.state == 'running' and job.lease_until and job.lease_until > now
            if not leased and job.desired != desired:
                job._update({'attempts':0})
            if settled or leased or job.attempts >= 3:
                _logger.debug('Trabajo sin transición disponible correlationId=%s', job.name)
                continue
            token = secrets.token_urlsafe(32)
            job._update({'state':'running','attempts':job.attempts+1,'desired':desired,'lease_hash':hashlib.sha256(token.encode()).hexdigest(),'lease_until':now+timedelta(minutes=15),'leased_revision':revision,'last_error':False})
            snapshot=job.subscription_id.commercial_snapshot or {}
            return {'id':job.id,'instance':job.name,'company':job.customer_id.name or job.company_id.name,
                'customer':job.customer_id.reference or False,'desired':desired,'token':token,'revision':revision,
                'snapshot':snapshot,'ends_on':str(job.subscription_id.ends_on),'refresh_access':job.access_requested,
                'contact_email':job.customer_id.email or '', 'contact_name':job.customer_id.contact_name or '',
                'vat':job.customer_id.vat or '', 'street':job.customer_id.street or '',
                'max_users':snapshot.get('users',job.subscription_id.plan_id.max_users),
                'max_companies':snapshot.get('max_companies',job.subscription_id.plan_id.max_companies)}
        _logger.debug('No hay trabajos de aprovisionamiento pendientes')
        return False

    def finish(self, token, succeeded, details=None):
        self.ensure_one()
        administrator(self.env)
        self.check_access('write')
        self.env.cr.execute('SELECT id FROM erpec_provision WHERE id=%s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        if self.state != 'running' or not self.lease_until or self.lease_until <= fields.Datetime.now() or not hmac.compare_digest(self.lease_hash or '', hashlib.sha256(str(token).encode()).hexdigest()):
            raise AccessError('El resultado no corresponde a una reserva vigente.')
        if type(succeeded) is not bool:
            raise ValidationError('El resultado del trabajador debe ser booleano.')
        details=details or {}
        if succeeded and self.desired=='start' and self.customer_id and details.get('revision')!=self.leased_revision:
            raise ValidationError('El trabajador no confirmó la revisión contratada.')
        if details.get('activation_url'):
            target=urlsplit(details['activation_url'])
            expected=urlsplit(ENDPOINT_SCHEME.format(self.name))
            if target.scheme!=expected.scheme or target.netloc!=expected.netloc or target.path!='/web/reset_password' or target.username or target.password:
                raise ValidationError('La activación no pertenece a esta instancia.')
            self._update({'activation_encrypted':secret_store.encrypt(details['activation_url'].encode(),'provision:%d:activation' % self.id),
                          'activation_expires':fields.Datetime.now()+timedelta(hours=4)})
        state = ('ready' if self.desired == 'start' else 'suspended') if succeeded else 'failed'
        if succeeded and (self._desired_state() != self.desired or self._revision()!=self.leased_revision):
            state = 'queued'
        if succeeded:
            self._update({'applied_revision':self.leased_revision,'access_requested':False,'observed_users':details.get('active_users',self.observed_users)})
        self._update({'state':state,'lease_hash':False,'lease_until':False,'attempts':0 if succeeded else self.attempts,'endpoint':ENDPOINT_SCHEME.format(self.name) if state == 'ready' else False,'last_error':False if succeeded else 'PROVISION_FAILED: revisar el registro local del trabajador antes de reintentar.'})
        _logger.info('Resultado de aprovisionamiento state=%s correlationId=%s userId=%s', state, self.name, self.env.uid)
        return True

    def action_retry(self):
        self.ensure_one()
        administrator(self.env)
        self.check_access('write')
        self.env.cr.execute('SELECT id FROM erpec_provision WHERE id=%s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        if self.state != 'failed':
            raise ValidationError('Solo se reintentan manualmente trabajos fallidos.')
        self._update({'state':'queued','attempts':0,'last_error':False})
        return True
