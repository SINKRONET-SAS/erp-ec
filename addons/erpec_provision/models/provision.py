"""Cola persistente con arrendamientos; solo el operador administra infraestructura."""
import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.erpec_suite.models.commercial import administrator

_logger = logging.getLogger(__name__)

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
    subscription_id = fields.Many2one('erpec.subscription', string='Contrato', required=True, readonly=True, ondelete='restrict')
    state = fields.Selection([('queued','En cola'),('running','Preparando'),('ready','Disponible localmente'),('suspended','Suspendida'),('failed','Fallo: revisar y reintentar')], string='Estado', default='queued', readonly=True)
    attempts = fields.Integer('Intentos', readonly=True)
    lease_until = fields.Datetime('Reserva del trabajador hasta', readonly=True)
    lease_hash = fields.Char(readonly=True, groups='base.group_system')
    desired = fields.Selection([('start','Iniciar'),('stop','Suspender')], readonly=True)
    endpoint = fields.Char('Acceso local', readonly=True)
    last_error = fields.Char('Último error', readonly=True)
    next_action = fields.Text('Siguiente acción', readonly=True, default='Ejecutar el trabajador Windows desde el equipo operador. Pendiente para nube: servidor y dominio/HTTPS, más proveedor y ambiente de verificación de pagos. Un alta manual no acredita un pago.')
    _sql_constraints = [('one_instance_company','unique(company_id)','Ya existe una instancia para esta organización.'),('instance_unique','unique(name)','El identificador de instancia ya existe.')]

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
        existing = self.search([('company_id','=',subscription.company_id.id)], limit=1)
        if existing:
            if existing.state == 'running':
                raise ValidationError('La instancia se está preparando. Espera al resultado antes de cambiar el contrato.')
            existing._update({'subscription_id':subscription.id})
            _logger.info('Solicitud repetida conserva instancia correlationId=%s userId=%s', existing.name, self.env.uid)
            return existing
        return super(Provision, self).create({'name':uuid.uuid4().hex, 'company_id':subscription.company_id.id, 'subscription_id':subscription.id})

    def _desired_state(self):
        self.subscription_id.invalidate_recordset(['state','rights'])
        return 'start' if self.subscription_id.state == 'active' and self.subscription_id.plan_id.erp else 'stop'

    @api.model
    def claim_next(self):
        administrator(self.env)
        now = fields.Datetime.now()
        # La búsqueda aplica reglas de compañía antes de tomar el bloqueo de fila.
        for job in self.search([], order='id'):
            self.env.cr.execute('SELECT id FROM erpec_provision WHERE id=%s FOR UPDATE SKIP LOCKED', [job.id])
            if not self.env.cr.fetchone():
                _logger.debug('Trabajo reservado por otro proceso correlationId=%s', job.name)
                continue
            job.invalidate_recordset()
            desired = job._desired_state()
            settled = (job.state == 'ready' and desired == 'start') or (job.state == 'suspended' and desired == 'stop')
            leased = job.state == 'running' and job.lease_until and job.lease_until > now
            if not leased and job.desired != desired:
                job._update({'attempts':0})
            if settled or leased or job.attempts >= 3:
                _logger.debug('Trabajo sin transición disponible correlationId=%s', job.name)
                continue
            token = secrets.token_urlsafe(32)
            job._update({'state':'running','attempts':job.attempts+1,'desired':desired,'lease_hash':hashlib.sha256(token.encode()).hexdigest(),'lease_until':now+timedelta(minutes=15),'last_error':False})
            return {'id':job.id,'instance':job.name,'company':job.company_id.name,'desired':desired,'token':token,'max_users':job.subscription_id.plan_id.max_users,'max_companies':job.subscription_id.plan_id.max_companies}
        _logger.debug('No hay trabajos de aprovisionamiento pendientes')
        return False

    def finish(self, token, succeeded):
        self.ensure_one()
        administrator(self.env)
        self.check_access('write')
        self.env.cr.execute('SELECT id FROM erpec_provision WHERE id=%s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        if self.state != 'running' or not self.lease_until or self.lease_until <= fields.Datetime.now() or not hmac.compare_digest(self.lease_hash or '', hashlib.sha256(str(token).encode()).hexdigest()):
            raise AccessError('El resultado no corresponde a una reserva vigente.')
        if type(succeeded) is not bool:
            raise ValidationError('El resultado del trabajador debe ser booleano.')
        state = ('ready' if self.desired == 'start' else 'suspended') if succeeded else 'failed'
        if succeeded and self._desired_state() != self.desired:
            state = 'queued'
        self._update({'state':state,'lease_hash':False,'lease_until':False,'attempts':0 if succeeded else self.attempts,'endpoint':f'http://127.0.0.1:{8180+self.id}' if state == 'ready' else False,'last_error':False if succeeded else 'PROVISION_FAILED: revisar el registro local del trabajador antes de reintentar.'})
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
