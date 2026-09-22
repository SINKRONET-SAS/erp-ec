"""Pruebas del agregador RDEP: consolidación de nómina y vista previa XML validada contra el esquema oficial."""
import base64
import hashlib
import json
from pathlib import Path
from lxml import etree
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged
from ..demo_parameters import PARAMS
from ..engine import calculate


@tagged('post_install', '-at_install')
class RdepAnnexCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self._build_fixture()

    def _build_fixture(self):
        """Empresa, política activa, empleado y tercero sintéticos; la reutilizan otras pruebas del anexo."""
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

    def test_bundled_schema_is_the_official_sri_rdep_schema(self):
        # D5: el esquema descargado por el titular de https://www.sri.gob.ec/formularios-e-instructivos1
        # (addons/erpec_payroll/xsd/Esquema_RDEP_2023.xsd, tal como lo publica el SRI) coincide, salvo el fin de línea, con el que valida el anexo.
        schema = (Path(__file__).resolve().parent.parent / 'xsd/Esquema_RDEP_2023.xsd').read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(hashlib.sha256(schema).hexdigest(), '8d595d42c17948ca9f4f5bf5bf4fff18ae9ddac5f3fb1f2a5670ba3ec2783636')

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
        self.employee.write({'ec_rdep_disability_type': '02', 'ec_rdep_disability_percentage': 40, 'ec_rdep_dependents_count': 2})
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

    def _setup_employee_for_xml(self, employee):
        employee.write({
            'ec_rdep_id_type': 'C', 'identification_id': '1712345678', 'ec_rdep_establishment': '001',
            'ec_rdep_fiscal_residence': '00', 'ec_rdep_residence_country': '593',
            'ec_rdep_treaty_applies': 'NO', 'ec_rdep_disability_type': '01',
        })

    def test_engine_exposes_annual_tax_fields_without_duplicating(self):
        result = calculate({'start_date': '2025-01-01', 'wage': 1200, 'personal_expenses': 1000}, PARAMS, 2098, 9)
        self.assertIn('annual_tax_caused', result)
        self.assertIn('personal_expense_rebate', result)
        self.assertIn('annual_tax_after_rebate', result)
        self.assertAlmostEqual(result['annual_tax_after_rebate'], max(0.0, result['annual_tax_caused'] - result['personal_expense_rebate']), places=2)

    def test_generate_xml_validates_against_official_schema(self):
        self._post_period(6)
        self._setup_employee_for_xml(self.employee)
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        with self.assertRaises(ValidationError):
            annex.action_generate_xml()
        self.company.with_context(no_vat_validation=True).write({'vat': '1790012345001'})
        annex.action_build()
        annex.action_generate_xml()
        self.assertEqual(annex.state, 'generated')
        decoded = base64.b64decode(annex.xml_file)
        self.assertEqual(hashlib.sha256(decoded).hexdigest(), annex.digest)
        schema = etree.XMLSchema(etree.parse(str(Path(__file__).parent.parent / 'xsd/Esquema_RDEP_2023.xsd')))
        tree = etree.fromstring(decoded)
        self.assertTrue(schema.validate(tree), schema.error_log)
        self.assertEqual(tree.find('numRuc').text, '1790012345001')
        self.assertEqual(tree.find('retRelDep/datRetRelDep/empleado/tipIdRet').text, 'C')

    def test_education_and_art_culture_merge_into_deducEducartcult(self):
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-12', 'policy_id': self.policy.id, 'month': 12, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True, 'expense_education': 10, 'expense_art_culture': 5})]})
        period.action_calculate()
        period.action_close()
        period.action_post()
        self._setup_employee_for_xml(self.employee)
        self.company.with_context(no_vat_validation=True).write({'vat': '1790012345001'})
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        annex.action_generate_xml()
        tree = etree.fromstring(base64.b64decode(annex.xml_file))
        detail = tree.find('retRelDep/datRetRelDep')
        self.assertEqual(detail.find('deducEducartcult').text, '15.0')
        self.assertIsNone(detail.find('deducEduca'))
        self.assertIsNone(detail.find('deducArtycult'))

    def test_generate_xml_requires_complete_employee_data(self):
        self._post_period(7)
        self.company.with_context(no_vat_validation=True).write({'vat': '1790012345001'})
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        with self.assertRaises(ValidationError):
            annex.action_generate_xml()

    def test_employer_assumed_tax_is_blocked_until_independent_validation(self):
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-8', 'policy_id': self.policy.id, 'month': 8, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True, 'employer_assumed_tax': 50})]})
        period.action_calculate()
        # La observación ahora se detecta antes de generar el asiento.
        with self.assertRaisesRegex(ValidationError, 'Impuesto asumido'):
            period.action_close()
        self.assertFalse(period.move_id)
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        self.assertTrue(annex._coverage_issues(period))

    def test_expense_caps_enforced_as_single_total_by_dependents(self):
        # Boletín NAC-COM-26-006 (SRI): tope único total, sin tope por categoría,
        # según cargas familiares (0 cargas = expense_limit tal cual, 7 canastas).
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-9', 'policy_id': self.policy.id, 'month': 9, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        cap = json.loads(self.policy.parameters)['expense_limit']
        with self.assertRaises(ValidationError), self.cr.savepoint():
            period.line_ids.write({'expense_housing': cap / 2 + 1, 'expense_health': cap / 2 + 1})
        period.line_ids.write({'expense_housing': cap / 2, 'expense_health': cap / 2})

    def test_expense_cap_scales_with_dependents_and_galapagos(self):
        # El tope esperado se calcula con la misma función que usa el código
        # (engine.personal_expense_cap, aritmética Decimal) para no comparar
        # contra un cálculo en punto flotante ligeramente distinto en el límite.
        from ..engine import personal_expense_cap
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-11', 'policy_id': self.policy.id, 'month': 11, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        baseline = json.loads(self.policy.parameters)['expense_limit']
        self.employee.write({'ec_rdep_dependents_count': 2})  # 11 canastas en vez de 7
        cap_with_dependents = float(personal_expense_cap(baseline, 2, 'NO'))
        with self.assertRaises(ValidationError), self.cr.savepoint():
            period.line_ids.write({'expense_food': cap_with_dependents + 1})
        period.line_ids.write({'expense_food': cap_with_dependents})
        self.employee.write({'ec_rdep_ben_galpg': 'SI'})
        cap_galapagos = float(personal_expense_cap(baseline, 2, 'SI'))
        period.line_ids.write({'expense_food': cap_galapagos})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            period.line_ids.write({'expense_food': cap_galapagos + 1})

    def test_monthly_engine_uses_employee_dependents_and_galapagos_cap(self):
        # El hallazgo colateral: engine.calculate() no escalaba el tope por
        # cargas/Galápagos, afectando la retención mensual real, no solo RDEP.
        # Corregido: Line._inputs() agrega dependents_count/galapagos del
        # empleado; engine.personal_expense_cap() es la única implementación.
        self.employee.write({'ec_rdep_dependents_count': 1})
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-14', 'policy_id': self.policy.id, 'month': 8, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 3000, 'approved': True, 'personal_expenses': 6000})]})
        period.action_calculate()
        with_dependent = json.loads(period.line_ids.result)['tax']
        period.action_reopen()
        self.employee.write({'ec_rdep_dependents_count': 0})
        period.action_calculate()
        without_dependent = json.loads(period.line_ids.result)['tax']
        self.assertLess(with_dependent, without_dependent)

    def test_action_correct_still_works_with_employee_derived_inputs(self):
        # _copy_inputs() (usado por action_correct) no debe intentar escribir
        # dependents_count/galapagos como campos de erpec.payroll.line: esos
        # solo viajan por _inputs(), exclusivo de calculate().
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-15', 'policy_id': self.policy.id, 'month': 10, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        period.action_calculate()
        period.action_close()
        period.action_post()
        period.action_reverse()
        action = period.action_correct()
        correction = self.env['erpec.payroll.period'].browse(action['res_id'])
        self.assertEqual(correction.state, 'draft')
        correction.action_calculate()
        self.assertEqual(correction.state, 'calculated')

    def test_education_and_art_culture_merge_for_reporting_not_for_cap(self):
        # Educación y arte/cultura se fusionan en deducEducartcult para el XML,
        # pero el tope ya no es por categoría: comparten el tope único total.
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-13', 'policy_id': self.policy.id, 'month': 4, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})
        cap = json.loads(self.policy.parameters)['expense_limit']
        period.line_ids.write({'expense_education': cap / 2, 'expense_art_culture': cap / 2})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            period.line_ids.write({'expense_art_culture': cap / 2 + 1})

    def test_correction_copies_rdep_novelties(self):
        period = self.env['erpec.payroll.period'].create({'name': 'ENSAYO-RDEP-10', 'policy_id': self.policy.id, 'month': 10, 'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True, 'annual_profit_sharing': 300, 'expense_health': 20})]})
        period.action_calculate()
        period.action_close()
        period.action_post()
        period.action_reverse()
        action = period.action_correct()
        correction = self.env['erpec.payroll.period'].browse(action['res_id'])
        self.assertEqual(correction.line_ids.annual_profit_sharing, 300)
        self.assertEqual(correction.line_ids.expense_health, 20)

    def test_di25_variable_year_uses_actual_accumulated_base(self):
        # Oráculo aritmético independiente con parámetros sintéticos:
        # 11*1000+3000=14000; IESS=1400; base=12600; (12600-12000)*10%=60.
        for month in [12, 3, 1, 9, 2, 7, 11, 5, 6, 4, 10, 8]:
            period = self.env['erpec.payroll.period'].create({
                'name': 'DI25 variable %s' % month, 'policy_id': self.policy.id, 'month': month,
                'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id,
                    'start_date': '2025-01-01', 'wage': 3000 if month == 12 else 1000, 'approved': True})]})
            period.action_calculate()
            period.action_close()
            period.action_post()
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        self.assertEqual(annex.line_ids.base, 14000)
        self.assertEqual(annex.line_ids.personal_iess, 1400)
        self.assertEqual(annex.line_ids.annual_tax_caused, 60)
        annex.action_build()
        self.assertEqual(annex.line_ids.annual_tax_caused, 60)

    def test_di25_annual_table_2026_independent_oracle(self):
        from ..engine import annual_income_tax
        from ..parameters_ec2026 import PARAMS as params_2026
        # SRI 2026: (12677 - 12208) * 5% = 23.45; rebaja 100 * 18% = 18.
        caused, rebate, remaining = annual_income_tax(12677, 100, params_2026)
        self.assertEqual(float(caused), 23.45)
        self.assertEqual(float(rebate), 18)
        self.assertEqual(float(remaining), 5.45)

    def test_di25_rdep_blocks_special_regimes_and_stale_sources(self):
        period = self._post_period(1)
        self._setup_employee_for_xml(self.employee)
        self.company.with_context(no_vat_validation=True).write({'vat': '1790012345001'})
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        annex.action_generate_xml()
        accreditation = {'ec_rdep_exemption_year': self.policy.year, 'ec_rdep_exemption_ref': 'DOC-SINTETICO-1'}
        # Exenciones acreditadas de forma incompleta o no cubierta bloquean; sin acreditación solo avisan.
        for values in [dict(accreditation, ec_rdep_exemption_date='%s-01-20' % self.policy.year,
                            ec_rdep_disability_type='02', ec_rdep_disability_percentage=40),
                       dict(accreditation, ec_rdep_exemption_date='%s-01-10' % self.policy.year,
                            ec_rdep_disability_type='01', ec_rdep_disability_percentage=0,
                            birthday='%s-06-01' % (self.policy.year-64)),
                       {'birthday': False, 'ec_rdep_ben_galpg': 'SI', 'ec_rdep_exemption_ref': False, 'ec_rdep_exemption_date': False}]:
            self.employee.write(values)
            annex.action_build()
            self.assertFalse(annex.xml_file)
            with self.assertRaisesRegex(ValidationError, 'XML bloqueado'):
                annex.action_generate_xml()
        self.employee.ec_rdep_ben_galpg = 'NO'
        annex.action_build()
        annex.action_generate_xml()
        period.action_reverse()
        with self.assertRaisesRegex(ValidationError, 'datos cambiaron'):
            annex.action_generate_xml()

    def test_di25_actual_expenses_and_benefits_reconcile_xml(self):
        period = self.env['erpec.payroll.period'].create({
            'name': 'DI25 beneficios XML', 'policy_id': self.policy.id, 'month': 1,
            'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id,
                'start_date': '2025-01-01', 'wage': 15000, 'approved': True,
                'expense_health': 100, 'personal_expenses': 4000})]})
        benefit = self.env['erpec.payroll.benefit.type'].create({'name': 'DI25 beneficio gravado', 'taxable': True})
        period.line_ids.benefit_line_ids = [(0, 0, {'benefit_type_id': benefit.id, 'amount': 1000})]
        period.action_calculate()
        period.action_close()
        period.action_post()
        self._setup_employee_for_xml(self.employee)
        self.company.with_context(no_vat_validation=True).write({'vat': '1790012345001'})
        annex = self.env['erpec.payroll.rdep'].create({'company_id': self.company.id, 'year': self.policy.year})
        annex.action_build()
        self.assertEqual(annex.line_ids.bonus_commission, 1000)
        self.assertEqual(annex.line_ids.annual_base, 14400)
        self.assertEqual(annex.line_ids.annual_tax_caused, 240)
        self.assertEqual(annex.line_ids.personal_expense_rebate, 18)
        annex.action_generate_xml()
        tree = etree.fromstring(base64.b64decode(annex.xml_file))
        detail = tree.find('retRelDep/datRetRelDep')
        self.assertEqual(float(detail.find('basImp').text), 14400)
        self.assertEqual(float(detail.find('impRentCaus').text), 240)
        self.assertEqual(float(detail.find('sobSuelComRemu').text), 1000)
