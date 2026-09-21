"""Regresiones del pronunciamiento DI25-03 con resultados y bloqueos independientes."""
import json
from datetime import date
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from .test_personal_exemptions import PersonalExemptionIntegrationCase
from ..engine import resolve_exemption_claims
from ..tax_review import review_calculation
from ..tax_review_cases import BASE_INPUTS
from ..parameters_ec2026 import PARAMS


@tagged('post_install', '-at_install')
class TaxControlsCase(TransactionCase):
    _build_fixture = PersonalExemptionIntegrationCase._build_fixture
    _setup_employee_for_xml = PersonalExemptionIntegrationCase._setup_employee_for_xml
    _accredit = PersonalExemptionIntegrationCase._accredit
    _period = PersonalExemptionIntegrationCase._period

    def setUp(self):
        super().setUp()
        self._build_fixture()

    def test_d1_birthday_boundaries_and_late_age_evidence(self):
        for birthday in (date(1961, 1, 1), date(1961, 12, 31), date(1960, 2, 29)):
            claims, issues, _ = resolve_exemption_claims(
                2026, birthday, '04', 0, 'N', '', 2026, 'EDAD-1', date(2026, 8, 1))
            self.assertEqual(claims, [{'kind': 'elderly'}])
            self.assertFalse(issues)
        claims, issues, _ = resolve_exemption_claims(
            2026, date(1962, 1, 1), '04', 0, 'N', '', 2026, 'EDAD-1', date(2026, 1, 1))
        self.assertFalse(claims)
        self.assertTrue(issues)

    def test_d2_late_disability_cannot_close(self):
        claims, issues, _ = resolve_exemption_claims(
            2026, date(1961, 12, 31), '01', 80, 'N', '', 2026, 'DOC-1', date(2026, 2, 1))
        self.assertEqual(claims, [{'kind': 'elderly'}])
        self.assertTrue(issues)

        self._accredit(ec_rdep_disability_type='01', ec_rdep_disability_percentage=50,
                       ec_rdep_exemption_date=date(self.policy.year, 2, 1))
        period = self._period(3000)
        period.action_calculate()
        self.assertEqual(json.loads(period.line_ids.result)['personal_exemption'], 0)
        with self.assertRaisesRegex(ValidationError, 'regularización'):
            period.action_close()

    def test_d4_duplicate_substitution_is_detected_without_exposing_other_employee(self):
        self._accredit(ec_rdep_disability_type='02', ec_rdep_disability_percentage=80,
                       ec_rdep_disability_id_type='C', ec_rdep_disability_id='1712345678')
        self.env['hr.employee'].create({
            'name': 'Persona confidencial', 'company_id': self.company.id,
            'ec_rdep_disability_type': '02', 'ec_rdep_disability_id': '1712345678',
            'ec_rdep_exemption_year': self.policy.year})
        status = self.employee._rdep_personal_status(self.policy.year)
        self.assertFalse(status['claims'])
        self.assertIn('Conflicto', ' '.join(status['issues']))
        self.assertNotIn('Persona confidencial', ' '.join(status['issues']))

    def test_d7_reference_alone_cannot_reduce_tax_or_close(self):
        self.employee.write({'ec_rdep_special_expense': 'holder',
                             'ec_rdep_special_expense_year': self.policy.year,
                             'ec_rdep_special_expense_ref': 'TEXTO-NO-VERIFICADO'})
        period = self._period(3000, personal_expenses=6000)
        period.action_calculate()
        self.assertEqual(json.loads(period.line_ids.result)['tax'], 95)
        self.assertIn('D7', period.tax_validation_notice)
        with self.assertRaisesRegex(ValidationError, 'D7'):
            period.action_close()

    def test_d8_previous_employer_requires_certificate_not_monthly_repetition(self):
        period = self._period(3000, other_employer_taxable_income=10000,
                              other_employer_iess=945, other_employer_withheld_tax=100)
        period.action_calculate()
        with self.assertRaisesRegex(ValidationError, 'D8'):
            period.action_close()
        self.assertEqual(period.state, 'calculated')
        self.assertFalse(period.move_id)

    def test_d8_inconsistent_iess_is_reported(self):
        period = self._period(3000, other_employer_taxable_income=100,
                              other_employer_iess=101)
        period.action_calculate()
        self.assertIn('supera sus ingresos', period.tax_validation_notice)

    def test_changed_tax_data_must_recalculate_before_close(self):
        period = self._period(3000)
        period.action_calculate()
        original_hash = period.tax_validation_hash
        self.employee.ec_rdep_dependents_count = 1
        with self.assertRaisesRegex(ValidationError, 'cambiaron'):
            period.action_close()
        period.action_calculate()
        self.assertNotEqual(period.tax_validation_hash, original_hash)
        period.action_close()
        self.assertEqual(period.state, 'closed')

    def test_changed_tax_data_after_close_cannot_post(self):
        period = self._period(3000)
        period.action_calculate()
        period.action_close()
        self.employee.ec_rdep_dependents_count = 1
        with self.assertRaisesRegex(ValidationError, 'cambiaron'):
            period.action_post()
        self.assertFalse(period.move_id)

    def test_same_inputs_keep_validation_hash_and_cannot_forge_it(self):
        period = self._period(3000)
        period.action_calculate()
        expected = period.tax_validation_hash
        period.action_calculate()
        self.assertEqual(period.tax_validation_hash, expected)
        with self.assertRaisesRegex(ValidationError, 'huella'):
            period.write({'tax_validation_hash': 'false'})

    def test_applied_rebate_never_exceeds_tax_and_does_not_invent_refund(self):
        values = dict(BASE_INPUTS, current_income=60000, current_iess=5670,
                      other_income=0, other_iess=0, other_withheld=0,
                      current_withheld=0, personal_expenses=100000,
                      special_condition='holder', galapagos='NO')
        result = review_calculation(values, PARAMS)
        self.assertEqual(float(result['tax_caused']), 6903.75)
        self.assertEqual(float(result['rebate']), 14792.40)
        self.assertEqual(float(result['rebate_applied']), 6903.75)
        self.assertEqual(float(result['annual_tax']), 0)
        self.assertEqual(float(result['excess_withheld']), 0)

    def test_visible_notice_refreshes_when_condition_changes(self):
        period = self._period(3000)
        self.assertNotIn('D7', period.tax_validation_notice)
        self.assertNotIn('D7', self.employee.ec_rdep_validation_notice)
        period.line_ids.other_employer_taxable_income = 100
        self.assertIn('D8', period.tax_validation_notice)
        self.employee.write({'ec_rdep_special_expense': 'holder'})
        self.assertIn('D7', self.employee.ec_rdep_validation_notice)
        self.assertIn('D7', period.tax_validation_notice)
