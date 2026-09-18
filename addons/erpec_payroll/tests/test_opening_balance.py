"""Pruebas de la carga de saldos iniciales (A4): dry-run -> commit -> revert, idempotente por
huella del origen, para altas de empresa/empleado a mitad de año (décimos/vacaciones/fondo de
reserva ya devengados en otro sistema, préstamos/anticipos pendientes)."""
import json

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..demo_parameters import PARAMS


@tagged('post_install', '-at_install')
class OpeningBalanceCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'name': 'DEMO nómina saldos', 'vat': False})
        self.expense = self.env['account.account'].create({'code': 'PAOBEXP', 'name': 'Nómina saldos ensayo', 'account_type': 'expense'})
        self.liability = self.env['account.account'].create({'code': 'PAOBLIAB', 'name': 'Obligaciones saldos ensayo', 'account_type': 'liability_current'})
        self.receivable = self.env['account.account'].create({'code': 'PAOBREC', 'name': 'Préstamos y anticipos ensayo', 'account_type': 'asset_current'})
        self.suspense = self.env['account.account'].create({'code': 'PAOBSUS', 'name': 'Contrapartida saldos iniciales ensayo', 'account_type': 'equity'})
        self.journal = self.env['account.journal'].create({'name': 'Nómina saldos ensayo', 'code': 'PYOB', 'type': 'general'})
        self.policy = self.env['erpec.payroll.policy'].create({
            'name': 'SINTETICA-SALDOS', 'year': 2096, 'journal_id': self.journal.id,
            'opening_balance_account_id': self.suspense.id,
            'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local de saldos iniciales',
            'source_reference': 'Parámetros ficticios para pruebas'})
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'other_deductions', 'employer_iess'):
            self.env['erpec.payroll.mapping'].create({
                'policy_id': self.policy.id, 'concept': concept,
                'debit_id': self.expense.id if concept in ('gross', 'employer_iess') else False,
                'credit_id': self.liability.id if concept != 'gross' else False})
        for concept in ('advances', 'loans'):
            self.env['erpec.payroll.mapping'].create({'policy_id': self.policy.id, 'concept': concept, 'credit_id': self.receivable.id})
        for concept in ('thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({'policy_id': self.policy.id, 'concept': concept, 'debit_id': self.expense.id, 'credit_id': self.liability.id})
        self.policy.action_activate()
        self.employee = self.env['hr.employee'].create({'name': 'Saldo inicial', 'company_id': self.company.id})
        self.partner = self.env['res.partner'].create({'name': 'Pago saldo inicial'})

    def _create_policy(self, name, year, opening_balance_account=True):
        values = {
            'name': name, 'year': year, 'journal_id': self.journal.id,
            'parameters': json.dumps(PARAMS), 'authorization': 'Ensayo local de saldos iniciales',
            'source_reference': 'Parámetros ficticios para pruebas'}
        if opening_balance_account:
            values['opening_balance_account_id'] = self.suspense.id
        policy = self.env['erpec.payroll.policy'].create(values)
        for concept in ('gross', 'net', 'personal_iess', 'tax', 'other_deductions', 'employer_iess'):
            self.env['erpec.payroll.mapping'].create({
                'policy_id': policy.id, 'concept': concept,
                'debit_id': self.expense.id if concept in ('gross', 'employer_iess') else False,
                'credit_id': self.liability.id if concept != 'gross' else False})
        for concept in ('advances', 'loans'):
            self.env['erpec.payroll.mapping'].create({'policy_id': policy.id, 'concept': concept, 'credit_id': self.receivable.id})
        for concept in ('thirteenth', 'fourteenth', 'vacation', 'reserve_iess'):
            self.env['erpec.payroll.mapping'].create({'policy_id': policy.id, 'concept': concept, 'debit_id': self.expense.id, 'credit_id': self.liability.id})
        policy.action_activate()
        return policy

    def _create_balance(self, **overrides):
        values = {
            'policy_id': self.policy.id, 'employee_id': self.employee.id, 'partner_id': self.partner.id,
            'as_of_date': '2026-01-01', 'thirteenth_accrued': 100.0, 'fourteenth_accrued': 50.0,
            'vacation_accrued': 75.0, 'reserve_accrued': 40.0, 'loan_balance': 200.0, 'advance_balance': 30.0,
            'source_reference': 'Exportación del sistema anterior, corte 31-12-2025',
        }
        values.update(overrides)
        return self.env['erpec.payroll.opening.balance'].create(values)

    def test_dry_run_computes_preview_without_posting_a_move(self):
        balance = self._create_balance()
        balance.action_dry_run()
        self.assertEqual(balance.state, 'dry_run')
        self.assertTrue(balance.preview_summary)
        self.assertFalse(balance.move_id)
        self.assertTrue(balance.source_hash)

    def test_commit_requires_dry_run_first(self):
        balance = self._create_balance()
        with self.assertRaises(ValidationError):
            balance.action_commit()

    def test_commit_posts_balanced_move_and_locks_the_record(self):
        balance = self._create_balance()
        balance.action_dry_run()
        balance.action_commit()
        self.assertEqual(balance.state, 'committed')
        move = balance.move_id
        self.assertEqual(move.state, 'posted')
        self.assertAlmostEqual(sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit')), places=2)
        with self.assertRaises(ValidationError):
            balance.write({'loan_balance': 999.0})

    def test_commit_is_idempotent_by_source_hash_across_policy_versions(self):
        # Escenario real: el mismo origen (mismo empleado, mismos valores, misma fecha de corte
        # y referencia) se intenta cargar dos veces bajo dos versiones de política distintas --
        # p. ej. un script de importación que se ejecuta dos veces por error, o una corrección de
        # versión que reutiliza el mismo lote sin darse cuenta. La restricción SQL
        # unique(policy_id,employee_id) NO detecta esto (son políticas distintas); la huella del
        # origen sí.
        balance = self._create_balance()
        balance.action_dry_run()
        balance.action_commit()
        other_policy = self._create_policy('SINTETICA-SALDOS-V2', 2095)
        duplicate = self._create_balance(policy_id=other_policy.id)
        duplicate.action_dry_run()
        with self.assertRaises(ValidationError):
            duplicate.action_commit()

    def test_revert_creates_reversal_and_allows_recommit(self):
        balance = self._create_balance()
        balance.action_dry_run()
        balance.action_commit()
        balance.action_revert()
        self.assertEqual(balance.state, 'reverted')
        self.assertTrue(balance.reversal_id)
        self.assertEqual(balance.reversal_id.state, 'posted')
        balance.action_dry_run()
        balance.action_commit()
        self.assertEqual(balance.state, 'committed')

    def test_revert_requires_committed_state(self):
        balance = self._create_balance()
        with self.assertRaises(ValidationError):
            balance.action_revert()

    def test_dry_run_fails_without_opening_balance_account(self):
        bare_policy = self._create_policy('SINTETICA-SALDOS-SIN-CUENTA', 2094, opening_balance_account=False)
        balance = self._create_balance(policy_id=bare_policy.id)
        with self.assertRaises(ValidationError):
            balance.action_dry_run()

    def test_zero_amounts_are_rejected(self):
        balance = self._create_balance(thirteenth_accrued=0, fourteenth_accrued=0, vacation_accrued=0, reserve_accrued=0, loan_balance=0, advance_balance=0)
        with self.assertRaises(ValidationError):
            balance.action_dry_run()
