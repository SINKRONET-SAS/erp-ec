"""Pruebas de beneficios propios configurables por empresa y del libro de anticipos/préstamos
con cuota fija -- nueva pasada pedida por el titular: los parámetros legales (nacionales,
uniformes) no permiten que cada cliente configure sus propios beneficios ni el descuento de
anticipos con cuota, así que se agregan como una capa aparte, sin tocar engine.py."""
import json

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from psycopg2 import IntegrityError

from ..demo_parameters import PARAMS


@tagged('post_install', '-at_install')
class BenefitsAdvancesCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'name': 'DEMO nómina beneficios', 'vat': False})
        self.expense = self.env['account.account'].create({'code': 'PAYBNEXP', 'name': 'Nómina beneficios ensayo', 'account_type': 'expense'})
        self.liability = self.env['account.account'].create({'code': 'PAYBNLIAB', 'name': 'Obligaciones beneficios ensayo', 'account_type': 'liability_current'})
        self.journal = self.env['account.journal'].create({'name': 'Nómina beneficios ensayo', 'code': 'PYBN', 'type': 'general'})
        self.policy = self.env['erpec.payroll.policy'].create({
            'name': 'SINTETICA-BENEFICIOS', 'year': 2093, 'journal_id': self.journal.id,
            'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local de beneficios propios',
            'source_reference': 'Parámetros ficticios para pruebas'})
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions',
                        'employer_iess', 'thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({
                'policy_id': self.policy.id, 'concept': concept,
                'debit_id': self.expense.id if concept not in ('net', 'personal_iess', 'tax', 'advances', 'loans', 'other_deductions') else False,
                'credit_id': self.liability.id if concept != 'gross' else False})
        self.policy.action_activate()
        self.employee = self.env['hr.employee'].create({'name': 'Persona beneficios', 'company_id': self.company.id})
        self.partner = self.env['res.partner'].create({'name': 'Pago beneficios'})

    def _make_period(self, month, name=None):
        return self.env['erpec.payroll.period'].create({
            'name': name or ('ENSAYO-BENEFICIOS-%s' % month), 'policy_id': self.policy.id, 'month': month,
            'line_ids': [(0, 0, {'employee_id': self.employee.id, 'partner_id': self.partner.id,
                                  'start_date': '2025-01-01', 'wage': 1200, 'approved': True})]})

    # -- Beneficios propios ------------------------------------------------

    def test_taxable_benefit_equals_manual_bonus(self):
        period_with_benefit = self._make_period(1)
        benefit_type = self.env['erpec.payroll.benefit.type'].create(
            {'name': 'Bono de responsabilidad', 'taxable': True})
        self.env['erpec.payroll.benefit.line'].create(
            {'line_id': period_with_benefit.line_ids.id, 'benefit_type_id': benefit_type.id, 'amount': 100})
        period_with_benefit.action_calculate()
        period_manual = self._make_period(2)
        period_manual.line_ids.bonus = 100
        period_manual.action_calculate()
        self.assertEqual(period_with_benefit.line_ids.net, period_manual.line_ids.net)
        self.assertEqual(period_with_benefit.line_ids.cost, period_manual.line_ids.cost)
        self.assertEqual(period_with_benefit.line_ids.result_personal_iess, period_manual.line_ids.result_personal_iess)

    def test_non_taxable_benefit_equals_manual_non_taxable_income(self):
        period_with_benefit = self._make_period(1)
        benefit_type = self.env['erpec.payroll.benefit.type'].create(
            {'name': 'Subsidio de alimentación', 'taxable': False})
        self.env['erpec.payroll.benefit.line'].create(
            {'line_id': period_with_benefit.line_ids.id, 'benefit_type_id': benefit_type.id, 'amount': 60})
        period_with_benefit.action_calculate()
        period_manual = self._make_period(2)
        period_manual.line_ids.non_taxable_income = 60
        period_manual.action_calculate()
        self.assertEqual(period_with_benefit.line_ids.net, period_manual.line_ids.net)
        self.assertEqual(period_with_benefit.line_ids.result_personal_iess, period_manual.line_ids.result_personal_iess)

    def test_benefit_amount_must_be_positive(self):
        period = self._make_period(1)
        benefit_type = self.env['erpec.payroll.benefit.type'].create({'name': 'Beneficio inválido', 'taxable': True})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.payroll.benefit.line'].create(
                {'line_id': period.line_ids.id, 'benefit_type_id': benefit_type.id, 'amount': 0})

    def test_benefit_line_locked_once_calculated(self):
        period = self._make_period(1)
        benefit_type = self.env['erpec.payroll.benefit.type'].create({'name': 'Bono bloqueo', 'taxable': True})
        benefit_line = self.env['erpec.payroll.benefit.line'].create(
            {'line_id': period.line_ids.id, 'benefit_type_id': benefit_type.id, 'amount': 50})
        period.action_calculate()
        with self.assertRaises(ValidationError):
            benefit_line.amount = 80
        period.action_reopen()
        benefit_line.amount = 80
        self.assertEqual(benefit_line.amount, 80)

    def test_benefit_type_name_unique_per_company(self):
        self.env['erpec.payroll.benefit.type'].create({'name': 'Bono único', 'taxable': True})
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['erpec.payroll.benefit.type'].create({'name': 'Bono único', 'taxable': False})

    # -- Anticipos y préstamos ----------------------------------------------

    def _make_advance(self, advance_type='anticipo', amount_total=250, installment_amount=100, start_month=1):
        advance = self.env['erpec.payroll.advance'].create({
            'employee_id': self.employee.id, 'advance_type': advance_type, 'amount_total': amount_total,
            'installment_amount': installment_amount, 'start_year': 2093, 'start_month': start_month,
            'reason': 'Ensayo real de anticipo'})
        advance.action_approve()
        return advance

    def test_advance_requires_reason_to_approve(self):
        advance = self.env['erpec.payroll.advance'].create({
            'employee_id': self.employee.id, 'amount_total': 100, 'installment_amount': 50,
            'start_year': 2093, 'start_month': 1, 'reason': '   '})
        with self.assertRaises(ValidationError):
            advance.action_approve()

    def test_installment_must_be_positive_and_not_exceed_total(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.payroll.advance'].create({
                'employee_id': self.employee.id, 'amount_total': 100, 'installment_amount': 150,
                'start_year': 2093, 'start_month': 1, 'reason': 'Cuota mayor al total'})

    def test_single_period_deduction_matches_manual_advance(self):
        advance = self._make_advance()
        period_with_ledger = self._make_period(1)
        period_with_ledger.action_calculate()
        # Comparación con un empleado SIN anticipo: si se reutilizara el mismo empleado, el
        # anticipo también aplicaría legítimamente a su segundo período (ver
        # test_multi_period_drawdown_until_settled), invalidando la comparación.
        other_employee = self.env['hr.employee'].create({'name': 'Persona sin anticipo', 'company_id': self.company.id})
        period_manual = self.env['erpec.payroll.period'].create({
            'name': 'ENSAYO-BENEFICIOS-MANUAL', 'policy_id': self.policy.id, 'month': 2,
            'line_ids': [(0, 0, {'employee_id': other_employee.id, 'partner_id': self.partner.id,
                                  'start_date': '2025-01-01', 'wage': 1200, 'approved': True, 'advances': 100})]})
        period_manual.action_calculate()
        self.assertEqual(period_with_ledger.line_ids.result_advances, 100)
        self.assertEqual(period_with_ledger.line_ids.net, period_manual.line_ids.net)
        self.assertEqual(advance.balance, 150)
        self.assertEqual(len(advance.deduction_ids), 1)

    def test_loan_deducted_as_loans_not_advances(self):
        self._make_advance(advance_type='prestamo')
        period = self._make_period(1)
        period.action_calculate()
        self.assertEqual(period.line_ids.result_loans, 100)
        self.assertEqual(period.line_ids.result_advances, 0)

    def test_multi_period_drawdown_until_settled(self):
        advance = self._make_advance(amount_total=250, installment_amount=100)
        first = self._make_period(1); first.action_calculate()
        self.assertEqual(advance.balance, 150)
        self.assertFalse(advance.settled)
        second = self._make_period(2); second.action_calculate()
        self.assertEqual(advance.balance, 50)
        third = self._make_period(3); third.action_calculate()
        self.assertEqual(third.line_ids.result_advances, 50)
        self.assertEqual(advance.balance, 0)
        self.assertTrue(advance.settled)
        fourth = self._make_period(4); fourth.action_calculate()
        self.assertEqual(fourth.line_ids.result_advances, 0)
        self.assertFalse(fourth.line_ids.advance_deduction_ids)

    def test_recalculating_same_period_does_not_double_deduct(self):
        advance = self._make_advance()
        period = self._make_period(1)
        period.action_calculate()
        period.action_reopen()
        period.action_calculate()
        self.assertEqual(len(advance.deduction_ids), 1)
        self.assertEqual(advance.balance, 150)

    def test_advance_does_not_apply_before_start_period(self):
        self._make_advance(start_month=6)
        period = self._make_period(1)
        period.action_calculate()
        self.assertEqual(period.line_ids.result_advances, 0)
        self.assertFalse(period.line_ids.advance_deduction_ids)

    def test_approved_advance_is_immutable_and_protected(self):
        advance = self._make_advance()
        with self.assertRaises(ValidationError):
            advance.amount_total = 999
        with self.assertRaises(ValidationError):
            advance.unlink()
        period = self._make_period(1)
        period.action_calculate()
        deduction = advance.deduction_ids
        with self.assertRaises(ValidationError):
            deduction.amount = 1
        with self.assertRaises(ValidationError):
            deduction.unlink()
        with self.assertRaises(ValidationError):
            self.env['erpec.payroll.advance.deduction'].create(
                {'advance_id': advance.id, 'line_id': period.line_ids.id, 'amount': 1})

    def test_cancel_blocked_once_deductions_exist(self):
        advance = self._make_advance()
        period = self._make_period(1)
        period.action_calculate()
        with self.assertRaises(ValidationError):
            advance.action_cancel()

    def test_draft_advance_can_be_cancelled(self):
        advance = self.env['erpec.payroll.advance'].create({
            'employee_id': self.employee.id, 'amount_total': 100, 'installment_amount': 50,
            'start_year': 2093, 'start_month': 1, 'reason': 'Ensayo de cancelación'})
        advance.action_cancel()
        self.assertEqual(advance.state, 'cancelled')

    def test_di25_correction_preserves_benefits(self):
        period = self._make_period(1)
        benefit = self.env['erpec.payroll.benefit.type'].create({'name': 'DI25 bono', 'taxable': True})
        period.line_ids.benefit_line_ids = [(0, 0, {'benefit_type_id': benefit.id, 'amount': 125, 'note': 'Conservar soporte'})]
        period.action_calculate()
        original = json.loads(period.line_ids.result)
        period.action_close()
        period.action_post()
        period.action_reverse()
        correction = self.env['erpec.payroll.period'].browse(period.action_correct()['res_id'])
        self.assertEqual(correction.line_ids.benefit_line_ids.amount, 125)
        self.assertEqual(correction.line_ids.benefit_line_ids.note, 'Conservar soporte')
        self.assertEqual(period.action_correct()['res_id'], correction.id)
        correction.action_calculate()
        self.assertEqual(json.loads(correction.line_ids.result), original)

    def test_di25_reversal_restores_loan_without_deleting_history(self):
        advance = self._make_advance(advance_type='prestamo')
        period = self._make_period(1)
        period.action_calculate()
        period.action_close()
        period.action_post()
        self.assertEqual(advance.balance, 150)
        old_deduction = period.line_ids.advance_deduction_ids
        period.action_reverse()
        period.action_reverse()
        self.assertEqual(advance.balance, 250)
        self.assertTrue(old_deduction.exists())
        correction = self.env['erpec.payroll.period'].browse(period.action_correct()['res_id'])
        correction.action_calculate()
        correction.action_calculate()
        self.assertEqual(correction.line_ids.result_loans, 100)
        self.assertEqual(advance.balance, 150)
        self.assertEqual(len(advance.deduction_ids), 2)

    def test_di25_balance_migration_preview_apply_restore(self):
        from ..balance_migration import preview, apply
        advance = self._make_advance(advance_type='prestamo')
        period = self._make_period(1)
        period.action_calculate()
        period.action_close()
        period.action_post()
        period.action_reverse()
        self.env.flush_all()
        # Simula únicamente la columna derivada heredada; el historial permanece intacto.
        self.env.cr.execute('UPDATE erpec_payroll_advance SET balance=150, settled=false WHERE id=%s', [advance.id])
        advance.invalidate_recordset(['balance', 'settled'])
        snapshot = preview(self.env)
        row = next(row for row in snapshot['rows'] if row['id'] == advance.id)
        self.assertEqual(row['before_balance'], 150)
        self.assertEqual(row['after_balance'], 250)
        self.assertEqual(advance.balance, 150)
        apply(self.env, snapshot)
        self.assertEqual(advance.balance, 250)
        apply(self.env, snapshot, restore=True)
        self.assertEqual(advance.balance, 150)
        apply(self.env, snapshot)
        correction = self.env['erpec.payroll.period'].browse(period.action_correct()['res_id'])
        correction.action_calculate()
        with self.assertRaisesRegex(ValidationError, 'cambiaron'):
            apply(self.env, snapshot, restore=True)
