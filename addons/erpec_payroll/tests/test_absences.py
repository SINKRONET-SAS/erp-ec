"""Caso 8 (DI25-03): ausencias del trabajador. Reglas verificadas contra el Oficio PGE No. 10097
(17-02-2025, art. 54 Código del Trabajo y art. 16 Reglamento General sobre Prestación de
Subsidios en Dinero) y el art. 152 del Código del Trabajo (reforma 2023), aportadas y corregidas
por el titular del proyecto el 22-09-2026: enfermedad, días 1-3 al 100 % sin aporte a IESS, desde
el día 4 el empleador no paga nada (subsidio directo del IESS); maternidad, 25 % del empleador y
sí aporta a IESS; paternidad, 100 % del empleador y sí aporta a IESS (no cambia el cálculo);
permiso no pagado y falta injustificada, 0 % de pago, reducen IESS e impuesto a la renta."""
import json
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from ..demo_parameters import PARAMS


@tagged('post_install', '-at_install')
class AbsencesCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'name': 'DEMO nómina ausencias', 'vat': False})
        self.expense = self.env['account.account'].create({'code': 'PAYABSEXP', 'name': 'Nómina ausencias ensayo', 'account_type': 'expense'})
        self.liability = self.env['account.account'].create({'code': 'PAYABSLIAB', 'name': 'Obligaciones ausencias ensayo', 'account_type': 'liability_current'})
        self.journal = self.env['account.journal'].create({'name': 'Nómina ausencias ensayo', 'code': 'PYAB', 'type': 'general'})
        self.policy = self.env['erpec.payroll.policy'].create({
            'name': 'SINTETICA-AUSENCIAS', 'year': 2094, 'journal_id': self.journal.id,
            'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local del caso 8 (ausencias)',
            'source_reference': 'Parámetros ficticios para pruebas'})
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions',
                        'employer_iess', 'thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({
                'policy_id': self.policy.id, 'concept': concept,
                'debit_id': self.expense.id if concept not in ('net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions') else False,
                'credit_id': self.liability.id if concept != 'gross' else False})
        self.policy.action_activate()
        self.employee = self.env['hr.employee'].create({'name': 'Persona ausencias', 'company_id': self.company.id})
        self.partner = self.env['res.partner'].create({'name': 'Pago ausencias'})

    def _period(self, month, name=None, **novelties):
        return self.env['erpec.payroll.period'].create({
            'name': name or ('ENSAYO-AUSENCIAS-%s' % month), 'policy_id': self.policy.id, 'month': month,
            'line_ids': [(0, 0, dict({'employee_id': self.employee.id, 'partner_id': self.partner.id,
                                      'start_date': '2025-01-01', 'wage': 1200, 'approved': True}, **novelties))]})

    ELIGIBLE = {'sick_eligibility': 'eligible', 'sick_eligibility_ref': 'IESS-CAL-1', 'sick_certificate_ref': 'EXP-001',
                'sick_certificate_origin': 'iess', 'sick_prior_days': 0, 'sick_continuity_ref': 'Nuevo episodio',
                'sick_iess_rate': '75', 'sick_iess_base': 1200, 'sick_iess_ref': 'LIQ-1'}
    INELIGIBLE = {'sick_eligibility': 'ineligible', 'sick_eligibility_ref': 'IESS-CAL-2', 'sick_certificate_ref': 'EXP-002',
                  'sick_certificate_origin': 'iess', 'sick_prior_days': 0, 'sick_continuity_ref': 'Nuevo episodio',
                  'sick_annual_ref': 'Saldo anual 0'}

    def _gross(self, period):
        return json.loads(period.line_ids.result)['gross']

    def test_sick_leave_first_three_days_full_pay_no_iess(self):
        # Días 1-3: 100 % del sueldo, sin aporte a IESS (grava IR).
        plain = self._period(1)
        plain.action_calculate()
        sick = self._period(2, sick_days=3, **self.ELIGIBLE)
        sick.action_calculate()
        # El bruto no cambia (se pagó el 100 % igual), pero al no aportar IESS esos días se
        # retiene menos y el neto es mayor.
        self.assertLess(sick.line_ids.result_personal_iess, plain.line_ids.result_personal_iess)
        self.assertGreater(sick.line_ids.net, plain.line_ids.net)
        self.assertEqual(float(json.loads(sick.line_ids.result)['gross']), float(json.loads(plain.line_ids.result)['gross']))

    def test_sick_leave_from_fourth_day_employer_pays_nothing(self):
        # 10 días de enfermedad: 3 pagados al 100 %, 7 sin pago alguno (subsidio directo del IESS).
        plain = self._period(1)
        plain.action_calculate()
        sick = self._period(2, sick_days=10, **self.ELIGIBLE)
        sick.action_calculate()
        plain_gross = json.loads(plain.line_ids.result)['gross']
        sick_gross = json.loads(sick.line_ids.result)['gross']
        self.assertAlmostEqual(plain_gross - sick_gross, 1200 / 30 * 7, places=2)

    def test_sick_leave_without_evidence_is_pending_review_not_a_full_deduction(self):
        period = self._period(1, sick_days=5)
        with self.assertRaises(ValidationError) as caught:
            period.action_calculate()
        self.assertIn('calificación del derecho', str(caught.exception))
        incomplete = self._period(2, sick_days=5, **dict(self.ELIGIBLE, sick_eligibility_ref=False))
        with self.assertRaises(ValidationError):
            incomplete.action_calculate()

    def test_sick_leave_continuity_does_not_restart_the_three_days_each_month(self):
        plain = self._period(1)
        plain.action_calculate()
        later = self._period(2, sick_days=5, **dict(self.ELIGIBLE, sick_prior_days=3))
        later.action_calculate()
        self.assertAlmostEqual(self._gross(plain) - self._gross(later), 1200 / 30 * 5, places=2)
        partial = self._period(3, sick_days=4, **dict(self.ELIGIBLE, sick_prior_days=1))
        partial.action_calculate()
        self.assertAlmostEqual(self._gross(plain) - self._gross(partial), 1200 / 30 * 2, places=2)

    def test_sick_leave_without_iess_right_pays_half_and_counts_the_annual_limit(self):
        plain = self._period(1)
        plain.action_calculate()
        half = self._period(2, sick_days=4, **self.INELIGIBLE)
        half.action_calculate()
        self.assertAlmostEqual(self._gross(plain) - self._gross(half), 1200 / 30 * 4 * 0.5, places=2)
        self.assertEqual(json.loads(half.line_ids.result)['sick_days_employer50'], 4)
        limit = self._period(3, sick_days=3, sick_annual_days_outside=58, **self.INELIGIBLE)
        with self.assertRaises(ValidationError) as caught:
            limit.action_calculate()
        self.assertIn('límite anual', str(caught.exception))

    def test_annual_balance_accumulates_from_closed_periods(self):
        first = self._period(4, sick_days=10, **self.INELIGIBLE)
        first.action_calculate()
        first.action_close()
        second = self._period(5, sick_days=2, **self.INELIGIBLE)
        self.assertEqual(second.line_ids._inputs()['sick_annual_prior_days'], 10)

    def test_sick_leave_tranche_private_certificate_and_complement_need_support(self):
        private = self._period(1, sick_days=10, **dict(self.ELIGIBLE, sick_certificate_origin='private'))
        with self.assertRaises(ValidationError):
            private.action_calculate()
        no_tranche = self._period(2, sick_days=10, **dict(self.ELIGIBLE, sick_iess_rate=False))
        with self.assertRaises(ValidationError):
            no_tranche.action_calculate()
        complement = self._period(3, sick_days=10, **dict(self.ELIGIBLE, sick_complement_pct=50))
        with self.assertRaises(ValidationError):
            complement.action_calculate()

    def test_employer_complement_and_iess_estimate_are_separate(self):
        plain = self._period(1)
        plain.action_calculate()
        sick = self._period(2, sick_days=10, sick_complement_pct=50, sick_complement_ref='Contrato art. 5', **self.ELIGIBLE)
        sick.action_calculate()
        self.assertAlmostEqual(self._gross(plain) - self._gross(sick), 1200 / 30 * 7 * 0.5, places=2)
        # 7 días subsidiados x (1200 / 30) x 75 %: lo paga el IESS, no forma parte del neto.
        self.assertAlmostEqual(sick.line_ids.result_sick_iess, 1200 / 30 * 0.75 * 7, places=2)
        self.assertAlmostEqual(sick.line_ids.gross, self._gross(sick), places=2)

    def test_maternity_pays_25_percent_and_contributes_to_iess(self):
        full_month = self._period(1, maternity_days=30)
        full_month.action_calculate()
        result = json.loads(full_month.line_ids.result)
        self.assertAlmostEqual(result['gross'], 1200 * 0.25, places=2)
        self.assertAlmostEqual(result['personal_iess'], 1200 * 0.25 * PARAMS['personal_rate'], places=2)

    def test_paternity_does_not_change_the_calculation(self):
        plain = self._period(1)
        plain.action_calculate()
        paternity = self._period(2, paternity_days=15)
        paternity.action_calculate()
        self.assertEqual(json.loads(plain.line_ids.result), json.loads(paternity.line_ids.result))

    def test_unpaid_leave_and_unexcused_absence_reduce_iess_and_income_tax_base_equally(self):
        plain = self._period(1)
        plain.action_calculate()
        unpaid = self._period(2, unpaid_leave_days=5)
        unpaid.action_calculate()
        unexcused = self._period(3, unexcused_absence_days=5)
        unexcused.action_calculate()
        # Mismo efecto financiero; solo cambia el campo donde se registra, para el expediente laboral.
        self.assertEqual(unpaid.line_ids.net, unexcused.line_ids.net)
        self.assertLess(unpaid.line_ids.net, plain.line_ids.net)
        self.assertLess(unpaid.line_ids.result_personal_iess, plain.line_ids.result_personal_iess)

    def test_absence_days_cannot_exceed_the_period(self):
        period = self._period(1, unpaid_leave_days=31)
        with self.assertRaises(ValidationError):
            period.action_calculate()

    def test_absence_days_must_be_non_negative(self):
        period = self._period(1, sick_days=-1)
        with self.assertRaises(ValidationError):
            period.action_calculate()
