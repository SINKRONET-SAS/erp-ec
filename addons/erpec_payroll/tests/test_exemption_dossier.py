"""DI25-03 D4 y D7: el expediente verificado sustituye a la referencia aislada."""
from datetime import date

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

from .test_personal_exemptions import PersonalExemptionIntegrationCase


@tagged('post_install', '-at_install')
class ExemptionDossierCase(TransactionCase):
    _build_fixture = PersonalExemptionIntegrationCase._build_fixture
    _setup_employee_for_xml = PersonalExemptionIntegrationCase._setup_employee_for_xml
    _accredit = PersonalExemptionIntegrationCase._accredit
    _period = PersonalExemptionIntegrationCase._period
    _monthly_tax = PersonalExemptionIntegrationCase._monthly_tax

    def setUp(self):
        super().setUp()
        self._build_fixture()
        self.model = self.env['erpec.payroll.exemption.dossier']
        self.year = self.policy.year
        self.verifier = new_test_user(self.env, login='verificador_expedientes', groups='base.group_user,erpec_payroll.group_payroll_manager')

    def _dossier(self, **values):
        base = {'employee_id': self.employee.id, 'year': self.year, 'kind': 'substitute', 'document_ref': 'DOC-SINTETICO-D4',
                'authority': 'Autoridad sintética', 'issue_date': date(2025, 12, 1), 'valid_from': date(self.year, 1, 1),
                'valid_to': date(self.year, 12, 31), 'person_id_type': 'C', 'person_id': '1712345678', 'disability_percentage': 80}
        return self.model.create(dict(base, **values))

    def _special_holder(self, **values):
        return self._dossier(kind='special_holder', condition='catastrophic', person_id=False, person_id_type=False, disability_percentage=0, **values)

    def _as_substitute(self):
        self.employee.write({
            'ec_rdep_disability_type': '02', 'ec_rdep_disability_percentage': 80, 'ec_rdep_disability_id_type': 'C',
            'ec_rdep_disability_id': '1712345678', 'ec_rdep_exemption_year': self.year, 'ec_rdep_exemption_ref': 'DOC-SINTETICO-1',
            'ec_rdep_exemption_date': date(self.year, 1, 10), 'ec_rdep_exemption_months': 12})

    def _verify(self, dossier):
        dossier.with_user(self.verifier).action_verify()
        return dossier

    def _other_employee(self, name):
        return self.env['hr.employee'].create({'name': name, 'company_id': self.company.id})

    # ── D4 sustituto ────────────────────────────────────────────────────────
    def test_substitute_without_verified_dossier_stays_blocked(self):
        self._as_substitute()
        status = self.employee._rdep_personal_status(self.year)
        self.assertFalse(status['claims'])
        self.assertIn('D4', ' '.join(status['issues']))
        self._dossier()  # en borrador no cuenta
        self.assertFalse(self.employee._rdep_personal_status(self.year)['claims'])

    def test_verified_dossier_applies_the_substitute_claim_and_lowers_the_retention(self):
        self._as_substitute()
        blocked = self._monthly_tax(3000)['tax']
        self._verify(self._dossier())
        status = self.employee._rdep_personal_status(self.year)
        self.assertEqual(status['claims'], [{'kind': 'substitute', 'percentage': 80, 'months': 12}])
        self.assertFalse([issue for issue in status['issues'] if 'D4' in issue])
        self.assertLess(self._monthly_tax(3000)['tax'], blocked)

    def test_partial_period_is_proportional_to_the_accredited_time(self):
        self._as_substitute()
        self._verify(self._dossier(valid_to=date(self.year, 6, 30)))
        self.assertEqual(self.employee._rdep_personal_status(self.year)['claims'][0]['months'], 6)

    def test_replacement_substitutes_share_the_year_without_overlapping(self):
        second = self._other_employee('Segundo sustituto ficticio')
        first_dossier = self._verify(self._dossier(valid_to=date(self.year, 6, 30)))
        second_dossier = self._verify(self._dossier(employee_id=second.id, valid_from=date(self.year, 7, 1)))
        self.assertEqual((first_dossier.state, second_dossier.state), ('verified', 'verified'))
        third = self._other_employee('Tercer sustituto ficticio')
        overlapping = self._dossier(employee_id=third.id, valid_from=date(self.year, 6, 1), valid_to=date(self.year, 8, 31))
        with self.assertRaisesRegex(ValidationError, 'ya tiene un sustituto'):
            self._verify(overlapping)
        self.assertEqual(overlapping.state, 'draft')

    def test_the_substitute_uses_the_benefit_only_once(self):
        self._verify(self._dossier())
        other_person = self._dossier(person_id='1798765432', valid_to=date(self.year, 6, 30))
        with self.assertRaisesRegex(ValidationError, 'solo se usa una vez'):
            self._verify(other_person)

    def test_person_in_the_form_must_match_the_verified_dossier(self):
        self._as_substitute()
        self.employee.ec_rdep_disability_id = '1700000001'
        self._verify(self._dossier())
        self.assertIn('no coincide', ' '.join(self.employee._rdep_personal_status(self.year)['issues']))

    # ── D7 100 canastas ─────────────────────────────────────────────────────
    def _special(self, mode):
        self.employee.write({'ec_rdep_special_expense': mode, 'ec_rdep_special_expense_year': self.year,
                             'ec_rdep_special_expense_ref': 'REF-SINTETICA', 'ec_rdep_dependents_count': 1 if mode == 'dependent' else 0})

    def test_special_limit_needs_a_verified_full_year_dossier(self):
        self._special('holder')
        blocked = self._monthly_tax(3000, personal_expenses=6000)['tax']
        self.assertIn('D7', ' '.join(self.employee._rdep_personal_status(self.year)['issues']))
        self._verify(self._special_holder(valid_to=date(self.year, 6, 30)))
        self.assertIn('D7', ' '.join(self.employee._rdep_personal_status(self.year)['issues']))  # vigencia parcial: no aplica
        self._verify(self._special_holder(valid_from=date(self.year, 7, 1)))
        status = self.employee._rdep_personal_status(self.year)
        self.assertTrue(status['special_expense'])
        self.assertFalse([issue for issue in status['issues'] if 'D7' in issue])
        self.assertLess(self._monthly_tax(3000, personal_expenses=6000)['tax'], blocked)

    def test_a_dependent_cannot_be_used_twice(self):
        self._special('dependent')
        values = {'kind': 'special_dependent', 'condition': 'rare', 'person_id': '1711111111', 'relationship': 'Hijo', 'disability_percentage': 0}
        self._verify(self._dossier(**values))
        other = self._other_employee('Otra persona ficticia')
        with self.assertRaisesRegex(ValidationError, 'doble uso'):
            self._verify(self._dossier(employee_id=other.id, **values))

    # ── Controles del expediente ────────────────────────────────────────────
    def test_the_registrant_cannot_verify_their_own_dossier(self):
        dossier = self._dossier()
        with self.assertRaisesRegex(ValidationError, 'otra persona'):
            dossier.action_verify()
        self.assertEqual(dossier.state, 'draft')

    def test_verified_dossier_is_immutable_and_can_be_revoked_with_a_reason(self):
        self._as_substitute()
        dossier = self._verify(self._dossier())
        with self.assertRaisesRegex(ValidationError, 'no se edita'):
            dossier.write({'valid_to': date(self.year, 3, 31)})
        with self.assertRaisesRegex(ValidationError, 'no se elimina'):
            dossier.unlink()
        with self.assertRaisesRegex(ValidationError, 'no se edita'):
            dossier.write({'state': 'draft'})
        forged = self._dossier(document_ref='DOC-FALSIFICADO')
        for values in ({'state': 'verified'}, {'verified_by': self.verifier.id}):
            with self.subTest(values=values), self.assertRaisesRegex(ValidationError, 'solo con sus acciones'):
                forged.write(values)
        with self.assertRaisesRegex(ValidationError, 'solo con sus acciones'):
            self._dossier(state='verified')
        dossier.revoked_reason = 'Documento reemplazado por la autoridad.'
        dossier.action_revoke()
        self.assertEqual((dossier.state, dossier.revoked_reason), ('revoked', 'Documento reemplazado por la autoridad.'))
        self.assertFalse(self.employee._rdep_personal_status(self.year)['claims'])
        with self.assertRaisesRegex(ValidationError, 'no se edita'):
            dossier.write({'authority': 'Otra'})

    def test_structural_validations(self):
        cases = [
            {'valid_to': date(self.year + 1, 1, 31)}, {'valid_from': date(self.year, 12, 31), 'valid_to': date(self.year, 1, 1)},
            {'person_id': False}, {'disability_percentage': 20}, {'issue_date': date(2999, 1, 1)}, {'person_id_type': False},
            {'kind': 'special_dependent', 'condition': 'rare', 'relationship': False},
            {'kind': 'special_holder', 'condition': False, 'person_id': False, 'person_id_type': False, 'disability_percentage': 0},
            {'kind': 'special_holder', 'condition': 'disability', 'person_id': False, 'person_id_type': False, 'disability_percentage': 10},
            {'condition': 'rare'}]  # el sustituto no lleva condición de 100 canastas
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self._dossier(**values)

    def test_only_payroll_managers_register_dossiers(self):
        user = new_test_user(self.env, login='sin_nomina_d4', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.model.with_user(user).create({'employee_id': self.employee.id, 'year': self.year, 'kind': 'special_holder'})

    def test_each_condition_is_its_own_documentary_route(self):
        self._special('holder')
        disability = self._dossier(kind='special_holder', condition='disability', disability_percentage=60, person_id=False, person_id_type=False)
        self.assertEqual(disability.condition, 'disability')
        for condition in ('catastrophic', 'rare', 'orphan'):
            with self.subTest(condition=condition):
                record = self._dossier(kind='special_holder', condition=condition, disability_percentage=0, person_id=False, person_id_type=False,
                                       document_ref='DOC-' + condition)
                self.assertEqual(record.condition, condition)
        with self.assertRaisesRegex(ValidationError, 'condición'):
            self._dossier(kind='special_holder', condition=False, disability_percentage=0, person_id=False, person_id_type=False)
