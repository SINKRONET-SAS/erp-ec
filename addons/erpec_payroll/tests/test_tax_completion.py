"""DI25-03: reliquidación acumulada (D6), regularización de documentos tardíos (D2), comparación de exenciones (D3),
caso 2 con supuestos explícitos, conciliación de devengo y pago (caso 4) y alta tardía de un empleado."""
import json
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

from .test_personal_exemptions import PersonalExemptionIntegrationCase
from .. import engine
from ..parameters_ec2026 import PARAMS as PARAMS_2026


@tagged('post_install', '-at_install')
class TaxCompletionCase(TransactionCase):
    """Política sintética: fracción básica 12.000, tarifa 10 %, IESS 10 %, sin gastos personales."""
    _build_fixture = PersonalExemptionIntegrationCase._build_fixture
    _setup_employee_for_xml = PersonalExemptionIntegrationCase._setup_employee_for_xml
    _accredit = PersonalExemptionIntegrationCase._accredit
    _period = PersonalExemptionIntegrationCase._period
    _post = PersonalExemptionIntegrationCase._post
    _monthly_tax = PersonalExemptionIntegrationCase._monthly_tax
    _annex = PersonalExemptionIntegrationCase._annex

    def setUp(self):
        super().setUp()
        self._build_fixture()
        self.year = self.policy.year
        self.verifier = new_test_user(self.env, login='verificador_completo', groups='base.group_user,erpec_payroll.group_payroll_manager')

    def _tax(self, period):
        return json.loads(period.line_ids.result)['tax']

    # ── D6 · reliquidación mensual acumulada ─────────────────────────────────
    def test_without_history_the_annual_projection_is_unchanged(self):
        self.assertEqual(self._monthly_tax(3000)['tax'], 170.0)  # (32.400 − 12.000) × 10 % / 12

    def test_a_raise_is_recovered_in_the_remaining_months_and_the_year_closes_at_zero(self):
        retentions = []
        for month in range(1, 13):
            retentions.append(self._tax(self._post(3000 if month <= 6 else 4000)))
        self.assertEqual(retentions[:6], [170.0] * 6)
        # Mes 7: (16.200 + 3.600 × 6 − 12.000) × 10 % = 2.580; ya retenido 1.020; 1.560 / 6 = 260.
        self.assertEqual(retentions[6:], [260.0] * 6)
        self.assertAlmostEqual(sum(retentions), 2580.0, places=2)
        annex = self._annex()
        line = annex.line_ids
        self.assertAlmostEqual(line.tax_difference, 0.0, places=2)
        self.assertEqual((line.months_reported, line.months_remaining, line.future_monthly_retention), (12, 0, 0.0))
        self.assertNotIn('Conciliación D6', annex.review_notice)

    def test_over_withholding_never_produces_a_negative_retention(self):
        self._post(6000)  # 5.400 × 12 = 64.800 → 5.280 / 12 = 440
        second = self._period(1000)
        second.action_calculate()
        self.assertEqual(self._tax(second), 0.0)

    def test_the_year_gap_is_shown_as_a_future_monthly_retention_while_months_remain(self):
        self._post(3000)
        self._post(3000)
        self._post(4000)
        annex = self._annex()
        line = annex.line_ids
        self.assertEqual((line.months_reported, line.months_remaining), (3, 9))
        # Proyección: 9.000 + 3.600 × 9 = 41.400 → 2.940; retenido 170 + 170 + 260 = 600; 2.340 / 9 = 260.
        self.assertAlmostEqual(line.projected_tax_after_rebate, 2940.0, places=2)
        self.assertAlmostEqual(line.future_monthly_retention, 260.0, places=2)
        self.assertIn('saldo proyectado por retener de 260.00 al mes', annex.review_notice)

    def test_certified_income_of_the_previous_employer_enters_the_projection(self):
        self.env['erpec.payroll.prior.employer'].create({
            'employee_id': self.employee.id, 'year': self.year, 'origin_ruc': '0990000000001', 'document_number': 'F107-9',
            'issued_date': date(2026, 1, 20), 'received_date': date(2026, 1, 25), 'taxable_income': 12000, 'iess': 1134, 'withheld_tax': 500})
        # (32.400 + 12.000 − 1.134 − 12.000) × 10 % = 3.126,60; menos 500 ya retenidos = 2.626,60 / 12.
        self.assertEqual(self._monthly_tax(3000)['tax'], 218.88)

    def test_late_hire_uses_the_annualised_projection_without_history(self):
        self.employee.write({'name': 'Alta tardía ficticia'})
        period = self.env['erpec.payroll.period'].create({
            'name': 'ALTA-TARDIA', 'policy_id': self.policy.id, 'month': 8,
            'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '%s-07-16' % self.year, 'wage': 3000, 'approved': True})]})
        period.action_calculate()
        result = json.loads(period.line_ids.result)
        self.assertEqual(result['days'], 30)
        self.assertEqual(result['tax'], 170.0)

    # ── D2 · regularización de un documento tardío ───────────────────────────
    def _late_disability(self):
        self._accredit(ec_rdep_disability_type='01', ec_rdep_disability_percentage=50, ec_rdep_exemption_date=date(self.year, 2, 1))

    def _regularization(self, **values):
        base = {'employee_id': self.employee.id, 'year': self.year, 'document_ref': 'DOC-SINTETICO-1', 'delivered_date': date(self.year, 2, 1),
                'validation_note': 'Documento revisado con la persona; sin diagnósticos.', 'effect_date': date(self.year, 3, 1),
                'criterion_reference': 'Criterio formal del responsable tributario, 21-09-2026'}
        return self.env['erpec.payroll.exemption.regularization'].create(dict(base, **values))

    def _verify(self, record):
        record.with_user(self.verifier).action_verify()
        return record

    def test_late_document_blocks_until_a_verified_regularization_and_applies_only_from_its_effect_date(self):
        self._late_disability()
        status = self.employee._rdep_personal_status(self.year, date(self.year, 3, 31))
        self.assertFalse(status['claims'])
        self.assertIn('Documento tardío', ' '.join(status['issues']))
        record = self._regularization()  # en borrador no cuenta
        self.assertIn('Documento tardío', ' '.join(self.employee._rdep_personal_status(self.year, date(self.year, 3, 31))['issues']))
        self._verify(record)
        before = self.employee._rdep_personal_status(self.year, date(self.year, 2, 28))
        self.assertFalse(before['claims'])
        self.assertFalse([issue for issue in before['issues'] if 'tardío' in issue])  # pendiente: aviso, no bloqueo
        self.assertIn('aún no surte efecto', ' '.join(before['notes']))
        after = self.employee._rdep_personal_status(self.year, date(self.year, 3, 31))
        self.assertEqual([claim['kind'] for claim in after['claims']], ['disability'])
        self.assertFalse(after['issues'])

    def test_regularized_exemption_lowers_only_the_future_retentions_and_never_reopens_closed_months(self):
        self._late_disability()
        self._verify(self._regularization())
        first, second = self._post(3000), self._post(3000)
        self.assertEqual((self._tax(first), self._tax(second)), (170.0, 170.0))  # meses previos: sin exención, ya cerrados
        third = self._period(3000)
        third.action_calculate()
        # Exención 50 % = 12.000 × 2 × 70 % = 16.800; (32.400 − 16.800 − 12.000) × 10 % = 360; ya retenido 340; 20 / 10 = 2.
        self.assertEqual(self._tax(third), 2.0)
        self.assertEqual(first.state, 'posted')
        self.assertAlmostEqual(json.loads(first.line_ids.result)['tax'], 170.0)

    def test_regularization_is_never_retroactive(self):
        self._late_disability()
        self._verify(self._regularization(effect_date=date(self.year, 3, 1)))
        self._post(3000)
        self._post(3000)
        second_document = self._regularization(effect_date=date(self.year, 3, 1), criterion_reference='Segundo criterio formal')
        self.employee.ec_rdep_exemption_ref = 'DOC-SINTETICO-1'  # mismo documento
        with self.assertRaisesRegex(ValidationError, 'no es retroactiva'):
            self._regularization(effect_date=date(self.year, 2, 15))
        self.assertEqual(second_document.state, 'draft')

    def test_regularization_controls(self):
        self._late_disability()
        with self.assertRaisesRegex(ValidationError, 'en plazo'):
            self._regularization(delivered_date=date(self.year, 1, 10), effect_date=date(self.year, 3, 1))
        with self.assertRaisesRegex(ValidationError, 'fecha de efecto'):
            self._regularization(effect_date=date(self.year, 1, 20))
        record = self._regularization()
        with self.assertRaisesRegex(ValidationError, 'otra persona'):
            record.action_verify()
        mismatch = self._regularization(document_ref='OTRO-DOC')
        with self.assertRaisesRegex(ValidationError, 'no coinciden'):
            self._verify(mismatch)
        self._verify(record)
        with self.assertRaisesRegex(ValidationError, 'no se edita'):
            record.write({'effect_date': date(self.year, 4, 1)})
        with self.assertRaisesRegex(ValidationError, 'no se elimina'):
            record.unlink()
        record.revoked_reason = 'Fundamento retirado por el responsable.'
        record.action_revoke()
        self.assertEqual(record.state, 'revoked')
        self.assertFalse(self.employee._rdep_personal_status(self.year, date(self.year, 6, 30))['claims'])

    # ── D3 · comparación de exenciones ───────────────────────────────────────
    def test_annex_keeps_the_comparison_of_accredited_exemptions(self):
        self._setup_employee_for_xml(self.employee)  # datos del XML primero: no deben pisar la discapacidad de la prueba
        self.employee.birthday = date(1950, 1, 1)
        self._accredit(ec_rdep_disability_type='01', ec_rdep_disability_percentage=40)
        self._post(3000)
        line = self._annex().line_ids
        self.assertIn('elderly 12000.00', line.exemption_comparison)
        self.assertIn('disability', line.exemption_comparison)
        self.assertIn('→ aplicada:', line.exemption_comparison)
        self.assertEqual(line.personal_exemption_kind, 'disability')

    # ── Caso 2 · saldo de 5,45 con supuestos explícitos ──────────────────────
    def test_case_2_balance_with_explicit_assumptions(self):
        # Supuestos: base imponible 12.677; gastos personales 100 (18 % = 18,00); sin cargas (límite 5.752,60).
        caused, rebate, after = engine.annual_income_tax(12677, 100, PARAMS_2026, 0)
        self.assertEqual((round(float(caused), 2), round(float(rebate), 2), round(float(after), 2)), (23.45, 18.0, 5.45))
        self.assertLessEqual(100, engine.personal_expense_cap(PARAMS_2026['expense_limit'], 0))

    # ── Caso 4 · devengo y pago ─────────────────────────────────────────────
    def test_settlement_notes_show_accrual_and_payment_status(self):
        self._post(3000)
        annex = self._annex()
        self.assertIn('Aviso de conciliación · devengo 1/%s' % self.year, annex.review_notice)
        self.assertIn('Aviso de conciliación · pago 1/%s' % self.year, annex.review_notice)
