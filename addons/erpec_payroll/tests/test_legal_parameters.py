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

    def test_post_init_hook_seeds_national_policy_without_journal_or_chart_dependency(self):
        """El hook no referencia ningún diario a propósito (regresión real encontrada en
        pruebas: instalar erpec_payroll puede ocurrir antes de que el plan de cuentas termine
        de cargarse o se reemplace por dependencias posteriores del mismo lote de instalación;
        referenciar entonces un diario provisional rompía esa carga con una violación de llave
        foránea). Por eso siembra sin importar el estado del plan de cuentas, y journal_id queda
        vacío hasta que alguien lo asigna al activar."""
        from ..hooks import SEED_YEAR, post_init_hook
        from ..parameters_ec2026 import PARAMS as OFFICIAL_PARAMS
        post_init_hook(self.env)  # ya corrió al instalar el módulo; debe ser idempotente aquí también.
        seeded = self.env['erpec.payroll.policy'].search([
            ('company_id', '=', self.env.company.id), ('year', '=', SEED_YEAR)])
        self.assertEqual(len(seeded), 1, 'El hook debe sembrar una sola versión nacional por empresa/año.')
        self.assertEqual(seeded.minimum_salary, OFFICIAL_PARAMS['minimum_salary'])
        self.assertEqual(len(seeded.tax_bracket_ids), len(OFFICIAL_PARAMS['tax_brackets']))
        params = json.loads(seeded.parameters)
        validate_parameters(params)
        self.assertEqual(seeded.state, 'draft')
        self.assertFalse(seeded.journal_id, 'La siembra no debe inventar ni buscar un diario.')
        with self.assertRaises(ValidationError):
            seeded.action_activate()
        seeded.journal_id = self.journal
        seeded.action_activate()
        self.assertEqual(seeded.state, 'active')
        # No debe duplicar si se vuelve a llamar (idempotencia del hook).
        post_init_hook(self.env)
        self.assertEqual(self.env['erpec.payroll.policy'].search_count([
            ('company_id', '=', self.env.company.id), ('year', '=', SEED_YEAR)]), 1)

    def _simulate_legacy_policy_created_before_typed_fields(self):
        """Una actualización de módulo agrega columnas nuevas con su valor por defecto (cero)
        sin reescribir registros ya guardados -- así queda una versión creada antes de que
        existieran los campos tipados: parameters con datos reales, campos tipados en cero."""
        from ..models import _INTERNAL, STRUCTURED_PARAMETER_FIELDS
        policy = self.env['erpec.payroll.policy'].create(self._base_values(parameters=json.dumps(PARAMS)))
        # write() con el token interno: evita _sync_parameters_json() (que si corriera,
        # reconstruiría `parameters` desde estos ceros y arruinaría la simulación), pero sigue
        # siendo el camino normal del ORM -- a diferencia de SQL crudo, no se desincroniza de
        # la caché del recordset.
        policy.with_context(_erpec_payroll_token=_INTERNAL).write({key: 0 for key in STRUCTURED_PARAMETER_FIELDS})
        policy.tax_bracket_ids.with_context(_erpec_payroll_token=_INTERNAL).unlink()
        self.assertEqual(policy.minimum_salary, 0)
        self.assertFalse(policy.tax_bracket_ids)
        return policy

    def test_action_reload_from_json_fixes_legacy_zeroed_policy(self):
        policy = self._simulate_legacy_policy_created_before_typed_fields()
        policy.action_reload_from_json()
        self.assertEqual(policy.minimum_salary, PARAMS['minimum_salary'])
        self.assertEqual(len(policy.tax_bracket_ids), len(PARAMS['tax_brackets']))

    def test_action_reload_from_json_works_on_active_policy(self):
        """El bug real reportado por el titular ocurrió sobre una versión ya activa; el botón
        debe poder corregirla sin necesidad de desactivarla primero."""
        policy = self._simulate_legacy_policy_created_before_typed_fields()
        policy.action_activate()
        self.assertEqual(policy.state, 'active')
        policy.action_reload_from_json()
        self.assertEqual(policy.minimum_salary, PARAMS['minimum_salary'])
        self.assertEqual(len(policy.tax_bracket_ids), len(PARAMS['tax_brackets']))

    def test_migration_script_fixes_legacy_policies_automatically(self):
        import importlib.util
        from pathlib import Path
        policy = self._simulate_legacy_policy_created_before_typed_fields()
        spec = importlib.util.spec_from_file_location(
            'post_migrate_1_3_0',
            Path(__file__).resolve().parents[1] / 'migrations' / '18.0.1.3.0' / 'post-migrate.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '18.0.1.3.0')
        policy.invalidate_recordset()
        self.assertEqual(policy.minimum_salary, PARAMS['minimum_salary'])
        self.assertEqual(len(policy.tax_bracket_ids), len(PARAMS['tax_brackets']))
