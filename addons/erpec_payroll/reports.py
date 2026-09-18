"""Modelo de agregación para la ficha de beneficios acumulados (A2): mismo patrón ya usado en
annex_rdep.py (Rdep.action_build) -- suma resultados JSON de erpec.payroll.line a través de los
períodos contabilizados ('posted') de un año/empresa, por empleado. No se reutiliza el modelo
RDEP directamente porque ese agregador tiene su propio ciclo de vida (generación de XML anual
para el SRI) y sus campos son específicos de ese anexo, no de un reporte interno de beneficios."""
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .models import manager

BENEFIT_KEYS = ('thirteenth', 'fourteenth', 'vacation', 'reserve_iess', 'gross', 'net', 'cost')


class BenefitSummary(models.Model):
    _name = 'erpec.payroll.benefit.summary'
    _description = 'Ficha de beneficios acumulados por empleado'
    _order = 'year desc'

    name = fields.Char(compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    year = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    line_ids = fields.One2many('erpec.payroll.benefit.summary.line', 'summary_id', readonly=True)

    @api.depends('company_id', 'year')
    def _compute_name(self):
        for summary in self:
            summary.name = 'Beneficios acumulados %s — %s' % (summary.year, summary.company_id.name)

    def action_build(self):
        self.ensure_one()
        manager(self.env)
        self.check_access('write')
        periods = self.env['erpec.payroll.period'].search([
            ('company_id', '=', self.company_id.id), ('year', '=', self.year), ('state', '=', 'posted')], order='id')
        if not periods:
            raise ValidationError('No hay períodos contabilizados de nómina para esta empresa y año.')
        totals = {}
        for period in periods:
            for line in period.line_ids:
                result = json.loads(line.result or '{}')
                entry = totals.setdefault(line.employee_id.id, dict.fromkeys(BENEFIT_KEYS, 0.0))
                entry['months'] = entry.get('months', 0) + 1
                for key in BENEFIT_KEYS:
                    entry[key] += result.get(key, 0.0)
        self.line_ids.unlink()
        self.env['erpec.payroll.benefit.summary.line'].create([
            {'summary_id': self.id, 'employee_id': employee_id, **values}
            for employee_id, values in totals.items()
        ])
        return True


class BenefitSummaryLine(models.Model):
    _name = 'erpec.payroll.benefit.summary.line'
    _description = 'Línea de la ficha de beneficios acumulados'
    summary_id = fields.Many2one('erpec.payroll.benefit.summary', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    months = fields.Integer('Meses contabilizados')
    thirteenth = fields.Float('Décimo tercero acumulado')
    fourteenth = fields.Float('Décimo cuarto acumulado')
    vacation = fields.Float('Vacaciones acumuladas')
    reserve_iess = fields.Float('Fondo de reserva acumulado')
    gross = fields.Float('Ingresos brutos acumulados')
    net = fields.Float('Neto acumulado')
    cost = fields.Float('Costo de empresa acumulado')
