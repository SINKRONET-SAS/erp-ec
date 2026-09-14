"""Registro de Actividades de Tratamiento (RAT) y exclusión de correo comercial.

Herramienta de apoyo a la Ley Orgánica de Protección de Datos Personales (LOPDP),
Registro Oficial Suplemento N.° 459, 26-05-2021, investigada el 13-09-2026 (ver
docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md, sección LEGAL-06). Este módulo NO
declara cumplimiento legal: es un registro estructurado que la empresa debe
completar y mantener con criterio propio o asesoría legal. Las bases jurídicas
del campo `legal_basis` provienen del artículo 7 de la LOPDP citado en fuentes
secundarias consistentes entre sí (no del texto primario completo, que resistió
la extracción directa); confirmar contra el texto oficial antes de un caso real.
El umbral de obligatoriedad del RAT (≥100 empleados, citado en fuentes
secundarias sobre el Reglamento General) tampoco está verificado contra fuente
primaria: este registro puede llevarse independientemente de ese umbral, como
buena práctica.

El campo de exclusión de correo comercial en res.partner apoya el mecanismo de
exclusión exigido por la Ley de Comercio Electrónico, Firmas Electrónicas y
Mensajes de Datos (Ley 67, 2002) para mensajes periódicos/masivos. Este ERP no
envía correos reales (ver seed-ui-acceptance.py, que desactiva ir.mail_server);
el campo solo registra la preferencia para cuando el envío se habilite.

Segundo incremento (13-09-2026): procedimiento operativo de derechos del
titular y de notificación de brechas, tras confirmar los artículos primarios
en la segunda pasada de investigación (ver docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md,
sección LEGAL-06). `erpec.data.subject.request` registra y da seguimiento a
solicitudes de acceso/rectificación/eliminación/oposición/portabilidad/suspensión
(Arts. 13-17 y 19 LOPDP); el plazo de 15 días está confirmado por artículo para
acceso/rectificación/eliminación/oposición (Arts. 13-16) y se aplica también a
portabilidad/suspensión como práctica operativa uniforme, ya que el texto leído
no fija un plazo distinto para esos dos derechos. `erpec.data.breach.incident`
registra incidentes de seguridad y calcula los plazos de notificación
confirmados en los Arts. 43 (5 días responsable→Autoridad/ARCOTEL, 2 días
encargado→responsable) y 46 (3 días al titular si hay riesgo para sus derechos
fundamentales, salvo una de las tres excepciones tasadas del propio Art. 46).
Ningún correo real se envía: los recordatorios usan `mail.activity.mixin`
(tareas internas visibles en Actividades), no el servidor de correo.
"""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

RIGHTS_REQUEST_TYPES = [
    ('acceso', 'Acceso (Art. 13 LOPDP)'),
    ('rectificacion', 'Rectificación o actualización (Art. 14 LOPDP)'),
    ('eliminacion', 'Eliminación (Art. 15 LOPDP)'),
    ('oposicion', 'Oposición (Art. 16 LOPDP)'),
    ('portabilidad', 'Portabilidad (Art. 17 LOPDP)'),
    ('suspension', 'Suspensión del tratamiento (Art. 19 LOPDP)'),
]
RIGHTS_REQUEST_DEADLINE_DAYS = 15

BREACH_DISCOVERED_BY = [
    ('responsable', 'Responsable del tratamiento'),
    ('encargado', 'Encargado del tratamiento'),
]
BREACH_TITULAR_EXCEPTIONS = [
    ('proteccion_previa', 'Medidas de protección previas ya mitigan el riesgo (Art. 46 LOPDP)'),
    ('riesgo_descartado', 'Riesgo descartado con garantías suficientes (Art. 46 LOPDP)'),
    ('esfuerzo_desproporcionado', 'Esfuerzo desproporcionado, sujeto a revisión de la Autoridad (Art. 46 LOPDP)'),
]
BREACH_ENCARGADO_NOTICE_DAYS = 2
BREACH_AUTHORITY_NOTICE_DAYS = 5
BREACH_TITULAR_NOTICE_DAYS = 3

LEGAL_BASIS = [
    ('consentimiento', 'Consentimiento (Art. 7 LOPDP)'),
    ('obligacion_legal', 'Obligación legal (Art. 7 LOPDP)'),
    ('necesidad_contractual', 'Necesidad contractual o precontractual (Art. 7 LOPDP)'),
    ('interes_vital', 'Interés vital del titular (Art. 7 LOPDP)'),
    ('interes_publico', 'Interés público (Art. 7 LOPDP)'),
    ('fuente_publica', 'Fuente de acceso público (Art. 7 LOPDP)'),
    ('interes_legitimo', 'Interés legítimo del responsable (Art. 7 LOPDP)'),
]


