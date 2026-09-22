"""Exenciones personales (LRTI art. 9 num. 12) contra oráculos aritméticos independientes del motor."""
import base64
import json
from datetime import date
from lxml import etree
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from ..engine import (apply_personal_exemption, calculate, disability_benefit_percent,
                      personal_exemption_amount, resolve_exemption_claims, resolve_special_expense)
from ..parameters_ec2026 import PARAMS as PARAMS_2026
from .test_annex_rdep import RdepAnnexCase


@tagged('post_install', '-at_install')
class PersonalExemptionEngineCase(TransactionCase):
    """Fracción básica 2026 = 12.208. Cada valor esperado se calculó a mano."""

    def test_official_scale_and_amounts(self):
        # Reglamento LOD art. 6: 30-49 → 60 %, 50-74 → 70 %, 75-84 → 80 %, 85-100 → 100 %.
        expected = {30: 14649.60, 40: 14649.60, 49: 14649.60, 50: 17091.20, 74: 17091.20,
                    75: 19532.80, 84: 19532.80, 85: 24416.00, 100: 24416.00}
        for percentage, amount in expected.items():
            with self.subTest(percentage=percentage):
                self.assertEqual(float(personal_exemption_amount(PARAMS_2026, {'kind': 'disability', 'percentage': percentage})), amount)
        self.assertEqual(float(personal_exemption_amount(PARAMS_2026, {'kind': 'elderly'})), 12208)
        for invalid in (0, 29, 101, -1, 40.5):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                disability_benefit_percent(invalid)

    def test_substitute_is_proportional_and_holder_is_not(self):
        claim = {'kind': 'substitute', 'percentage': 80, 'months': 6}
        self.assertEqual(float(personal_exemption_amount(PARAMS_2026, claim)), 9766.40)
        for months in (0, 13, 2.5):
            with self.subTest(months=months), self.assertRaises(ValueError):
                personal_exemption_amount(PARAMS_2026, dict(claim, months=months))
        with self.assertRaises(ValueError):
            personal_exemption_amount(PARAMS_2026, {'kind': 'disability', 'percentage': 80, 'months': 6})
        with self.assertRaises(ValueError):
            personal_exemption_amount(PARAMS_2026, {'kind': 'unknown'})

    def test_best_exemption_is_applied_never_the_sum(self):
        elderly, disability40 = {'kind': 'elderly'}, {'kind': 'disability', 'percentage': 40}
        kind, amount, taxable = apply_personal_exemption(27165, PARAMS_2026, [elderly, disability40])
        self.assertEqual((kind, float(amount), float(taxable)), ('disability', 14649.60, 12515.40))
        small_substitute = {'kind': 'substitute', 'percentage': 30, 'months': 1}
        kind, amount, taxable = apply_personal_exemption(27165, PARAMS_2026, [small_substitute, elderly])
        self.assertEqual((kind, float(amount), float(taxable)), ('elderly', 12208, 14957))
        self.assertEqual(apply_personal_exemption(27165, PARAMS_2026, [])[0], 'none')

    def test_exemption_is_limited_by_available_base(self):
        kind, amount, taxable = apply_personal_exemption(9055, PARAMS_2026, [{'kind': 'elderly'}])
        self.assertEqual((kind, float(amount), float(taxable)), ('elderly', 9055, 0))
        self.assertEqual(apply_personal_exemption(0, PARAMS_2026, [{'kind': 'elderly'}])[0], 'none')

    def test_monthly_calculation_uses_the_common_exemption(self):
        # 2.500 − 9,45 % = 2.263,75 × 12 = 27.165. Sin exención 1.481,75 / 12 = 123,48.
        data = {'start_date': '2025-01-01', 'wage': 2500}
        plain = calculate(data, PARAMS_2026, 2026, 3)
        self.assertEqual(plain['tax'], 123.48)
        self.assertEqual(plain['personal_exemption'], 0)
        # 14.957 → 137,45 / 12 = 11,45.
        elderly = calculate(dict(data, exemptions=[{'kind': 'elderly'}]), PARAMS_2026, 2026, 3)
        self.assertEqual((elderly['tax'], elderly['personal_exemption']), (11.45, 12208))
        self.assertEqual(calculate(dict(data, exemptions=[]), PARAMS_2026, 2026, 3), plain)
        self.assertEqual(calculate(dict(data, special_expense=False), PARAMS_2026, 2026, 3), plain)

    def test_resolution_requires_current_year_accreditation(self):
        january = date(2026, 1, 10)
        cases = [
            # (nacimiento, tipo, %, tipo id, id, año, ref, fecha, meses) → reclamos, incidencias, avisos
            (date(1950, 5, 1), '01', 0, 'N', '', 2026, 'DOC-1', january, 12, [{'kind': 'elderly'}], 0, 0),
            # D1 (titular, 21-09-2026): el adulto mayor se reconoce por la edad, sin acreditación documental.
            (date(1950, 5, 1), '01', 0, 'N', '', 2025, 'DOC-1', january, 12, [{'kind': 'elderly'}], 0, 0),
            (date(1950, 5, 1), '01', 0, 'N', '', 2026, '', january, 12, [{'kind': 'elderly'}], 0, 0),
            (date(1950, 5, 1), '01', 0, 'N', '', 2026, 'DOC-1', False, 12, [{'kind': 'elderly'}], 0, 0),
            (date(1950, 5, 1), '01', 0, 'N', '', None, '', False, 12, [{'kind': 'elderly'}], 0, 0),
            (date(1950, 5, 1), '02', 50, 'N', '', None, '', False, 12, [{'kind': 'elderly'}], 0, 1),
            (date(1990, 5, 1), '02', 50, 'N', '', 2026, 'DOC-1', january, 12, [{'kind': 'disability', 'percentage': 50}], 0, 0),
            (date(1990, 5, 1), '02', 29, 'N', '', 2026, 'DOC-1', january, 12, [], 1, 0),
            (date(1990, 5, 1), '02', 0, 'N', '', 2026, 'DOC-1', january, 12, [], 1, 0),
            (date(1990, 5, 1), '00', 50, 'N', '', 2026, 'DOC-1', january, 12, [], 1, 0),
            (date(1990, 5, 1), '04', 50, 'N', '', 2026, 'DOC-1', january, 12, [], 1, 0),
            (date(1990, 5, 1), '01', 0, 'N', '', 2026, 'DOC-1', january, 12, [], 1, 0),
            (date(1990, 5, 1), '02', 50, 'N', '', 2026, 'DOC-1', date(2026, 1, 16), 12, [], 1, 0),
            (date(1990, 5, 1), '02', 50, 'N', '', 2026, 'DOC-1', date(2026, 1, 15), 12, [{'kind': 'disability', 'percentage': 50}], 0, 0),
            (date(1990, 5, 1), '03', 50, 'C', '1712345678', 2026, 'DOC-1', january, 6, [{'kind': 'substitute', 'percentage': 50, 'months': 6}], 0, 0),
            (date(1990, 5, 1), '03', 50, 'N', '', 2026, 'DOC-1', january, 6, [], 1, 0),
            (date(1990, 5, 1), '03', 50, 'C', '1712345678', 2026, 'DOC-1', january, 0, [], 1, 0),
            # D1: cumple 65 años en cualquier fecha del ejercicio.
            (date(1961, 6, 1), '01', 0, 'N', '', 2026, 'DOC-1', january, 12, [{'kind': 'elderly'}], 0, 0),
            (date(1961, 1, 1), '01', 0, 'N', '', 2026, 'DOC-1', january, 12, [{'kind': 'elderly'}], 0, 0),
            (date(1961, 1, 2), '01', 0, 'N', '', 2026, 'DOC-1', january, 12, [{'kind': 'elderly'}], 0, 0),
        ]
        for index, (born, kind, percent, id_type, ident, year, ref, delivered, months, claims, issues, notes) in enumerate(cases):
            with self.subTest(case=index):
                result = resolve_exemption_claims(2026, born, kind, percent, id_type, ident, year, ref, delivered, months)
                self.assertEqual((result[0], len(result[1]), len(result[2])), (claims, issues, notes), result)

    def test_elderly_and_disability_together_keep_both_claims_for_the_best_choice(self):
        claims, issues, _ = resolve_exemption_claims(
            2026, date(1950, 1, 1), '02', 40, 'N', '', 2026, 'DOC-1', date(2026, 1, 5))
        self.assertEqual(issues, [])
        self.assertEqual([claim['kind'] for claim in claims], ['elderly', 'disability'])

    def test_special_expense_resolution(self):
        self.assertEqual(resolve_special_expense(2026, 'none', None, None, 0), (False, []))
        self.assertEqual(resolve_special_expense(2026, False, None, None, 0), (False, []))
        self.assertEqual(resolve_special_expense(2026, 'holder', 2026, 'CERT-1', 0), (True, []))
        self.assertEqual(resolve_special_expense(2026, 'dependent', 2026, 'CERT-1', 1), (True, []))
        for args in (('holder', 2025, 'CERT-1', 0), ('holder', 2026, '', 0), ('dependent', 2026, 'CERT-1', 0), ('other', 2026, 'CERT-1', 1)):
            with self.subTest(args=args):
                applies, issues = resolve_special_expense(2026, *args)
                self.assertFalse(applies)
                self.assertTrue(issues)


