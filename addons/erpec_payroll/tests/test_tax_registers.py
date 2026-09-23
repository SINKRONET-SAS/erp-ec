"""DI25-03 segunda ronda: sellado de parámetros, comprobantes del empleador anterior (D8) y su conciliación."""
import base64
import hashlib
import json
from copy import deepcopy
from datetime import date

from lxml import etree
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

from .test_personal_exemptions import PersonalExemptionIntegrationCase
from .. import engine, parameters_seal
from ..parameters_ec2026 import PARAMS


@tagged('post_install', '-at_install')
class ParametersSealCase(TransactionCase):
    def test_seal_matches_the_hash_and_the_shipped_2026_parameters(self):
        self.assertEqual(parameters_seal.verify_seal_integrity(2026), [])
        self.assertEqual(parameters_seal.verify_policy_parameters(2026, PARAMS), [])
        self.assertEqual(parameters_seal.verify_engine_constants(2026, engine), [])

    def test_independent_official_figures(self):
        sealed = parameters_seal.SEALED_TAX_PARAMETERS[2026]
        self.assertEqual(sealed['tax_brackets'][0]['to'], 12208)
        self.assertEqual(sealed['tax_brackets'][1]['to'], 15549)
        self.assertEqual(sealed['tax_brackets'][1]['rate'], 0.05)
        self.assertEqual(sealed['basket'], 821.8)
        self.assertEqual(round(sealed['basket'] * 7, 2), 5752.6)
        self.assertEqual(sorted(sealed['baskets_by_dependents'].values()), [7, 9, 11, 14, 17, 20])
        self.assertEqual(sealed['special_expense_baskets'], 100)
        self.assertEqual(sealed['ipceg_factor'], 1.803)
        # Caso 2 del pronunciamiento: (12.677 − 12.208) × 5 % = 23,45.
        self.assertEqual(round(float(engine.annual_income_tax(12677, 0, PARAMS)[0]), 2), 23.45)

    def test_bracket_table_is_internally_coherent(self):
        self.assertEqual(parameters_seal.verify_bracket_coherence(PARAMS['tax_brackets']), [])
        broken = deepcopy(PARAMS['tax_brackets'])
        broken[3]['base'] += 50
        self.assertTrue(parameters_seal.verify_bracket_coherence(broken))

    def test_silent_change_of_sealed_values_is_detected(self):
        sealed = parameters_seal.SEALED_TAX_PARAMETERS[2026]
        original = sealed['basket']
        try:
            sealed['basket'] = 800.0
            self.assertTrue(parameters_seal.verify_seal_integrity(2026))
            self.assertTrue(parameters_seal.verify_policy_parameters(2026, PARAMS))
        finally:
            sealed['basket'] = original
        self.assertEqual(parameters_seal.verify_seal_integrity(2026), [])

    def test_policy_deviations_are_reported(self):
        tampered = deepcopy(PARAMS)
        tampered['tax_brackets'][1]['rate'] = 0.06
        self.assertIn('tabla progresiva', ' '.join(parameters_seal.verify_policy_parameters(2026, tampered)))
        tampered = dict(PARAMS, rebate_rate=0.2)
        self.assertIn('rebate_rate', ' '.join(parameters_seal.verify_policy_parameters(2026, tampered)))
        tampered = dict(PARAMS, expense_limit=5000)
        self.assertIn('expense_limit', ' '.join(parameters_seal.verify_policy_parameters(2026, tampered)))

    def test_engine_constants_deviation_is_reported(self):
        original = engine.GALAPAGOS_IPCEG_FACTOR
        try:
            engine.GALAPAGOS_IPCEG_FACTOR = 1.5
            self.assertTrue(parameters_seal.verify_engine_constants(2026, engine))
        finally:
            engine.GALAPAGOS_IPCEG_FACTOR = original

    def test_unsealed_years_do_not_validate_and_only_near_years_warn(self):
        self.assertEqual(parameters_seal.verify_policy_parameters(2098, {}), [])
        self.assertEqual(parameters_seal.year_notice(2098), [])
        self.assertEqual(parameters_seal.year_notice(2026), [])
        self.assertTrue(parameters_seal.year_notice(date.today().year + 1))


