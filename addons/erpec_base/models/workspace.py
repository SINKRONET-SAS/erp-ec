from odoo import fields, models


class Workspace(models.Model):
    _name = 'erpec.workspace'
    _description = 'Estado de implementación ERP EC'

    name = fields.Char(string='Nombre', required=True, default='ERP EC')
    company_id = fields.Many2one('res.company', string='Empresa', required=True, default=lambda self: self.env.company)
    platform = fields.Char(string='Plataforma', default='Windows nativo', readonly=True)
    integration_status = fields.Selection([('pending', 'Pendiente de implementación y verificación')], string='Estado de integración', default='pending', readonly=True)
    next_action = fields.Text(string='Siguiente acción', default='Configurar suscripción, vínculos por empresa y conectores. El entorno local no acredita autorización fiscal ni integración productiva.', readonly=True)
    _sql_constraints = [('company_unique', 'unique(company_id)', 'Ya existe una configuración para esta empresa.')]