@tagged('post_install', '-at_install')
class PersonalExemptionIntegrationCase(TransactionCase):
    """Integración con nómina mensual y RDEP. Política sintética: fracción 12.000, tarifa 10 %, IESS 10 %."""
    _build_fixture = RdepAnnexCase._build_fixture
    _setup_employee_for_xml = RdepAnnexCase._setup_employee_for_xml

    def setUp(self):
        super().setUp()
        self._build_fixture()

    def _accredit(self, **values):
        year = self.policy.year
        base = {'ec_rdep_exemption_year': year, 'ec_rdep_exemption_ref': 'DOC-SINTETICO-1',
                'ec_rdep_exemption_date': date(year, 1, 10)}
        self.employee.write(dict(base, **values))

    def _period(self, wage, **novelties):
        # El mes es único por empresa, año y versión: cada período de la prueba usa el siguiente.
        self._month = getattr(self, '_month', 0)+1
        return self.env['erpec.payroll.period'].create({
            'name': 'EXENCION-%s-%s' % (self._month, wage), 'policy_id': self.policy.id, 'month': self._month,
            'line_ids': [(0, 0, dict({'employee_id': self.employee.id, 'partner_id': self.partner.id,
                                      'start_date': '2025-01-01', 'wage': wage, 'approved': True}, **novelties))]})

    def _monthly_tax(self, wage=3000, **novelties):
        period = self._period(wage, **novelties)
        period.action_calculate()
        return json.loads(period.line_ids.result)

    def _post(self, wage):
        period = self._period(wage)
        period.action_calculate()
        period.action_close()
        period.action_post()
        return period

    def _annex(self):
        self.company.with_context(no_vat_validation=True).write({'vat': '1790012345001'})
        if not self.employee.ec_rdep_id_type:  # los datos del XML se completan una vez; no pisan el tipo de discapacidad de la prueba
            self._setup_employee_for_xml(self.employee)
        annex = self.env['erpec.payroll.rdep'].search([('company_id', '=', self.company.id), ('year', '=', self.policy.year)])
        annex = annex or self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        return annex

    def test_monthly_retention_uses_only_accredited_exemptions(self):
        # 3.000 − 10 % = 2.700 × 12 = 32.400. Sin exención: (32.400 − 12.000) × 10 % = 2.040 → 170/mes.
        result = self._monthly_tax()
        self.assertEqual((result['tax'], result['personal_exemption']), (170, 0))
        self.employee.write({'ec_rdep_disability_type': '02', 'ec_rdep_disability_percentage': 50})
        self.assertEqual(self._monthly_tax()['tax'], 170)  # condición sin acreditación: no se aplica
        # 24.000 × 70 % = 16.800; base 15.600; 3.600 × 10 % = 360 → 30/mes.
        self._accredit()
        result = self._monthly_tax()
        self.assertEqual((result['tax'], result['personal_exemption']), (30, 16800))
        # Otro año de acreditación: no aplica.
        self.employee.ec_rdep_exemption_year = self.policy.year - 1
        self.assertEqual(self._monthly_tax()['tax'], 170)

    def test_best_of_elderly_and_disability_never_added(self):
        # Adulto mayor 12.000 frente a discapacidad 40 % = 14.400: rige 14.400; base 18.000 → 600 → 50/mes.
        self.employee.write({'birthday': date(self.policy.year-70, 1, 1)})
        self._accredit(ec_rdep_disability_type='02', ec_rdep_disability_percentage=40)
        result = self._monthly_tax()
        self.assertEqual((result['tax'], result['personal_exemption']), (50, 14400))

    def test_substitute_months_and_required_identification(self):
        # 24.000 × 100 % × 6/12 = 12.000; base 20.400 → 840 → 70/mes.
        self._accredit(ec_rdep_disability_type='03', ec_rdep_disability_percentage=100, ec_rdep_exemption_months=6,
                       ec_rdep_disability_id_type='C', ec_rdep_disability_id='1799999999')
        self.assertEqual(self._monthly_tax()['tax'], 170)  # D4: meses y referencia no acreditan sustitución.
        self.employee.ec_rdep_disability_id = False
        self.assertEqual(self._monthly_tax()['tax'], 170)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.employee.ec_rdep_exemption_months = 13

    def test_special_expense_cap_reaches_monthly_retention_and_line_validation(self):
        # Gastos 6.000: tope general 5.000 → rebaja 900 → 1.140 → 95/mes; con 100 canastas → rebaja 1.080 → 960 → 80/mes.
        self.assertEqual(self._monthly_tax(personal_expenses=6000)['tax'], 95)
        self.employee.write({'ec_rdep_special_expense': 'holder', 'ec_rdep_special_expense_year': self.policy.year,
                             'ec_rdep_special_expense_ref': 'CERT-SINTETICO-1'})
        self.assertEqual(self._monthly_tax(personal_expenses=6000)['tax'], 95)  # D7: referencia aislada bloqueada.
        self.employee.ec_rdep_special_expense_ref = False
        self.assertEqual(self._monthly_tax(personal_expenses=6000)['tax'], 95)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._period(3000, expense_food=6000)
        self.employee.ec_rdep_special_expense_ref = 'CERT-SINTETICO-1'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._period(3000, expense_food=6000)

    def test_annual_rdep_reports_accredited_exemption_in_the_right_field(self):
        # 40.000 − IESS 4.000 = 36.000. Adulto mayor 12.000 → 24.000 → 1.200. Sin exención, 2.400.
        self.employee.write({'birthday': date(self.policy.year-70, 1, 1)})
        self._accredit()
        self._post(40000)
        annex = self._annex()
        line = annex.line_ids
        self.assertEqual((line.personal_exemption_kind, line.personal_exemption, line.annual_base, line.annual_tax_caused),
                         ('elderly', 12000, 24000, 1200))
        annex.action_generate_xml()
        detail = etree.fromstring(base64.b64decode(annex.xml_file)).find('retRelDep/datRetRelDep')
        self.assertEqual([float(detail.find(tag).text) for tag in ('exoTerEd', 'exoDiscap', 'basImp', 'impRentCaus')],
                         [12000, 0, 24000, 1200])
        # Discapacidad 50 %: 16.800 → 19.200 → 720, en exoDiscap.
        self.employee.write({'birthday': False, 'ec_rdep_disability_type': '02', 'ec_rdep_disability_percentage': 50})
        annex = self._annex()
        annex.action_generate_xml()
        detail = etree.fromstring(base64.b64decode(annex.xml_file)).find('retRelDep/datRetRelDep')
        self.assertEqual([float(detail.find(tag).text) for tag in ('exoDiscap', 'exoTerEd', 'basImp', 'impRentCaus')],
                         [16800, 0, 19200, 720])

    def test_elderly_is_recognized_by_age_without_accreditation_but_disability_is_not(self):
        # D1 (titular, 21-09-2026): 12.000 de exención por la edad, sin documento; 36.000 → 24.000 → 1.200.
        self.employee.write({'birthday': date(self.policy.year-70, 1, 1)})
        self._post(40000)
        annex = self._annex()
        self.assertEqual((annex.line_ids.personal_exemption_kind, annex.line_ids.personal_exemption, annex.line_ids.annual_tax_caused),
                         ('elderly', 12000, 1200))
        self.assertNotIn('sin acreditación', annex.review_notice or '')
        # La discapacidad detectada sin documento sigue sin aplicarse y avisa.
        self.employee.write({'birthday': False, 'ec_rdep_disability_type': '02', 'ec_rdep_disability_percentage': 50})
        annex = self._annex()
        self.assertEqual((annex.line_ids.personal_exemption, annex.line_ids.annual_tax_caused), (0, 2400))
        self.assertIn('sin acreditación', annex.review_notice)

    def test_inconsistent_accreditation_blocks_xml_without_applying_it(self):
        self.employee.write({'ec_rdep_disability_type': '02', 'ec_rdep_disability_percentage': 50})
        self._post(40000)
        variants = [
            {'ec_rdep_exemption_date': date(self.policy.year, 1, 20)},
            {'ec_rdep_disability_percentage': 29},
            {'ec_rdep_disability_type': '00'},
            {'ec_rdep_disability_type': '01'},
        ]
        for values in variants:
            with self.subTest(values=values):
                self._accredit(ec_rdep_disability_type='02', ec_rdep_disability_percentage=50)
                self.employee.write(values)
                annex = self._annex()
                self.assertEqual(annex.line_ids.personal_exemption, 0)
                with self.assertRaisesRegex(ValidationError, 'XML bloqueado'):
                    annex.action_generate_xml()

    def test_special_expense_inconsistency_and_rdep_cap(self):
        self._post(40000)
        self.employee.write({'ec_rdep_special_expense': 'dependent', 'ec_rdep_special_expense_year': self.policy.year,
                             'ec_rdep_special_expense_ref': 'CERT-SINTETICO-1', 'ec_rdep_dependents_count': 0})
        annex = self._annex()
        with self.assertRaisesRegex(ValidationError, 'XML bloqueado'):
            annex.action_generate_xml()
        self.employee.ec_rdep_dependents_count = 1
        annex = self._annex()
        with self.assertRaisesRegex(ValidationError, 'D7'):
            annex.action_generate_xml()

    def test_views_expose_accreditation_fields(self):
        manager = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Responsable exenciones', 'login': 'rdep_exemption_view', 'company_id': self.company.id,
            'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('erpec_payroll.group_payroll_manager').id])]})
        arch = self.env['hr.employee'].with_user(manager).get_view(view_type='form')['arch']
        for name in ('ec_rdep_exemption_ref', 'ec_rdep_exemption_date', 'ec_rdep_special_expense'):
            self.assertIn(name, arch)
        self.assertIn('personal_exemption', self.env['erpec.payroll.rdep'].with_user(manager).get_view(view_type='form')['arch'])