class DataProcessingActivity(models.Model):
    _name = 'erpec.data.processing.activity'
    _description = 'Registro de actividad de tratamiento de datos personales (LOPDP)'
    _inherit = ['mail.thread']
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    name = fields.Char('Actividad de tratamiento', required=True)
    purpose = fields.Text('Finalidad', required=True, help='Para qué se tratan los datos de esta actividad; debe ser específica, no genérica.')
    legal_basis = fields.Selection(LEGAL_BASIS, string='Base legal', required=True, help='Art. 7 de la LOPDP. Confirmar contra el texto oficial antes de un caso real; ver docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md.')
    data_subjects = fields.Text('Categorías de titulares', required=True, help='Por ejemplo: empleados, clientes, proveedores.')
    data_categories = fields.Text('Categorías de datos tratados', required=True)
    special_category_data = fields.Boolean('Incluye datos sensibles', help='Salud, biométricos u otra categoría especial. Confirmar la lista exacta de categorías especiales contra el texto oficial de la LOPDP antes de declarar que una actividad no las incluye.')
    recipients = fields.Text('Destinatarios', help='A quién se comunican estos datos, dentro o fuera de la empresa.')
    retention_period = fields.Char('Plazo de conservación')
    security_measures = fields.Text('Medidas de seguridad aplicadas')
    responsible_id = fields.Many2one('res.users', string='Responsable del tratamiento', required=True)
    cross_border_transfer = fields.Boolean('Transferencia internacional')
    transfer_country = fields.Char('País destino de la transferencia')
    transfer_mechanism = fields.Text('Mecanismo/base legal de la transferencia', help='Consentimiento específico, declaración de adecuación de la SPDP u otro mecanismo lícito. Las transferencias internacionales deben registrarse además en el RNPD (registro público de la SPDP), fuera del alcance de este módulo.')
    state = fields.Selection([('draft', 'Borrador'), ('active', 'Vigente'), ('under_review', 'En revisión')], default='draft', required=True, tracking=True)
    notes = fields.Text('Notas')
    _sql_constraints = [('name_company_unique', 'unique(company_id,name)', 'Ya existe una actividad de tratamiento con este nombre en la empresa.')]

    @api.constrains('cross_border_transfer', 'transfer_country')
    def _check_transfer_country(self):
        for activity in self:
            if activity.cross_border_transfer and not activity.transfer_country:
                raise ValidationError('Indica el país destino de la transferencia internacional.')


class Partner(models.Model):
    _inherit = 'res.partner'
    ec_marketing_email_opt_out = fields.Boolean(
        'Excluido de correo comercial', tracking=True,
        help='Mecanismo de exclusión de mensajes periódicos/masivos exigido por la Ley de Comercio Electrónico, '
             'Firmas Electrónicas y Mensajes de Datos (Ley 67, 2002). Este ERP no envía correos reales todavía; '
             'este campo solo registra la preferencia declarada por el contacto.')
    ec_marketing_email_opt_out_date = fields.Date('Fecha de exclusión', readonly=True)

    def action_ec_mark_marketing_opt_out(self):
        self.write({'ec_marketing_email_opt_out': True, 'ec_marketing_email_opt_out_date': fields.Date.today()})
        return True


