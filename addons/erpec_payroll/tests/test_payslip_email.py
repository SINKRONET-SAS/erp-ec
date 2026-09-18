"""Pruebas del envío automático del rol de pago (A3): se dispara al aprobar el cierre del
período, encola el correo (no lo envía de verdad sin un servidor SMTP real) con el reporte
adjunto, y no bloquea el cierre si un empleado no tiene correo de trabajo configurado.

El adjunto del reporte se verifica como HTML aquí, no PDF: igual que en A2, Odoo cae a
render_html a propósito bajo --test-tags (ver ir_actions_report.py:1011) porque este arnés
corre con --no-http y wkhtmltopdf no puede resolver sus activos internos. La generación de
PDF real del adjunto se verifica aparte, contra la demo (HTTP activo)."""
import json

from odoo.tests import TransactionCase, tagged

from ..demo_parameters import PARAMS


@tagged('post_install', '-at_install')
class PayslipEmailCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'name': 'DEMO nómina correo', 'vat': False})
        self.expense = self.env['account.account'].create({'code': 'PAYMAILEXP', 'name': 'Nómina correo ensayo', 'account_type': 'expense'})
        self.liability = self.env['account.account'].create({'code': 'PAYMAILLIAB', 'name': 'Obligaciones correo ensayo', 'account_type': 'liability_current'})
        self.journal = self.env['account.journal'].create({'name': 'Nómina correo ensayo', 'code': 'PYMA', 'type': 'general'})
        self.policy = self.env['erpec.payroll.policy'].create({
            'name': 'SINTETICA-CORREO', 'year': 2097, 'journal_id': self.journal.id,
            'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local de correo',
            'source_reference': 'Parámetros ficticios para pruebas'})
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions',
                        'employer_iess', 'thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({
                'policy_id': self.policy.id, 'concept': concept,
                'debit_id': self.expense.id if concept not in ('net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions') else False,
                'credit_id': self.liability.id if concept != 'gross' else False})
        self.policy.action_activate()
        self.partner = self.env['res.partner'].create({'name': 'Pago de correo'})

    def _make_period(self, employee_vals):
        employee = self.env['hr.employee'].create({'company_id': self.company.id, **employee_vals})
        period = self.env['erpec.payroll.period'].create({
            'name': 'ENSAYO-CORREO-' + employee.name, 'policy_id': self.policy.id, 'month': 8,
            'line_ids': [(0, 0, {'employee_id': employee.id, 'partner_id': self.partner.id,
                                  'start_date': '2025-01-01', 'wage': 1000, 'approved': True})]})
        period.action_calculate()
        return period, employee

    def test_close_sends_queued_email_with_pdf_attachment_when_employee_has_work_email(self):
        period, employee = self._make_period({'name': 'Con correo', 'work_email': 'con.correo@ejemplo-ensayo.test'})
        period.action_close()
        line = period.line_ids
        self.assertTrue(line.payslip_mail_id)
        self.assertTrue(line.payslip_sent_date)
        self.assertFalse(line.payslip_send_error)
        mail = line.payslip_mail_id
        self.assertEqual(mail.state, 'outgoing')
        self.assertEqual(mail.email_to, employee.work_email)
        self.assertTrue(mail.attachment_ids)
        self.assertTrue(any(att.name.lower().endswith(('.pdf', '.html')) and att.datas for att in mail.attachment_ids))

    def test_close_does_not_send_real_email_without_smtp_credentials(self):
        period, employee = self._make_period({'name': 'Sin SMTP', 'work_email': 'sin.smtp@ejemplo-ensayo.test'})
        period.action_close()
        mail = period.line_ids.payslip_mail_id
        self.assertNotEqual(mail.state, 'sent')

    def test_close_skips_and_logs_error_when_employee_has_no_work_email(self):
        period, employee = self._make_period({'name': 'Sin correo'})
        period.action_close()
        line = period.line_ids
        self.assertFalse(line.payslip_mail_id)
        self.assertIn('correo electrónico de trabajo', line.payslip_send_error)

    def test_close_does_not_block_other_employees_when_one_lacks_email(self):
        employee_ok = self.env['hr.employee'].create({'company_id': self.company.id, 'name': 'Con correo dos', 'work_email': 'dos@ejemplo-ensayo.test'})
        employee_bad = self.env['hr.employee'].create({'company_id': self.company.id, 'name': 'Sin correo dos'})
        period = self.env['erpec.payroll.period'].create({
            'name': 'ENSAYO-CORREO-MIXTO', 'policy_id': self.policy.id, 'month': 9,
            'line_ids': [
                (0, 0, {'employee_id': employee_ok.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1000, 'approved': True}),
                (0, 0, {'employee_id': employee_bad.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1000, 'approved': True}),
            ]})
        period.action_calculate()
        period.action_close()
        line_ok = period.line_ids.filtered(lambda l: l.employee_id == employee_ok)
        line_bad = period.line_ids.filtered(lambda l: l.employee_id == employee_bad)
        self.assertTrue(line_ok.payslip_mail_id)
        self.assertFalse(line_bad.payslip_mail_id)
        self.assertTrue(line_bad.payslip_send_error)

    def test_action_resend_payslip_works_standalone(self):
        period, employee = self._make_period({'name': 'Reenvío', 'work_email': 'reenvio@ejemplo-ensayo.test'})
        period.action_close()
        line = period.line_ids
        first_mail = line.payslip_mail_id
        self.assertTrue(first_mail)
        line.action_resend_payslip()
        self.assertTrue(line.payslip_mail_id)
