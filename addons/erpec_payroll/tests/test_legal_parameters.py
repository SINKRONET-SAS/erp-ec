"""Pruebas de los campos tipados de erpec.payroll.policy (sustituyen la edición manual del
JSON de `parameters`, adaptado del patrón de nuevo_nomina: legal_parameter_versions con
columnas propias). Cubre ambas direcciones de sincronización y que el motor de cálculo sigue
consumiendo exactamente el mismo `parameters` que antes."""
import json

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..demo_parameters import PARAMS
from ..engine import calculate, validate_parameters


@tagged('post_install', '-at_install')
class LegalParameterCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.journal = self.env['account.journal'].create({'name': 'Nómina ensayo params', 'code': 'PYTP', 'type': 'general'})

    def _base_values(self, **extra):
        return dict({
            'name': 'ENSAYO-PARAMS-' + str(id(extra) % 100000), 'year': 2097, 'journal_id': self.journal.id,
            'authorization': 'Ensayo local de parámetros tipados', 'source_reference': 'Parámetros ficticios para pruebas',
        }, **extra)

    def _structured_values(self):
        return {
            'minimum_salary': PARAMS['minimum_salary'], 'monthly_hours': PARAMS['monthly_hours'],
            'personal_rate': PARAMS['personal_rate'], 'employer_rate': PARAMS['employer_rate'],
            'employer_other_rate': 0.01, 'reserve_rate': PARAMS['reserve_rate'],
            'reserve_months': PARAMS['reserve_months'], 'thirteenth_rate': PARAMS['thirteenth_rate'],
            'fourteenth_rate': PARAMS['fourteenth_rate'], 'vacation_rate': PARAMS['vacation_rate'],
            'expense_limit': PARAMS['expense_limit'], 'rebate_rate': PARAMS['rebate_rate'],
            'overtime_50': PARAMS['overtime_50'], 'overtime_100': PARAMS['overtime_100'],
            'night_rate': PARAMS['night_rate'],
            'tax_bracket_ids': [(0, 0, {
                'sequence': index, 'income_from': bracket['from'], 'income_to': bracket['to'] or 0,
                'open_ended': bracket['to'] is None, 'base_tax': bracket['base'], 'rate': bracket['rate'],
            }) for index, bracket in enumerate(PARAMS['tax_brackets'])],
        }

    def test_create_from_structured_fields_derives_valid_json(self):
        policy = self.env['erpec.payroll.policy'].create(self._base_values(**self._structured_values()))
        self.assertTrue(policy.parameters)
        params = json.loads(policy.parameters)
        validate_parameters(params)
        self.assertEqual(params['minimum_salary'], PARAMS['minimum_salary'])
        self.assertEqual(len(params['tax_brackets']), len(PARAMS['tax_brackets']))
        self.assertIsNone(params['tax_brackets'][-1]['to'])

    def test_create_from_json_populates_structured_fields(self):
        policy = self.env['erpec.payroll.policy'].create(self._base_values(parameters=json.dumps(PARAMS)))
        self.assertEqual(policy.minimum_salary, PARAMS['minimum_salary'])
        self.assertEqual(policy.reserve_months, PARAMS['reserve_months'])
        self.assertEqual(len(policy.tax_bracket_ids), len(PARAMS['tax_brackets']))
        self.assertTrue(policy.tax_bracket_ids.sorted('sequence')[-1].open_ended)

    def test_editing_structured_field_updates_json_and_engine_still_works(self):
        policy = self.env['erpec.payroll.policy'].create(self._base_values(**self._structured_values()))
        policy.write({'minimum_salary': 600.0})
        params = json.loads(policy.parameters)
        self.assertEqual(params['minimum_salary'], 600.0)
        data = {'start_date': '2025-01-01', 'wage': 600, 'bonus': 0, 'commission': 0, 'non_taxable_income': 0,
                'advances': 0, 'loans': 0, 'other_deductions': 0, 'personal_expenses': 0, 'hours_50': 0,
                'hours_100': 0, 'night_hours': 0, 'monthly_thirteenth': False, 'monthly_fourteenth': False,
                'reserve_paid': False}
        result = calculate(data, params, 2097, 1)
        self.assertGreater(result['gross'], 0)

    def test_editing_tax_bracket_line_updates_json(self):
        policy = self.env['erpec.payroll.policy'].create(self._base_values(**self._structured_values()))
        first_bracket = policy.tax_bracket_ids.sorted('sequence')[0]
        first_bracket.write({'rate': 0.05})
        params = json.loads(policy.parameters)
        self.assertEqual(params['tax_brackets'][0]['rate'], 0.05)

    def test_active_policy_is_immutable_for_structured_fields(self):
        policy = self.env['erpec.payroll.policy'].create(self._base_values(**self._structured_values()))
        policy.action_activate()
        with self.assertRaises(ValidationError):
            policy.write({'minimum_salary': 999.0})
        with self.assertRaises(ValidationError):
            policy.tax_bracket_ids[0].write({'rate': 0.99})

    def test_incomplete_structured_fields_fail_activation_validation(self):
        policy = self.env['erpec.payroll.policy'].create(self._base_values(minimum_salary=480.0))
        with self.assertRaises(ValidationError):
            policy.action_activate()
