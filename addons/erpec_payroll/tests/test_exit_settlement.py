"""Pruebas de salida, rol proporcional y acta de finiquito (plan NM27)."""
import json
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..demo_parameters import PARAMS
from ..engine import calculate, days_worked
from ..settlement import days360, settle, vacation_entitlement_days


def base_data(**extra):
    data = {'cause': 'renuncia_voluntaria', 'modality': 'con_finiquito', 'start_date': date(2024, 3, 15), 'end_date': date(2099, 9, 17),
            'wage': 1200, 'fourteenth_regime': 'sierra_amazonia', 'vacation_days_taken': 0, 'other_deductions': 0,
            'thirteenth_paid': 0, 'fourteenth_paid': 0, 'reserve_paid': 0, 'reserve_covered': 0}
    data.update(extra)
    return data


@tagged('post_install', '-at_install')
class SettlementPureCase(TransactionCase):
    def test_days_worked_prorates_to_exit(self):
        self.assertEqual(days_worked(date(2025, 1, 1), 2099, 9, date(2099, 9, 15)), 15)
        self.assertEqual(days_worked(date(2025, 1, 1), 2099, 2, date(2099, 2, 28)), 30)
        self.assertEqual(days_worked(date(2025, 1, 1), 2099, 1, date(2099, 1, 31)), 30)
        self.assertEqual(days_worked(date(2025, 1, 1), 2099, 9, date(2099, 8, 31)), 0)
        self.assertEqual(days_worked(date(2099, 9, 10), 2099, 9, date(2099, 9, 20)), 11)
        self.assertEqual(days_worked(date(2025, 1, 1), 2099, 9), 30)

    def test_calculate_prorated_salary(self):
        result = calculate({'start_date': '2025-01-01', 'end_date': '2099-09-15', 'wage': 1200}, PARAMS, 2099, 9)
        self.assertEqual(result['days'], 15)
        self.assertEqual(result['salary'], 600)
        with self.assertRaises(ValueError):
            calculate({'start_date': '2025-01-01', 'end_date': '2024-12-31', 'wage': 1200}, PARAMS, 2099, 9)

    def test_days360(self):
        self.assertEqual(days360(date(2098, 12, 1), date(2099, 11, 30)), 360)
        self.assertEqual(days360(date(2099, 8, 1), date(2099, 9, 17)), 47)
        self.assertEqual(days360(date(2099, 3, 1), date(2099, 2, 28)), 0)

    def test_vacation_entitlement(self):
        self.assertAlmostEqual(float(vacation_entitlement_days(365)), 15, places=6)
        self.assertAlmostEqual(float(vacation_entitlement_days(365*6)), 15*6+1, places=6)

    def test_modalities_do_not_double_pay(self):
        with_settlement = settle(base_data(), PARAMS)
        roll_first = settle(base_data(modality='rol_primero'), PARAMS)
        self.assertEqual(with_settlement['pending_salary'], 680)
        self.assertEqual(roll_first['pending_salary'], 0)
        self.assertEqual(with_settlement['personal_iess'], round(680*PARAMS['personal_rate'], 2))
        self.assertEqual(roll_first['personal_iess'], 0)
        self.assertEqual(with_settlement['thirteenth'], roll_first['thirteenth'])

    def test_benefits_already_paid_are_discounted(self):
        full = settle(base_data(), PARAMS)
        reduced = settle(base_data(thirteenth_paid=100, fourteenth_paid=10, reserve_paid=50), PARAMS)
        self.assertEqual(round(full['thirteenth']-reduced['thirteenth'], 2), 100)
        self.assertEqual(round(full['fourteenth']-reduced['fourteenth'], 2), 10)
        self.assertEqual(round(full['reserve']-reduced['reserve'], 2), 50)
        floor = settle(base_data(thirteenth_paid=99999), PARAMS)
        self.assertEqual(floor['thirteenth'], 0)

    def test_vacations_discount_enjoyed_days(self):
        none = settle(base_data(), PARAMS)
        taken = settle(base_data(vacation_days_taken=10), PARAMS)
        self.assertEqual(round(none['vacation']-taken['vacation'], 2), 400)
        self.assertEqual(settle(base_data(vacation_days_taken=9999), PARAMS)['vacation'], 0)

    def test_dismissal_and_desahucio(self):
        short = settle(base_data(cause='despido_intempestivo', start_date=date(2098, 1, 1)), PARAMS)
        self.assertEqual(short['dismissal'], 3600)
        long = settle(base_data(cause='despido_intempestivo', start_date=date(2090, 1, 1)), PARAMS)
        self.assertEqual(long['dismissal'], 1200*10)
        self.assertEqual(long['desahucio'], 1200*0.25*9)
        self.assertEqual(settle(base_data(cause='conclusion_obra'), PARAMS)['desahucio'], 0)

    def test_probation_and_invalid_inputs(self):
        with self.assertRaises(ValueError):
            settle(base_data(cause='prueba_empleador'), PARAMS)
        ok = settle(base_data(cause='prueba_empleador', start_date=date(2099, 8, 1)), PARAMS)
        self.assertEqual(ok['dismissal'], 0)
        with self.assertRaises(ValueError):
            settle(base_data(end_date=date(2020, 1, 1)), PARAMS)
        with self.assertRaises(ValueError):
            settle(base_data(cause='visto_bueno_empleador'), PARAMS)
        with self.assertRaises(ValueError):
            settle(base_data(other_deductions=10**7), PARAMS)
        with self.assertRaises(ValueError):
            settle(base_data(fourteenth_regime=False), PARAMS)