class DataSubjectRequest(models.Model):
    _name = 'erpec.data.subject.request'
    _description = 'Solicitud de derechos del titular (LOPDP, Arts. 13-19)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_date desc, id desc'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    name = fields.Char('Referencia', required=True, help='Descripción corta, por ejemplo "Acceso - Juan Pérez".')
    request_type = fields.Selection(RIGHTS_REQUEST_TYPES, string='Derecho solicitado', required=True, tracking=True)
    requester_name = fields.Char('Nombre del titular', required=True)
    requester_identification = fields.Char(
        'Identificación del titular',
        help='Cédula, RUC o pasaporte. Sirve para verificar la identidad antes de responder, '
             'lo que evita un ejercicio abusivo del derecho (Art. 13 LOPDP).')
    partner_id = fields.Many2one('res.partner', string='Contacto vinculado')
    identity_verified = fields.Boolean('Identidad verificada', tracking=True)
    description = fields.Text('Detalle de la solicitud')
    received_date = fields.Date('Fecha de recepción', required=True, default=fields.Date.context_today)
    deadline_date = fields.Date(
        'Plazo de respuesta', compute='_compute_deadline_date', store=True,
        help='15 días desde la recepción. Confirmado por artículo para acceso/rectificación/eliminación/oposición '
             '(Arts. 13-16 LOPDP); se aplica el mismo plazo a portabilidad y suspensión como práctica operativa '
             'uniforme, ya que el texto leído no fija uno distinto para esos dos derechos.')
    response_date = fields.Date('Fecha de respuesta')
    response_notes = fields.Text('Respuesta entregada')
    exception_notes = fields.Text(
        'Excepción aplicada',
        help='Motivo si se rechaza o limita el ejercicio del derecho, conforme a las excepciones tasadas del Art. 18 LOPDP.')
    responsible_id = fields.Many2one('res.users', string='Responsable de atención', required=True, default=lambda self: self.env.user)
    state = fields.Selection([
        ('new', 'Registrada'),
        ('in_progress', 'En trámite'),
        ('answered', 'Respondida'),
        ('rejected', 'Rechazada'),
        ('closed', 'Cerrada'),
    ], default='new', required=True, tracking=True)
    is_overdue = fields.Boolean('Vencida', compute='_compute_is_overdue')
    notes = fields.Text('Notas internas')

    @api.depends('received_date')
    def _compute_deadline_date(self):
        for request in self:
            request.deadline_date = (request.received_date + timedelta(days=RIGHTS_REQUEST_DEADLINE_DAYS)) if request.received_date else False

    @api.depends('deadline_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for request in self:
            request.is_overdue = bool(
                request.deadline_date and request.deadline_date < today
                and request.state not in ('answered', 'rejected', 'closed'))

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        for request in requests:
            request.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=request.deadline_date,
                summary=_('Responder solicitud de derecho del titular (%s)') % dict(RIGHTS_REQUEST_TYPES).get(request.request_type),
                user_id=request.responsible_id.id or self.env.uid,
            )
        return requests

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_mark_answered(self):
        for request in self:
            if not request.identity_verified:
                raise UserError(_('Verifica la identidad del titular antes de responder la solicitud.'))
            if not request.response_notes:
                raise UserError(_('Registra la respuesta entregada antes de marcar la solicitud como respondida.'))
        self.write({'state': 'answered', 'response_date': fields.Date.context_today(self)})

    def action_reject(self):
        for request in self:
            if not request.identity_verified:
                raise UserError(_('Verifica la identidad del titular antes de rechazar la solicitud.'))
            if not request.exception_notes:
                raise UserError(_('Indica la excepción aplicada (Art. 18 LOPDP) antes de rechazar la solicitud.'))
        self.write({'state': 'rejected', 'response_date': fields.Date.context_today(self)})

    def action_close(self):
        for request in self:
            if request.state not in ('answered', 'rejected'):
                raise UserError(_('Solo se puede cerrar una solicitud ya respondida o rechazada.'))
        self.write({'state': 'closed'})


