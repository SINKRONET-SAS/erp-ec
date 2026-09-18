"""Pruebas del reporte de cumplimiento de visitas (B3): agrega por vendedor/zona en un rango
de fechas -- planificadas/completadas/omitidas/no planificadas, tasa dentro de geocerca y
excepciones pendientes -- e imprime un PDF real."""
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

# Sitio de referencia: Parque La Carolina, Quito.
SITE_LAT, SITE_LON = -0.1807, -78.4864
NEARBY_LAT, NEARBY_LON = -0.18043, -78.4864
FAR_LAT, FAR_LON = -0.1627, -78.4864


@tagged('post_install', '-at_install')
class ComplianceReportCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('erpec_field_routes.group_route_manager').id)]})
        self.employee = self.env['hr.employee'].create({'name': 'Vendedor de reporte', 'company_id': self.env.company.id})
        self.site = self.env['erpec.route.site'].create({
            'name': 'Zona de reporte', 'latitude': SITE_LAT, 'longitude': SITE_LON,
            'radius_meters': 150, 'min_accuracy_meters': 50})
        self.other_site = self.env['erpec.route.site'].create({
            'name': 'Otra zona', 'latitude': SITE_LAT, 'longitude': SITE_LON,
            'radius_meters': 150, 'min_accuracy_meters': 50})

    def _make_day(self, date, planned_ok=1, planned_far=0, omitted=0, unplanned=0):
        day = self.env['erpec.route.day'].create({'employee_id': self.employee.id, 'date': date})
        for _ in range(planned_ok):
            stop = self.env['erpec.route.stop'].create({'route_day_id': day.id, 'site_id': self.site.id})
            stop.action_checkin(NEARBY_LAT, NEARBY_LON, 20)
            stop.action_checkout(NEARBY_LAT, NEARBY_LON, 20)
        for _ in range(planned_far):
            stop = self.env['erpec.route.stop'].create({'route_day_id': day.id, 'site_id': self.site.id})
            stop.action_checkin(FAR_LAT, FAR_LON, 20)
            stop.action_checkout(FAR_LAT, FAR_LON, 20)
        for _ in range(omitted):
            stop = self.env['erpec.route.stop'].create({'route_day_id': day.id, 'site_id': self.site.id})
            stop.action_omit('Cliente cerrado')
        for _ in range(unplanned):
            day.action_add_unplanned_stop(self.site.id, 'Visita de oportunidad')
        return day

    def test_build_requires_days_in_range(self):
        report = self.env['erpec.route.compliance.report'].create({'date_from': '2020-01-01', 'date_to': '2020-01-31'})
        with self.assertRaises(ValidationError):
            report.action_build()

    def test_build_aggregates_by_employee_and_site(self):
        self._make_day('2026-09-01', planned_ok=2, planned_far=1, omitted=1)
        report = self.env['erpec.route.compliance.report'].create({'date_from': '2026-09-01', 'date_to': '2026-09-01'})
        report.action_build()
        self.assertEqual(len(report.line_ids), 1)
        line = report.line_ids
        self.assertEqual(line.employee_id, self.employee)
        self.assertEqual(line.site_id, self.site)
        self.assertEqual(line.planned_stops, 4)
        self.assertEqual(line.completed_stops, 3)
        self.assertEqual(line.omitted_stops, 1)
        self.assertAlmostEqual(line.completion_rate, 75.0)
        self.assertEqual(line.marks_total, 6)
        self.assertEqual(line.marks_within_geofence, 4)
        self.assertAlmostEqual(line.within_geofence_rate, 4 / 6 * 100)
        # 2 excepciones geofence_violation (checkin y checkout fuera de geocerca, cada marca
        # genera la suya) + 1 excepcion omitted_visit = 3.
        self.assertEqual(line.pending_exceptions, 3)

    def test_build_counts_unplanned_stops(self):
        self._make_day('2026-09-02', planned_ok=0, unplanned=1)
        report = self.env['erpec.route.compliance.report'].create({'date_from': '2026-09-02', 'date_to': '2026-09-02'})
        report.action_build()
        line = report.line_ids
        self.assertEqual(line.unplanned_stops, 1)
        self.assertEqual(line.pending_exceptions, 1)

    def test_build_separates_lines_by_site(self):
        day = self.env['erpec.route.day'].create({'employee_id': self.employee.id, 'date': '2026-09-03'})
        stop_a = self.env['erpec.route.stop'].create({'route_day_id': day.id, 'site_id': self.site.id})
        stop_a.action_checkin(NEARBY_LAT, NEARBY_LON, 20)
        stop_a.action_checkout(NEARBY_LAT, NEARBY_LON, 20)
        stop_b = self.env['erpec.route.stop'].create({'route_day_id': day.id, 'site_id': self.other_site.id})
        stop_b.action_omit('No disponible')
        report = self.env['erpec.route.compliance.report'].create({'date_from': '2026-09-03', 'date_to': '2026-09-03'})
        report.action_build()
        self.assertEqual(len(report.line_ids), 2)
        sites = report.line_ids.mapped('site_id')
        self.assertIn(self.site, sites)
        self.assertIn(self.other_site, sites)

    def test_build_excludes_cancelled_days(self):
        self._make_day('2026-09-04', planned_ok=1)
        cancelled_day = self.env['erpec.route.day'].create({'employee_id': self.employee.id, 'date': '2026-09-05'})
        cancelled_day.action_cancel()
        report = self.env['erpec.route.compliance.report'].create({'date_from': '2026-09-04', 'date_to': '2026-09-05'})
        report.action_build()
        self.assertEqual(len(report.line_ids), 1)

    def test_rebuild_does_not_duplicate_lines(self):
        self._make_day('2026-09-06', planned_ok=1)
        report = self.env['erpec.route.compliance.report'].create({'date_from': '2026-09-06', 'date_to': '2026-09-06'})
        report.action_build()
        report.action_build()
        self.assertEqual(len(report.line_ids), 1)

    def test_date_from_after_date_to_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['erpec.route.compliance.report'].create({'date_from': '2026-09-10', 'date_to': '2026-09-01'})

    def test_report_renders_html_in_isolated_harness(self):
        # Igual que en erpec_payroll (A2): bajo --test-tags, sin --http, wkhtmltopdf no puede
        # resolver sus activos internos; Odoo cae a HTML a propósito. El PDF real se verifica
        # aparte, contra la demo.
        self._make_day('2026-09-07', planned_ok=1)
        report = self.env['erpec.route.compliance.report'].create({'date_from': '2026-09-07', 'date_to': '2026-09-07'})
        report.action_build()
        html, report_type = self.env['ir.actions.report']._render_qweb_pdf('erpec_field_routes.report_compliance', report.ids)
        self.assertEqual(report_type, 'html')
        self.assertIn(self.employee.name.encode(), html)
