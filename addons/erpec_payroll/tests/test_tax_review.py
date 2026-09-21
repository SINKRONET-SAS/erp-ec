"""Contraste independiente, recálculo y aislamiento del ensayo tributario."""
import json
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, TransactionCase, tagged
from ..parameters_ec2026 import PARAMS
from ..tax_review import review_calculation, BASE_INPUTS


@tagged('post_install', '-at_install')
class TaxReviewCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({'name': 'DEMO revisión tributaria', 'vat': False})
        cls.policy = cls.env['erpec.payroll.policy'].create({
            'name': 'Revisión sintética 2026', 'year': 2026, 'parameters': json.dumps(PARAMS),
            'authorization': 'Ensayo sin efectos contables', 'source_reference': 'Tabla SRI 2026'})
        cls.review = cls.env['erpec.payroll.tax.review'].create({'policy_id': cls.policy.id})

    def test_independent_annual_cases_and_once_only(self):
        self.review.scenario = 'baseline'
        self.review.action_load_reference()
        self.assertEqual(self.review.annual_base, 16299)
        self.assertEqual(self.review.annual_tax, 62)
        self.assertEqual(self.review.pending_tax, 12)
        self.review.write({'other_income': 6000, 'other_iess': 567, 'other_withheld': 150})
        self.assertEqual(self.review.combined_income, 24000)
        self.assertEqual(self.review.annual_base, 21732)
        self.assertEqual(self.review.tax_caused, 816.28)
        self.assertEqual(self.review.rebate, 180)
        self.assertEqual(self.review.annual_tax, 636.28)
        self.assertEqual(self.review.without_other_tax, 62)
        self.assertEqual(self.review.tax_increase, 574.28)
        self.assertEqual(self.review.pending_tax, 436.28)
        self.assertEqual(self.review.monthly_estimate, 145.42)
        self.assertEqual(self.review.last_estimate, 145.44)
        self.review.scenario = 'higher'
        self.review.action_load_reference()
        self.assertEqual(self.review.annual_base, 25354)
        self.assertEqual(self.review.annual_tax, 1070.92)
        self.assertEqual(self.review.pending_tax, 870.92)
        self.assertIn('Coincide', self.review.reference_status)

    def test_form_recomputes_after_edit_and_save(self):
        with Form(self.review) as form:
            form.other_income = 10000
            form.other_iess = 945
            self.assertEqual(form.annual_base, 25354)
            self.assertEqual(form.annual_tax, 1070.92)
        self.review.invalidate_recordset()
        self.assertEqual(self.review.annual_tax, 1070.92)
        self.assertIn('modificadas', self.review.reference_status)

    def test_withholding_is_credit_and_never_negative_retention(self):
        before = (self.review.annual_base, self.review.annual_tax)
        self.review.other_withheld = 1000
        self.assertEqual((self.review.annual_base, self.review.annual_tax), before)
        self.assertEqual(self.review.pending_tax, 0)
        self.assertEqual(self.review.excess_withheld, 413.72)
        self.assertEqual(self.review.monthly_estimate, 0)
        self.assertEqual(self.review.last_estimate, 0)

    def test_invalid_values_and_onchange_error(self):
        for values in ({'other_income': -1}, {'other_iess': 6001}, {'remaining_months': 0},
                       {'remaining_months': 13}, {'personal_expenses': -1}, {'dependents': -1}):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self.review.write(values)
        transient = self.env['erpec.payroll.tax.review'].new({'policy_id': self.policy.id, 'other_income': -1})
        self.assertTrue(transient.validation_error)
        self.assertEqual(transient.annual_tax, 0)
        with self.assertRaises(ValueError):
            review_calculation(dict(BASE_INPUTS, other_income=float('inf')), PARAMS)

    def test_expense_cap_and_cent_distribution(self):
        self.review.write({'personal_expenses': 100000, 'dependents': 0})
        self.assertEqual(self.review.expense_cap, 5752.60)
        self.assertEqual(self.review.rebate, 1035.47)
        self.assertEqual(self.review.annual_tax, 0)
        self.review.personal_expenses = 0
        for months in (1, 3, 12):
            self.review.remaining_months = months
            self.assertAlmostEqual(self.review.monthly_estimate*(months-1)+self.review.last_estimate,
                                   self.review.pending_tax, places=2)
        self.review.dependents = 1
        self.assertEqual(self.review.expense_cap, 7396.20)

    def test_reset_preserves_notes_and_does_not_mutate_payroll(self):
        moves = self.env['account.move'].search_count([])
        periods = self.env['erpec.payroll.period'].search_count([])
        annexes = self.env['erpec.payroll.rdep'].search_count([])
        self.review.write({'reviewer_notes': 'Observación sintética del revisor', 'scenario': 'previous', 'other_income': 9000})
        self.review.action_load_reference()
        self.review.action_load_reference()
        self.assertEqual(self.review.other_income, 6000)
        self.assertEqual(self.review.reviewer_notes, 'Observación sintética del revisor')
        self.assertIn('Coincide', self.review.reference_status)
        self.assertEqual(self.env['account.move'].search_count([]), moves)
        self.assertEqual(self.env['erpec.payroll.period'].search_count([]), periods)
        self.assertEqual(self.env['erpec.payroll.rdep'].search_count([]), annexes)

    def test_company_policy_and_access_guards(self):
        company = self.env['res.company'].create({'name': 'DEMO otra empresa'})
        policy = self.env['erpec.payroll.policy'].create({
            'name': 'Otra política', 'company_id': company.id, 'year': 2026,
            'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo', 'source_reference': 'SRI'})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.review.policy_id = policy
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Revisor limitado DEMO', 'login': 'di25-renta-review-test',
            'company_id': company.id, 'company_ids': [(6, 0, company.ids)],
            'groups_id': [(6, 0, [self.env.ref('erpec_payroll.group_payroll_manager').id])]})
        with self.assertRaises(AccessError):
            self.review.with_user(user).read(['other_income'])
        user.groups_id = [(6, 0, [self.env.ref('base.group_user').id])]
        with self.assertRaises(AccessError):
            self.env['erpec.payroll.tax.review'].with_user(user).create({'policy_id': policy.id})
        self.env.company.name = 'Empresa fuera del ensayo'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.review.other_income = 100

    def test_all_visible_examples_against_independent_references(self):
        from ..tax_review_cases import CASES
        self.assertEqual(len(CASES), 19)
        for key, case in CASES.items():
            with self.subTest(case=key):
                self.review.scenario = key
                self.review.action_load_reference()
                self.assertFalse(self.review.validation_error)
                self.assertEqual((self.review.annual_base, self.review.tax_caused,
                                  self.review.annual_tax, self.review.pending_tax), tuple(case[2:6]))
                self.assertIn('Coincide', self.review.reference_status)

    def test_exempt_benefits_do_not_increase_tax_and_region_only_changes_rebate(self):
        self.review.scenario = 'exempt_benefits'
        self.review.action_load_reference()
        self.assertEqual(self.review.exempt_income, 10482)
        self.assertEqual(self.review.total_informed, 70482)
        self.assertEqual(self.review.annual_base, 54330)
        self.assertEqual(self.review.annual_tax, 5868.28)
        self.review.exempt_thirteenth = 7000
        self.assertEqual(self.review.total_informed, 72482)
        self.assertEqual(self.review.annual_tax, 5868.28)
        self.review.galapagos = 'SI'
        self.assertEqual(self.review.annual_base, 54330)
        self.assertEqual(self.review.tax_caused, 6903.75)
        self.assertEqual(self.review.rebate, 1866.95)
        self.assertEqual(self.review.annual_tax, 5036.80)
        self.review.dependents = 4
        self.assertEqual(self.review.annual_tax, 2369.73)
        self.review.dependents = 5
        self.assertEqual(self.review.annual_tax, 1569.61)