class DataBreachIncident(models.Model):
    _name = 'erpec.data.breach.incident'
    _description = 'Incidente de vulneración de seguridad de datos personales (LOPDP, Arts. 43 y 46)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'detected_date desc, id desc'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    name = fields.Char('Referencia', required=True)
    discovered_by = fields.Selection(BREACH_DISCOVERED_BY, string='Detectado por', required=True, default='responsable', tracking=True)
    detected_date = fields.Datetime('Fecha en que se tuvo constancia', required=True, default=fields.Datetime.now)
    description = fields.Text('Qué ocurrió', required=True)
    affected_data_categories = fields.Text('Categorías de datos afectadas')
    affected_subjects_estimate = fields.Char('Titulares afectados (estimado)')
    containment_measures = fields.Text('Medidas de contención aplicadas')
    internal_risk_triage = fields.Selection(
        [('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta')], string='Riesgo interno estimado',
        help='Triaje interno de este ERP; no es la calificación legal de gravedad, que corresponde a la SPDP.')
    risk_to_rights = fields.Boolean(
        'Riesgo para los derechos fundamentales del titular', tracking=True,
        help='Si aplica, activa la obligación de notificar al titular (Art. 46 LOPDP).')

    encargado_notice_date = fields.Datetime('Fecha de aviso del encargado al responsable')
    encargado_notice_deadline = fields.Datetime('Plazo de aviso del encargado', compute='_compute_deadlines', store=True)

    authority_notified_date = fields.Datetime('Fecha de notificación a la Autoridad/ARCOTEL')
    authority_notice_deadline = fields.Datetime('Plazo de notificación a la Autoridad', compute='_compute_deadlines', store=True)

    titular_notified_date = fields.Datetime('Fecha de notificación al titular')
    titular_notice_deadline = fields.Datetime('Plazo de notificación al titular', compute='_compute_deadlines', store=True)
    titular_notice_exception = fields.Selection(BREACH_TITULAR_EXCEPTIONS, string='Excepción aplicada a la notificación al titular')

    responsible_id = fields.Many2one('res.users', string='Responsable del caso', required=True, default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Registrado'),
        ('assessing', 'En evaluación'),
        ('notified', 'Notificado'),
        ('closed', 'Cerrado'),
    ], default='draft', required=True, tracking=True)
    is_authority_notice_overdue = fields.Boolean('Notificación a la Autoridad vencida', compute='_compute_overdue')
    is_titular_notice_overdue = fields.Boolean('Notificación al titular vencida', compute='_compute_overdue')
    notes = fields.Text('Notas internas')

    @api.depends('detected_date', 'discovered_by', 'encargado_notice_date', 'risk_to_rights')
    def _compute_deadlines(self):
        for incident in self:
            incident.encargado_notice_deadline = (
                incident.detected_date + timedelta(days=BREACH_ENCARGADO_NOTICE_DAYS)
                if (incident.detected_date and incident.discovered_by == 'encargado') else False)
            authority_start = (
                incident.encargado_notice_date
                if (incident.discovered_by == 'encargado' and incident.encargado_notice_date)
                else incident.detected_date)
            incident.authority_notice_deadline = (
                authority_start + timedelta(days=BREACH_AUTHORITY_NOTICE_DAYS) if authority_start else False)
            incident.titular_notice_deadline = (
                incident.detected_date + timedelta(days=BREACH_TITULAR_NOTICE_DAYS)
                if (incident.detected_date and incident.risk_to_rights) else False)

    @api.depends('authority_notice_deadline', 'authority_notified_date', 'titular_notice_deadline',
                 'titular_notified_date', 'titular_notice_exception', 'risk_to_rights', 'state')
    def _compute_overdue(self):
        now = fields.Datetime.now()
        for incident in self:
            incident.is_authority_notice_overdue = bool(
                incident.authority_notice_deadline and not incident.authority_notified_date
                and incident.authority_notice_deadline < now and incident.state != 'closed')
            incident.is_titular_notice_overdue = bool(
                incident.risk_to_rights and incident.titular_notice_deadline and not incident.titular_notified_date
                and not incident.titular_notice_exception and incident.titular_notice_deadline < now
                and incident.state != 'closed')

    @api.constrains('encargado_notice_date', 'detected_date')
    def _check_encargado_notice_date(self):
        for incident in self:
            if incident.encargado_notice_date and incident.detected_date and incident.encargado_notice_date < incident.detected_date:
                raise ValidationError(_('La fecha de aviso del encargado no puede ser anterior a la fecha en que se detectó el incidente.'))

    @api.model_create_multi
    def create(self, vals_list):
        incidents = super().create(vals_list)
        for incident in incidents:
            if incident.authority_notice_deadline:
                incident.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=incident.authority_notice_deadline.date(),
                    summary=_('Notificar la vulneración a la Autoridad de Protección de Datos (Art. 43 LOPDP)'),
                    user_id=incident.responsible_id.id or self.env.uid,
                )
        return incidents

    def action_start_assessment(self):
        self.write({'state': 'assessing'})

    def action_notify_authority(self):
        for incident in self:
            incident.write({'authority_notified_date': fields.Datetime.now()})
            if incident.state == 'draft':
                incident.state = 'assessing'
            if incident.state == 'assessing':
                incident.state = 'notified'

    def action_notify_titular(self):
        self.write({'titular_notified_date': fields.Datetime.now()})

    def action_close(self):
        for incident in self:
            if not incident.authority_notified_date:
                raise UserError(_('Registra la notificación a la Autoridad antes de cerrar el incidente.'))
            if incident.risk_to_rights and not incident.titular_notified_date and not incident.titular_notice_exception:
                raise UserError(_('Notifica al titular o registra la excepción aplicada (Art. 46 LOPDP) antes de cerrar.'))
        self.write({'state': 'closed'})
