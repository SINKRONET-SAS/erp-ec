"""Pruebas del agregador RDEP: solo consolida datos ya contabilizados, sin generar XML."""
import json
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged
from ..demo_parameters import PARAMS


@tagged('post_install', '-at_install')
class RdepAnnexCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'name': 'DEMO nómina sintética', 'vat': False})
        self.expense = self.env['account.account'].create({'code': 'RDEPTESTEXP', 'name': 'Nómina ensayo RDEP', 'account_type': 'expense'})
        self.liability = self.env['account.account'].create({'code': 'RDEPTESTLIAB', 'name': 'Obligaciones ensayo RDEP', 'account_type': 'liability_current'})
        self.journal = self.env['account.journal'].create({'name': 'Nómina ensayo RDEP', 'code': 'RDEPT', 'type': 'general'})
        self.policy = self.env['erpec.payroll.policy'].create({'name': 'SINTETICA-RDEP-1', 'year': 2098, 'journal_id': self.journal.id, 'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local del agregador RDEP', 'source_reference': 'Parámetros ficticios para pruebas'})
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions', 'employer_iess', 'thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({'policy_id': self.policy.id, 'concept': concept, 'debit_id': self.expense.id if concept not in ('net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions') else False, 'credit_id': self.liability.id if concept != 'gross' else False})
        self.policy.action_activate()
        self.employee = self.env['hr.employee'].create({'name': 'Persona ficticia RDEP', 'company_id': self.company.id})
        self.partner = self.env['res.partner'].create({'name': 'Pago ficticio RDEP'})
        self.company.write({'ec_rdep_employer_type': 'PRIVADO_MIXTO', 'ec_rdep_social_security_entity': 'IESS'})

    def _post_period(self, month):
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-%s' % month, 'policy_id': self.policy.id, 'month': month, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        period.action_calculate()
        period.action_close()
        period.action_post()
        return period

    def test_build_consolidates_only_posted_periods(self):
        first = self._post_period(1)
        second = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-DRAFT', 'policy_id': self.policy.id, 'month': 2, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        self.assertEqual(len(annex.line_ids), 1)
        line = annex.line_ids
        self.assertEqual(line.employee_id, self.employee)
        self.assertEqual(line.months, 1)
        first_result = json.loads(first.line_ids.result)
        self.assertEqual(line.gross, first_result['gross'])
        self.assertEqual(line.tax, first_result['tax'])
        second.action_calculate()
        self.assertEqual(second.state, 'calculated')

    def test_build_sums_two_posted_periods_and_is_idempotent(self):
        first = self._post_period(3)
        second = self._post_period(4)
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        line = annex.line_ids
        self.assertEqual(line.months, 2)
        expected_gross = json.loads(first.line_ids.result)['gross'] + json.loads(second.line_ids.result)['gross']
        self.assertEqual(line.gross, expected_gross)
        annex.action_build()
        self.assertEqual(len(annex.line_ids), 1)
        self.assertEqual(annex.line_ids.months, 2)

    def test_build_requires_company_classification(self):
        self.company.write({'ec_rdep_employer_type': False})
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        with self.assertRaises(ValidationError):
            annex.action_build()

    def test_build_requires_posted_periods(self):
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        with self.assertRaises(ValidationError):
            annex.action_build()

    def test_unique_company_year(self):
        self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})

    def test_access_requires_payroll_manager(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({'name': 'Operador sin nómina RDEP', 'login': 'rdep_no_access', 'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)], 'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]})
        self._post_period(5)
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        with self.assertRaises(AccessError):
            annex.with_user(user).action_build()

    def test_employee_field_ranges(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.employee.ec_rdep_disability_percentage = 150
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.employee.ec_rdep_dependents_count = 6
        self.employee.write({'ec_rdep_disability_type': '01', 'ec_rdep_disability_percentage': 40, 'ec_rdep_dependents_count': 2})
        self.assertEqual(self.employee.ec_rdep_disability_percentage, 40)

    def test_views_compile(self):
        self.assertTrue(self.env['erpec.payroll.rdep'].get_view(view_type='form')['arch'])
        # La página RDEP está restringida a group_payroll_manager (igual que la página de
        # Pagos de nómina de erpec_treasury); solo se resuelve en el arch para un usuario
        # con ese grupo, tal como sucede con el resto de contenido restringido del proyecto.
        manager_user = self.env['res.users'].with_context(no_reset_password=True).create({'name': 'Responsable nómina RDEP', 'login': 'rdep_manager_view', 'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)], 'groups_id': [(6, 0, [self.env.ref('erpec_payroll.group_payroll_manager').id])]})
        arch = self.env['hr.employee'].with_user(manager_user).get_view(view_type='form')['arch']
        self.assertIn('ec_rdep_disability_type', arch)
        company_arch = self.env['res.company'].with_user(manager_user).get_view(view_type='form')['arch']
        self.assertIn('ec_rdep_employer_type', company_arch)
