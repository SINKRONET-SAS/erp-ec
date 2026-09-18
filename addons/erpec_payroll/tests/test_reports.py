"""Pruebas de los reportes de nómina (A2): rol de pago, resumen de nómina y ficha de
beneficios acumulados.

Estas pruebas verifican que las plantillas QWeb compilan y renderizan sin error
(HTML, no PDF). wkhtmltopdf resuelve enlaces/activos internos con una petición
HTTP de vuelta al propio Odoo (ver 'Passing the cookie to wkhtmltopdf' en
ir_actions_report.py); este arnés corre con --no-http, así que forzar PDF aquí
cuelga el proceso indefinidamente esperando esa petición. La generación de PDF
real se verifica aparte, contra la demo (que sí tiene HTTP activo)."""
import json

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..demo_parameters import PARAMS


@tagged('post_install', '-at_install')
class ReportCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'name': 'DEMO nómina reportes', 'vat': False})
        self.expense = self.env['account.account'].create({'code': 'PAYRPTEXP', 'name': 'Nómina ensayo', 'account_type': 'expense'})
        self.liability = self.env['account.account'].create({'code': 'PAYRPTLIAB', 'name': 'Obligaciones ensayo', 'account_type': 'liability_current'})
        self.journal = self.env['account.journal'].create({'name': 'Nómina ensayo reportes', 'code': 'PAYR', 'type': 'general'})
        self.policy = self.env['erpec.payroll.policy'].create({
            'name': 'SINTETICA-REPORTES', 'year': 2098, 'journal_id': self.journal.id,
            'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local de reportes',
            'source_reference': 'Parámetros ficticios para pruebas'})
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions',
                        'employer_iess', 'thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({
                'policy_id': self.policy.id, 'concept': concept,
                'debit_id': self.expense.id if concept not in ('net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions') else False,
                'credit_id': self.liability.id if concept != 'gross' else False})
        self.policy.action_activate()
        self.employee = self.env['hr.employee'].create({'name': 'Persona de reportes', 'company_id': self.company.id})
        self.partner = self.env['res.partner'].create({'name': 'Pago de reportes'})
        self.period = self.env['erpec.payroll.period'].create({
            'name': 'ENSAYO-REPORTES', 'policy_id': self.policy.id, 'month': 9,
            'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id,
                                  'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        self.period.action_calculate()
        self.period.action_close()
        self.period.action_post()

    def test_payslip_report_renders_html(self):
        html, report_type = self.env['ir.actions.report']._render_qweb_pdf(
            'erpec_payroll.report_payslip', self.period.line_ids.ids)
        self.assertEqual(report_type, 'html')
        self.assertIn(self.employee.name.encode(), html)
        self.assertIn(b'Rol de pago', html)

    def test_period_summary_report_renders_html(self):
        html, report_type = self.env['ir.actions.report']._render_qweb_pdf(
            'erpec_payroll.report_period_summary', self.period.ids)
        self.assertEqual(report_type, 'html')
        self.assertIn(self.employee.name.encode(), html)

    def test_benefit_summary_requires_posted_periods(self):
        summary = self.env['erpec.payroll.benefit.summary'].create({'company_id': self.company.id, 'year': 2001})
        with self.assertRaises(ValidationError):
            summary.action_build()

    def test_benefit_summary_aggregates_posted_periods_and_renders(self):
        summary = self.env['erpec.payroll.benefit.summary'].create({'company_id': self.company.id, 'year': 2098})
        summary.action_build()
        self.assertEqual(len(summary.line_ids), 1)
        line = summary.line_ids
        self.assertEqual(line.employee_id, self.employee)
        self.assertEqual(line.months, 1)
        result = json.loads(self.period.line_ids.result)
        self.assertEqual(line.thirteenth, result['thirteenth'])
        self.assertEqual(line.fourteenth, result['fourteenth'])
        self.assertEqual(line.cost, result['cost'])
        html, report_type = self.env['ir.actions.report']._render_qweb_pdf(
            'erpec_payroll.report_benefit_summary', summary.ids)
        self.assertEqual(report_type, 'html')
        self.assertIn(self.employee.name.encode(), html)

    def test_benefit_summary_rebuild_does_not_duplicate(self):
        summary = self.env['erpec.payroll.benefit.summary'].create({'company_id': self.company.id, 'year': 2098})
        summary.action_build()
        summary.action_build()
        self.assertEqual(len(summary.line_ids), 1)
