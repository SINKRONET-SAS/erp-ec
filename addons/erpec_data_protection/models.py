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
"""
from odoo import api, fields, models
from odoo.exceptions import ValidationError

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
