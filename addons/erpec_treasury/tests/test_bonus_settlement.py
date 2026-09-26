"""Liquidación de décimos acumulados (DI26-C): período legal, régimen del décimo cuarto, asiento a nómina por pagar,
pago y reversión sin incluir dos veces la misma nómina."""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .test_treasury import TreasuryCase
from ..bonus_settlement import legal_window


@tagged('post_install', '-at_install')
class BonusSettlementCase(TreasuryCase):
    def settlement(self, kind, regime=False):
        return self.env['erpec.payroll.bonus.settlement'].with_user(self.manager).create(
            {'company_id': self.env.company.id, 'kind': kind, 'regime': regime, 'year': 2098})

    def test_legal_windows(self):
        self.assertEqual(legal_window('thirteenth', False, 2026), (date(2025, 12, 1), date(2026, 11, 30), date(2026, 12, 24)))
        self.assertEqual(legal_window('fourteenth', 'sierra_amazonia', 2026), (date(2025, 8, 1), date(2026, 7, 31), date(2026, 8, 15)))
        self.assertEqual(legal_window('fourteenth', 'costa_insular', 2028), (date(2027, 3, 1), date(2028, 2, 29), date(2028, 3, 15)))

    def test_thirteenth_settles_once_posts_payable_and_reverses(self):
        period = self.period()
        expected = {line.employee_id: line._result_value('thirteenth') for line in period.line_ids}
        self.assertTrue(all(expected.values()))
        settlement = self.settlement('thirteenth')
        self.assertEqual((settlement.date_from, settlement.date_to, settlement.deadline), (date(2097, 12, 1), date(2098, 11, 30), date(2098, 12, 24)))
        settlement.action_compute()
        self.assertEqual({line.employee_id: line.amount for line in settlement.line_ids}, {k: round(v, 2) for k, v in expected.items()})
        settlement.action_post()
        payable = settlement.move_id.line_ids.filtered(lambda l: l.account_type == 'liability_payable')
        self.assertAlmostEqual(sum(payable.mapped('credit')), settlement.total, places=2)
        self.assertEqual(set(payable.mapped('date_maturity')), {date(2098, 12, 24)})
        self.assertEqual(settlement.line_ids[0].residual, settlement.line_ids[0].amount)
        action = settlement.line_ids[0].action_pay()
        self.assertEqual(action['res_model'], 'account.payment.register')
        second = self.settlement('thirteenth')
        second.action_compute()
        self.assertFalse(second.line_ids, 'Una nómina ya liquidada no se vuelve a incluir.')
        with self.assertRaises(ValidationError):
            second.action_post()
        settlement.action_reverse()
        self.assertEqual(settlement.state, 'reversed')
        second.action_compute()
        self.assertEqual(len(second.line_ids), 2, 'Tras revertir, lo provisionado vuelve a estar disponible.')

    def test_fourteenth_requires_regime_and_filters_by_it(self):
        period = self.period()
        settlement = self.settlement('fourteenth', 'sierra_amazonia')
        with self.assertRaisesRegex(ValidationError, 'régimen del décimo cuarto'):
            settlement.action_compute()
        first, second = period.line_ids.mapped('employee_id')
        first.ec_fourteenth_regime = 'sierra_amazonia'
        second.ec_fourteenth_regime = 'costa_insular'
        settlement.action_compute()
        self.assertEqual(settlement.line_ids.employee_id, first)
        costa = self.settlement('fourteenth', 'costa_insular')
        self.assertEqual(costa.deadline, date(2098, 3, 15))
        costa.action_compute()
        self.assertEqual(costa.line_ids.employee_id, second)

    def test_posted_settlement_is_immutable(self):
        self.period()
        settlement = self.settlement('thirteenth')
        settlement.action_compute()
        settlement.action_post()
        with self.assertRaises(Exception):
            settlement.write({'year': 2099})
        with self.assertRaises(ValidationError):
            settlement.unlink()
