"""Datos y agregador anual para el anexo RDEP del SRI.

No genera XML ni presenta el anexo. Cubre solo los campos del Esquema RDEP
2023.xsd (SRI) con significado confirmado en el propio esquema descargado el
13-09-2026; ver docs/ALCANCE_ATS_RDEP.md. Participación de utilidades,
intereses ganados, salario digno, otros ingresos gravados, deducciones
desglosadas por categoría, residencia fiscal, país de residencia y los
indicadores benGalpg/enfcatastro quedan fuera de este incremento: su cálculo
o catálogo no está confirmado y no deben completarse con datos inventados.
"""
import json
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from .models import manager

DISABILITY_TYPES = [
    ('00', '00 (sin descripción en el esquema oficial SRI; confirmar en la ficha técnica antes de usar)'),
    ('01', '01 · Trabajador con discapacidad'),
    ('02', '02 · Actúa como sustituto de una persona con discapacidad'),
    ('03', '03 · Cónyuge, pareja en unión de hecho o hijo con discapacidad bajo su cuidado'),
    ('04', '04 · No aplica'),
]
DISABILITY_ID_TYPES = [('C', 'C · Cédula'), ('P', 'P · Pasaporte'), ('E', 'E · Extranjero'), ('N', 'N · No aplica')]
TREATY_APPLIES = [('SI', 'SI'), ('NO', 'NO'), ('NA', 'NA'), ('SD', 'SD · Sin dato')]
RDEP_TOTAL_KEYS = ('gross', 'thirteenth', 'fourteenth', 'reserve_iess', 'personal_iess', 'tax')


class Company(models.Model):
    _inherit = 'res.company'
    ec_rdep_employer_type = fields.Selection(
        [('PRIVADO_MIXTO', 'PRIVADO_MIXTO'), ('PUBLICO', 'PUBLICO')],
        string='Tipo de empleador (RDEP)',
        help='Campo tipoEmpleador del Esquema RDEP 2023.xsd del SRI.')
    ec_rdep_social_security_entity = fields.Selection(
        [('IESS', 'IESS'), ('ISSFA_ISSPOL', 'ISSFA_ISSPOL')],
        string='Ente de seguridad social (RDEP)',
        help='Campo enteSegSocial del Esquema RDEP 2023.xsd del SRI.')


class Employee(models.Model):
    _inherit = 'hr.employee'
    ec_rdep_disability_type = fields.Selection(
        DISABILITY_TYPES, string='Discapacidad (RDEP)',
        help='Campo discapTyp del Esquema RDEP 2023.xsd; etiquetas 01-04 tomadas de la documentación del propio esquema.')
    ec_rdep_disability_percentage = fields.Integer('Porcentaje de discapacidad (RDEP)')
    ec_rdep_disability_id_type = fields.Selection(DISABILITY_ID_TYPES, string='Identificación del titular de la discapacidad (RDEP)')
    ec_rdep_disability_id = fields.Char('Número de identificación del titular de la discapacidad (RDEP)')
    ec_rdep_dependents_count = fields.Integer(
        'Cargas para rebaja de gastos personales (RDEP)',
        help='Campo numCargRebGastPers del esquema SRI; admite de 0 a 5.')
    ec_rdep_treaty_applies = fields.Selection(TREATY_APPLIES, string='Aplica convenio doble imposición (RDEP)')

    @api.constrains('ec_rdep_disability_percentage')
    def _check_ec_rdep_disability_percentage(self):
        for employee in self:
            if employee.ec_rdep_disability_percentage and not 0 <= employee.ec_rdep_disability_percentage <= 100:
                raise ValidationError('El porcentaje de discapacidad del RDEP debe estar entre 0 y 100.')

    @api.constrains('ec_rdep_dependents_count')
    def _check_ec_rdep_dependents_count(self):
        for employee in self:
            if employee.ec_rdep_dependents_count and not 0 <= employee.ec_rdep_dependents_count <= 5:
                raise ValidationError('Las cargas para rebaja de gastos personales del RDEP van de 0 a 5.')


class RdepAnnex(models.Model):
    _name = 'erpec.payroll.rdep'
    _description = 'Agregador anual de nómina para el anexo RDEP (borrador interno, no presentable)'
    _inherit = ['mail.thread']
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    year = fields.Integer('Año fiscal', required=True)
    state = fields.Selection([('draft', 'Borrador')], default='draft', readonly=True)
    line_ids = fields.One2many('erpec.payroll.rdep.line', 'annex_id', readonly=True)
    pending_notice = fields.Text('Pendiente', readonly=True, default=(
        'Agregado interno de nómina para preparar el anexo RDEP; no genera XML ni se presenta ante el SRI. '
        'No incluye participación de utilidades, intereses ganados, salario digno, otros ingresos gravados, '
        'deducciones desglosadas por categoría, residencia fiscal ni país de residencia: su cálculo o catálogo '
        'no está confirmado en este incremento y no se completan con datos inventados. '
        'Revisa docs/ALCANCE_ATS_RDEP.md antes de continuar.'))
    _sql_constraints = [('company_year_unique', 'unique(company_id,year)', 'Ya existe un agregador para esta empresa y año.')]

    def action_build(self):
        self.ensure_one()
        manager(self.env)
        self.check_access('write')
        if not self.company_id.ec_rdep_employer_type or not self.company_id.ec_rdep_social_security_entity:
            raise ValidationError('Completa el tipo de empleador y el ente de seguridad social de la empresa antes de agregar.')
        periods = self.env['erpec.payroll.period'].search([
            ('company_id', '=', self.company_id.id), ('year', '=', self.year), ('state', '=', 'posted')])
        if not periods:
            raise ValidationError('No hay períodos contabilizados de nómina para esta empresa y año.')
        totals = {}
        for period in periods:
            for line in period.line_ids:
                result = json.loads(line.result or '{}')
                entry = totals.setdefault(line.employee_id.id, dict.fromkeys(RDEP_TOTAL_KEYS, 0.0))
                entry['months'] = entry.get('months', 0) + 1
                for key in RDEP_TOTAL_KEYS:
                    entry[key] += result.get(key, 0.0)
        self.line_ids.unlink()
        self.env['erpec.payroll.rdep.line'].create([
            {'annex_id': self.id, 'employee_id': employee_id, **values} for employee_id, values in totals.items()])
        return True


class RdepAnnexLine(models.Model):
    _name = 'erpec.payroll.rdep.line'
    _description = 'Totales anuales por empleado para el agregador RDEP'
    annex_id = fields.Many2one('erpec.payroll.rdep', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='annex_id.company_id', store=True)
    employee_id = fields.Many2one('hr.employee', required=True, readonly=True)
    months = fields.Integer('Períodos contabilizados', readonly=True)
    gross = fields.Float('Ingresos gravados acumulados (referencia suelSal)', readonly=True)
    thirteenth = fields.Float('Décimo tercero acumulado (decimTer)', readonly=True)
    fourteenth = fields.Float('Décimo cuarto acumulado (decimCuar)', readonly=True)
    reserve_iess = fields.Float('Fondo de reserva acumulado (fondoReserva)', readonly=True)
    personal_iess = fields.Float('Aporte personal IESS acumulado (apoPerIess)', readonly=True)
    tax = fields.Float('Impuesto a la renta retenido acumulado (referencia valRet)', readonly=True)