@tagged('post_install', '-at_install')
class ExitFlowCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'name': 'DEMO nómina sintética', 'vat': False})
        expense = self.env['account.account'].create({'code': 'EXTESTEXP', 'name': 'Nómina ensayo', 'account_type': 'expense'})
        liability = self.env['account.account'].create({'code': 'EXTESTLIAB', 'name': 'Obligaciones ensayo', 'account_type': 'liability_current'})
        journal = self.env['account.journal'].create({'name': 'Nómina ensayo', 'code': 'EXT', 'type': 'general'})
        self.policy = self.env['erpec.payroll.policy'].create({'name': 'SINTETICA-EX', 'year': 2099, 'journal_id': journal.id, 'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local', 'source_reference': 'Parámetros ficticios'})
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions', 'employer_iess', 'thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({'policy_id': self.policy.id, 'concept': concept, 'debit_id': expense.id if concept not in ('net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions') else False, 'credit_id': liability.id if concept != 'gross' else False})
        self.policy.action_activate()
        self.employee = self.env['hr.employee'].create({'name': 'Persona ficticia', 'company_id': self.company.id, 'ec_fourteenth_regime': 'sierra_amazonia'})
        self.partner = self.env['res.partner'].create({'name': 'Pago ficticio'})

    def make_exit(self, modality, **extra):
        values = {'policy_id': self.policy.id, 'employee_id': self.employee.id, 'start_date': '2025-01-01', 'end_date': '2099-09-17', 'wage': 1200,
                  'cause': 'renuncia_voluntaria', 'modality': modality}
        values.update(extra)
        return self.env['erpec.payroll.exit'].create(values)

    def make_period(self, month, **line_extra):
        line = {'employee_id': self.employee.id, 'partner_id': self.partner.id, 'start_date': '2025-01-01', 'wage': 1200, 'approved': True}
        line.update(line_extra)
        return self.env['erpec.payroll.period'].create({'name': 'EX-%s' % month, 'policy_id': self.policy.id, 'month': month, 'line_ids': [(0, 0, line)]})

    def test_roll_first_flow(self):
        exit_ = self.make_exit('rol_primero')
        exit_.action_calculate()
        self.assertEqual(exit_.state, 'calculated')
        self.assertEqual(exit_.amount_pending_salary, 0)
        with self.assertRaises(ValidationError):
            exit_.action_approve()
        with self.assertRaises(ValidationError):
            self.make_period(9)
        period = self.make_period(9, end_date='2099-09-17')
        period.action_calculate()
        self.assertEqual(period.line_ids.result_salary, 680)
        with self.assertRaises(ValidationError):
            exit_.action_approve()
        period.action_close()
        with self.assertRaises(ValidationError):
            exit_.action_approve()  # el rol cerrado cambia lo ya cubierto: exige recalcular
        exit_.action_calculate()
        exit_.action_approve()
        self.assertEqual(exit_.state, 'approved')
        self.assertTrue(exit_.name.startswith('FIN-'))
        with self.assertRaises(ValidationError):
            self.make_period(10)
        with self.assertRaises(ValidationError):
            exit_.write({'wage': 1})
        with self.assertRaises(ValidationError):
            exit_.action_mark_paid()
        exit_.write({'paid_date': '2099-09-30', 'payment_reference': 'REF-1'})
        exit_.action_mark_paid()
        self.assertEqual(exit_.state, 'paid')
        with self.assertRaises(ValidationError):
            exit_.action_cancel()

    def test_with_settlement_blocks_exit_month_roll(self):
        exit_ = self.make_exit('con_finiquito')
        exit_.action_calculate()
        self.assertEqual(exit_.amount_pending_salary, 680)
        with self.assertRaises(ValidationError):
            self.make_period(9)
        self.make_period(8)
        exit_.action_approve()
        self.assertEqual(exit_.state, 'approved')

    def test_existing_roll_contradicting_modality_blocks_calculation(self):
        self.make_period(9)
        with self.assertRaises(ValidationError):
            self.make_exit('con_finiquito').action_calculate()
        exit_ = self.make_exit('rol_primero')
        with self.assertRaises(ValidationError):
            exit_.action_calculate()

    def test_monthly_paid_benefits_are_discounted(self):
        period = self.make_period(8, monthly_thirteenth=True)
        period.action_calculate()
        paid = json.loads(period.line_ids.result)['thirteenth_paid']
        self.assertGreater(paid, 0)
        period.action_close()
        exit_ = self.make_exit('con_finiquito')
        exit_.action_calculate()
        reference = settle(base_data(end_date=date(2099, 9, 17), start_date=date(2025, 1, 1)), PARAMS)
        self.assertAlmostEqual(reference['thirteenth']-exit_.amount_thirteenth, paid, places=2)

    def test_recalculation_required_after_change_and_cancel_reopens(self):
        exit_ = self.make_exit('con_finiquito')
        exit_.action_calculate()
        exit_.write({'other_deductions': 50})
        self.assertEqual(exit_.state, 'draft')
        exit_.action_calculate()
        self.assertEqual(exit_.amount_other_deductions, 50)
        with self.assertRaises(ValidationError):
            self.make_exit('con_finiquito')
        exit_.action_cancel()
        self.assertEqual(self.make_exit('con_finiquito').state, 'draft')

    def test_report_renders(self):
        exit_ = self.make_exit('con_finiquito')
        exit_.action_calculate()
        html = self.env['ir.actions.report']._render_qweb_html('erpec_payroll.report_exit_settlement', exit_.ids)[0]
        self.assertIn(b'Acta de finiquito', html)
        self.assertIn(b'680.00', html)

    def test_line_end_date_validation(self):
        with self.assertRaises(ValidationError):
            self.make_period(9, end_date='2099-10-01')
        with self.assertRaises(ValidationError):
            self.make_period(9, end_date='2024-12-31')
