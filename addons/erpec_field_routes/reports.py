"""Reporte de cumplimiento de visitas (B3): agrega días de ruta, paradas, marcas y excepciones
por vendedor y zona en un rango de fechas, para revisión gerencial. Exportable con la
exportación nativa de listas de Odoo (CSV/XLSX) desde `erpec.route.compliance.report.line`, y
con un reporte PDF imprimible (ver reports.xml)."""
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ComplianceReport(models.Model):
    _name = 'erpec.route.compliance.report'
    _description = 'Reporte de cumplimiento de visitas por vendedor y zona'
    _check_company_auto = True

    name = fields.Char(compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date('Desde', required=True)
    date_to = fields.Date('Hasta', required=True)
    line_ids = fields.One2many('erpec.route.compliance.report.line', 'report_id', readonly=True, string='Líneas')

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for report in self:
            report.name = 'Cumplimiento de visitas %s a %s' % (report.date_from or '', report.date_to or '')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for report in self:
            if report.date_from and report.date_to and report.date_from > report.date_to:
                raise ValidationError('La fecha inicial debe ser anterior o igual a la fecha final.')

    def action_build(self):
        self.ensure_one()
        self.check_access('write')
        days = self.env['erpec.route.day'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
            ('state', '!=', 'cancelled'),
        ])
        if not days:
            raise ValidationError('No hay días de ruta (planificados, en progreso o completados) en ese rango de fechas.')
        buckets = {}
        stop_key = {}
        for day in days:
            for stop in day.stop_ids:
                key = (day.employee_id.id, stop.site_id.id)
                stop_key[stop.id] = key
                entry = buckets.setdefault(key, dict(
                    planned=0, completed=0, omitted=0, unplanned=0,
                    marks_total=0, marks_within=0, pending_exceptions=0,
                ))
                if stop.planned:
                    entry['planned'] += 1
                else:
                    entry['unplanned'] += 1
                if stop.state == 'completed':
                    entry['completed'] += 1
                elif stop.state == 'omitted':
                    entry['omitted'] += 1
                for mark in (stop.checkin_mark_id, stop.checkout_mark_id):
                    if mark:
                        entry['marks_total'] += 1
                        if mark.within_geofence:
                            entry['marks_within'] += 1
        if stop_key:
            # geofence_violation/low_accuracy solo guardan mark_id (no stop_id); unplanned_visit/
            # omitted_visit solo guardan stop_id directamente -- hay que buscar por ambos caminos.
            exceptions = self.env['erpec.route.exception'].search([
                '|', ('stop_id', 'in', list(stop_key)), ('mark_id.stop_id', 'in', list(stop_key)),
                ('state', '=', 'pending'),
            ])
            for exception in exceptions:
                stop = exception.stop_id or exception.mark_id.stop_id
                key = stop_key.get(stop.id)
                if key:
                    buckets[key]['pending_exceptions'] += 1
        self.line_ids.unlink()
        self.env['erpec.route.compliance.report.line'].create([{
            'report_id': self.id, 'employee_id': employee_id, 'site_id': site_id,
            'planned_stops': entry['planned'], 'completed_stops': entry['completed'],
            'omitted_stops': entry['omitted'], 'unplanned_stops': entry['unplanned'],
            'completion_rate': (entry['completed'] / entry['planned'] * 100) if entry['planned'] else 0.0,
            'marks_total': entry['marks_total'], 'marks_within_geofence': entry['marks_within'],
            'within_geofence_rate': (entry['marks_within'] / entry['marks_total'] * 100) if entry['marks_total'] else 0.0,
            'pending_exceptions': entry['pending_exceptions'],
        } for (employee_id, site_id), entry in buckets.items()])
        return True


class ComplianceReportLine(models.Model):
    _name = 'erpec.route.compliance.report.line'
    _description = 'Línea de cumplimiento de visitas por vendedor y zona'
    _order = 'report_id, employee_id, site_id'

    report_id = fields.Many2one('erpec.route.compliance.report', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='report_id.company_id', store=True)
    date_from = fields.Date(related='report_id.date_from', store=True)
    date_to = fields.Date(related='report_id.date_to', store=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Vendedor')
    site_id = fields.Many2one('erpec.route.site', required=True, string='Zona/sitio')
    planned_stops = fields.Integer('Paradas planificadas')
    completed_stops = fields.Integer('Paradas completadas')
    omitted_stops = fields.Integer('Paradas omitidas')
    unplanned_stops = fields.Integer('Paradas no planificadas')
    completion_rate = fields.Float('Cumplimiento (%)')
    marks_total = fields.Integer('Marcas registradas')
    marks_within_geofence = fields.Integer('Marcas dentro de geocerca')
    within_geofence_rate = fields.Float('Dentro de geocerca (%)')
    pending_exceptions = fields.Integer('Excepciones pendientes')
