"""Caso 11 (DI25-03): convenio de doble imposición (CDI). No hay una regla genérica: cada
tratado bilateral (España, Comunidad Andina/Decisión 578, Alemania, etc.) fija su propio
mecanismo y tope para rentas del trabajo dependiente. En vez de fabricar una tasa, este modelo
deja que el responsable tributario registre, por país y con su fuente documentada, si el
convenio exonera la renta en Ecuador o fija un tope de retención. Sin un tratado registrado
para el país de residencia del empleado, el cierre sigue bloqueado (tax_controls.py)."""
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from .models import manager

MECHANISMS = [
    ('exempt', 'Exento en Ecuador (potestad exclusiva del país de residencia)'),
    ('capped_rate', 'Tasa tope fijada por el tratado'),
]


class TaxTreaty(models.Model):
    _name = 'erpec.payroll.tax.treaty'
    _description = 'Convenio de doble imposición aplicable a rentas del trabajo dependiente (caso 11, DI25-03)'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    country_code = fields.Char('País (código RDEP)', required=True, help='Campo paisResidencia del esquema RDEP: código de 3 dígitos del catálogo del SRI.')
    country_name = fields.Char('País', help='Solo para referencia visual; no se usa en el cálculo.')
    mechanism = fields.Selection(MECHANISMS, 'Mecanismo', required=True)
    rate = fields.Float('Tasa tope (%)', help='Solo si el mecanismo es "Tasa tope fijada por el tratado"; en porcentaje (10 = 10 %).')
    reference = fields.Text('Fuente del tratado', required=True, help='Cita el tratado, decisión o artículo exacto (por ejemplo, "Decisión 578 CAN, art. 13" o el convenio bilateral con España, art. 15). No se acepta sin fuente.')
    active = fields.Boolean('Activo', default=True)
    note = fields.Text('Notas')
    _sql_constraints = [('country_unique', 'unique(company_id,country_code)', 'Ya existe un convenio registrado para este país en esta empresa.')]

    @api.constrains('country_code')
    def _check_country_code(self):
        for treaty in self:
            if not (len(treaty.country_code) == 3 and treaty.country_code.isdigit()):
                raise ValidationError('El código de país debe tener 3 dígitos, igual que paisResidencia del RDEP.')

    @api.constrains('mechanism', 'rate')
    def _check_rate(self):
        for treaty in self:
            if treaty.mechanism == 'capped_rate' and not 0 < treaty.rate <= 100:
                raise ValidationError('La tasa tope debe estar entre 0 y 100 % cuando el mecanismo es "Tasa tope fijada por el tratado".')
            if treaty.mechanism == 'exempt' and treaty.rate:
                raise ValidationError('El mecanismo "Exento" no lleva tasa tope.')

    @api.constrains('reference')
    def _check_reference(self):
        for treaty in self:
            if not (treaty.reference or '').strip():
                raise ValidationError('El convenio requiere la fuente exacta del tratado; no se registra sin ella.')

    @api.model_create_multi
    def create(self, vals_list):
        manager(self.env)
        return super().create(vals_list)

    def write(self, values):
        manager(self.env)
        return super().write(values)

    def unlink(self):
        manager(self.env)
        return super().unlink()

    @api.model
    def for_employee(self, employee):
        """Convenio activo para el país de residencia del empleado, o un recordset vacío."""
        if not employee.ec_rdep_residence_country:
            return self.browse()
        return self.search([
            ('company_id', '=', employee.company_id.id),
            ('country_code', '=', employee.ec_rdep_residence_country),
        ], limit=1)