@tagged('post_install', '-at_install')
class TaxRegistersCase(TransactionCase):
    _build_fixture = PersonalExemptionIntegrationCase._build_fixture
    _setup_employee_for_xml = PersonalExemptionIntegrationCase._setup_employee_for_xml
    _accredit = PersonalExemptionIntegrationCase._accredit
    _period = PersonalExemptionIntegrationCase._period
    _post = PersonalExemptionIntegrationCase._post

    def setUp(self):
        super().setUp()
        self._build_fixture()
        self.model = self.env['erpec.payroll.prior.employer']
        self.values = {
            'employee_id': self.employee.id, 'year': self.policy.year, 'origin_ruc': '0990000000001', 'origin_name': 'Empleador anterior S.A.',
            'document_number': 'F107-001', 'issued_date': date(2026, 1, 20), 'received_date': date(2026, 1, 25),
            'taxable_income': 10000, 'iess': 945, 'withheld_tax': 100}

    # ── sellado sobre el cálculo ─────────────────────────────────────────────
    def test_sealed_year_with_altered_policy_blocks_the_calculation(self):
        policy = self.env['erpec.payroll.policy'].create({
            'name': 'ALTERADA-2026', 'year': 2026, 'company_id': self.company.id, 'journal_id': self.journal.id,
            'parameters': json.dumps(dict(PARAMS, rebate_rate=0.2)), 'authorization': 'Ensayo de sello',
            'source_reference': 'Parámetros alterados a propósito'})
        period = self.env['erpec.payroll.period'].create({
            'name': 'SELLO-2026', 'policy_id': policy.id, 'month': 1,
            'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        self.assertIn('rebate_rate', period.tax_validation_notice)
        with self.assertRaisesRegex(ValidationError, 'sellados'):
            period.action_calculate()
        self.assertEqual(period.state, 'draft')

    def test_unsealed_synthetic_year_is_not_blocked_by_the_seal(self):
        period = self._period(3000)
        period.action_calculate()
        self.assertEqual(period.state, 'calculated')
        self.assertNotIn('Parámetros oficiales', period.tax_validation_notice)

    # ── registro idempotente y versionado ────────────────────────────────────
    def test_same_certificate_registered_twice_is_idempotent(self):
        first = self.model.create(self.values)
        second = self.model.create(dict(self.values))
        self.assertEqual(first, second)
        self.assertEqual(self.model.search_count([('employee_id', '=', self.employee.id)]), 1)
        self.assertEqual((first.version, first.state, first.hash_origin), (1, 'active', 'values'))

    def test_rectification_supersedes_with_log_and_never_duplicates_the_active_one(self):
        first = self.model.create(self.values)
        second = self.model.create(dict(self.values, withheld_tax=150))
        self.assertNotEqual(first, second)
        self.assertEqual((second.version, second.state, second.supersedes_id), (2, 'active', first))
        self.assertEqual(first.state, 'superseded')
        self.assertIn('withheld_tax: 100.00 → 150.00', second.change_log)
        self.assertEqual(self.model.search_count([('employee_id', '=', self.employee.id), ('state', '=', 'active')]), 1)
        again = self.model.create(dict(self.values, withheld_tax=150))
        self.assertEqual(again, second)
        third = self.model.create(dict(self.values, withheld_tax=100))
        self.assertEqual(third.version, 3)
        self.assertEqual(self.model.active_totals(self.company, self.employee, self.policy.year)['withheld_tax'], 100.0)

    def test_different_document_is_a_different_key(self):
        self.model.create(self.values)
        other = self.model.create(dict(self.values, document_number='F107-002', origin_ruc='0990000000002'))
        self.assertEqual(other.version, 1)
        totals = self.model.active_totals(self.company, self.employee, self.policy.year)
        self.assertEqual((totals['count'], totals['taxable_income']), (2, 20000.0))

    def test_file_hash_is_the_content_hash_and_a_different_file_is_a_new_version(self):
        content = b'contenido del comprobante'
        first = self.model.create(dict(self.values, document_file=base64.b64encode(content)))
        self.assertEqual((first.hash_origin, first.file_hash), ('file', hashlib.sha256(content).hexdigest()))
        self.assertEqual(self.model.create(dict(self.values, document_file=base64.b64encode(content))), first)
        second = self.model.create(dict(self.values, document_file=base64.b64encode(b'otro archivo')))
        self.assertEqual(second.version, 2)
        self.assertIn('sin cambio de importes', second.change_log)

    def test_certificate_validations(self):
        bad = {
            'origin_ruc': '123', 'iess': 20000, 'taxable_income': -1, 'year': 1999,
            'received_date': date(2999, 1, 1), 'document_number': '  ', 'issued_date': date(2026, 3, 1)}
        for key, value in bad.items():
            with self.subTest(key=key), self.assertRaises(ValidationError):
                self.model.create(dict(self.values, **{key: value}))
        self.company.with_context(no_vat_validation=True).write({'vat': self.values['origin_ruc']})
        with self.assertRaisesRegex(ValidationError, 'distinto'):
            self.model.create(self.values)

    def test_certificates_are_immutable_and_protected_fields_are_refused(self):
        record = self.model.create(self.values)
        with self.assertRaisesRegex(ValidationError, 'no se edita'):
            record.write({'taxable_income': 1})
        with self.assertRaisesRegex(ValidationError, 'no se eliminan'):
            record.unlink()
        for key, value in (('version', 9), ('state', 'active'), ('file_hash', 'x' * 64), ('supersedes_id', record.id)):
            with self.subTest(key=key), self.assertRaisesRegex(ValidationError, 'define el registro'):
                self.model.create(dict(self.values, document_number='OTRO', **{key: value}))

    def test_only_payroll_managers_can_register(self):
        user = new_test_user(self.env, login='sin_nomina_d8', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.model.with_user(user).create(self.values)

    # ── conciliación con las novedades ───────────────────────────────────────
    def _declared(self, **values):
        return dict({'other_employer_taxable_income': 10000, 'other_employer_iess': 945, 'other_employer_withheld_tax': 100}, **values)

    def test_declared_values_without_certificate_block_the_close(self):
        period = self._period(3000, **self._declared())
        period.action_calculate()
        self.assertIn('falta registrar el comprobante', period.tax_validation_notice)
        with self.assertRaisesRegex(ValidationError, 'D8'):
            period.action_close()

    def test_matching_certificate_unblocks_the_close_after_recalculating(self):
        period = self._period(3000, **self._declared())
        period.action_calculate()
        self.model.create(self.values)
        with self.assertRaisesRegex(ValidationError, 'cambiaron|D8'):
            period.action_close()  # el registro cambia la huella: hay que recalcular
        period.action_calculate()
        self.assertNotIn('D8', period.tax_validation_notice)
        period.action_close()
        self.assertEqual(period.state, 'closed')

    def test_mismatching_amounts_are_reported_with_both_figures(self):
        self.model.create(dict(self.values, withheld_tax=999))
        period = self._period(3000, **self._declared())
        period.action_calculate()
        self.assertIn('no concilian', period.tax_validation_notice)
        self.assertIn('withheld_tax', period.tax_validation_notice)
        with self.assertRaisesRegex(ValidationError, 'D8'):
            period.action_close()

    def test_rectified_certificate_reconciles_only_with_the_current_version(self):
        self.model.create(dict(self.values, withheld_tax=999))
        self.model.create(self.values)  # rectificación que iguala lo declarado
        period = self._period(3000, **self._declared())
        period.action_calculate()
        self.assertNotIn('D8', period.tax_validation_notice)
        period.action_close()

    def test_repeating_the_accumulated_values_every_month_is_detected(self):
        self.model.create(self.values)
        first = self._period(3000, **self._declared())
        first.action_calculate()
        first.action_close()
        first.action_post()
        second = self._period(3000, **self._declared())
        second.action_calculate()
        self.assertIn('no concilian', second.tax_validation_notice)
        with self.assertRaisesRegex(ValidationError, 'D8'):
            second.action_close()

    def test_certificate_not_incorporated_is_only_a_warning(self):
        self.model.create(self.values)
        period = self._period(3000)
        period.action_calculate()
        self.assertIn('no incorporan', period.tax_validation_notice)
        period.action_close()
        self.assertEqual(period.state, 'closed')

    def test_annex_uses_the_reconciliation_instead_of_a_generic_block(self):
        self.model.create(self.values)
        period = self._period(3000, **self._declared())
        period.action_calculate()
        period.action_close()
        period.action_post()
        annex = self._annex()
        self.assertNotIn('no concilian', annex.review_notice)
        self.model.create(dict(self.values, withheld_tax=500))
        annex._compute_review_notice()
        self.assertIn('Los datos cambiaron', annex.review_notice)
        annex.action_build()
        self.assertIn('no concilian', annex.review_notice)

    def test_other_employer_income_and_non_taxable_income_map_to_the_right_rdep_fields(self):
        # Catálogo RDEP vigente, hoja TABLAS: <intGrabGen> son los ingresos gravados con OTRO
        # empleador (lo que usa D8); <otrosIngRenGrav> son otros ingresos de ESTA relación que
        # NO constituyen renta gravada. El código tenía estos dos campos intercambiados; se
        # corrigió el 22-09-2026 al leer el catálogo que aportó el titular.
        self.model.create(self.values)
        period = self._period(3000, **self._declared())
        period.action_calculate()
        period.action_close()
        period.action_post()
        annex = self._annex()
        annex.line_ids.other_general_interest_income = 250  # otros ingresos no gravados de esta relación, no de otro empleador.
        annex.action_generate_xml()
        detail = etree.fromstring(base64.b64decode(annex.xml_file)).find('retRelDep/datRetRelDep')
        self.assertEqual(float(detail.find('intGrabGen').text), 10000.0)
        self.assertEqual(float(detail.find('otrosIngRenGrav').text), 250.0)

    def test_case_11_special_regimes_block_the_close(self):
        # Galápagos ya no bloquea por sí solo (18.0.1.14.12): aplica el factor IPCEG y tributa
        # normalmente. El convenio de doble imposición y el impuesto asumido siguen bloqueando.
        self.employee.ec_rdep_treaty_applies = 'SI'
        period = self._period(3000)
        period.action_calculate()
        self.assertIn('Caso 11', period.tax_validation_notice)
        with self.assertRaisesRegex(ValidationError, 'Caso 11'):
            period.action_close()
        self.employee.ec_rdep_treaty_applies = 'NO'
        assumed = self._period(3000, employer_assumed_tax=50)
        assumed.action_calculate()
        with self.assertRaisesRegex(ValidationError, 'Caso 11'):
            assumed.action_close()

    def test_galapagos_scales_the_wage_by_the_ipceg_factor_and_no_longer_blocks(self):
        # Caso 11 (criterio del titular, 23-09-2026): la Reforma a la LOREG unificó el incremento
        # salarial de Galápagos con el mismo IPCEG que el SRI usa en D5 (1,803, ya sellado).
        continental = self._period(3000)
        continental.action_calculate()
        self.employee.ec_rdep_ben_galpg = 'SI'
        galapagos = self._period(3000)
        galapagos.action_calculate()
        galapagos.action_close()  # ya no bloquea
        result_continental = json.loads(continental.line_ids.result)
        result_galapagos = json.loads(galapagos.line_ids.result)
        self.assertAlmostEqual(result_galapagos['salary'], result_continental['salary']*1.803, places=2)
        self.assertAlmostEqual(result_galapagos['personal_iess'], result_continental['personal_iess']*1.803, places=2)

    def test_case_11_non_resident_alone_no_longer_blocks_but_a_treaty_still_does(self):
        # Caso 11 (criterio del titular, 23-09-2026): un no residente bajo relación de
        # dependencia formal tributa igual que un residente; solo el convenio de doble
        # imposición sin regla aprobada bloquea.
        self.employee.write({'ec_rdep_residence_country': '110', 'ec_rdep_fiscal_residence': '02', 'ec_rdep_treaty_applies': 'NO'})  # 110 = Estados Unidos, catálogo RDEP
        period = self._period(3000)
        period.action_calculate()
        period.action_close()  # no lanza ValidationError
        self.employee.ec_rdep_treaty_applies = 'SI'
        with_treaty = self._period(3000)
        with_treaty.action_calculate()
        with self.assertRaisesRegex(ValidationError, 'Caso 11'):
            with_treaty.action_close()

    # ── conciliación nómina ↔ mayor ↔ RDEP (caso 10) ─────────────────────────
    def test_ledger_reconciles_and_a_tampered_move_is_detected(self):
        period = self._period(3000)
        period.action_calculate()
        period.action_close()
        period.action_post()
        annex = self._annex()
        self.assertNotIn('Conciliación ·', annex.review_notice)
        self.env.cr.execute('UPDATE account_move_line SET debit = debit + 5 WHERE move_id = %s AND debit > 0', [period.move_id.id])
        self.env.invalidate_all()
        annex._compute_review_notice()
        self.assertIn('no coinciden con la nómina', annex.review_notice)
        with self.assertRaisesRegex(ValidationError, 'Conciliación'):
            annex.action_generate_xml()

    def test_annual_retention_gap_is_reported_per_employee(self):
        period = self._period(3000)
        period.action_calculate()
        period.action_close()
        period.action_post()
        annex = self._annex()
        self.assertIn('Conciliación D6', annex.review_notice)
        self.assertIn(self.employee.name, annex.review_notice)

    def _annex(self):
        return PersonalExemptionIntegrationCase._annex(self)
