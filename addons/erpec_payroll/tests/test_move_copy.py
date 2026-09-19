"""Regresión: con erpec_payroll instalado, copiar o revertir un asiento ordinario (duplicar factura, nota de crédito o de
débito) no debe bloquearse; solo se protege el vínculo real con la nómina."""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class PayrollMoveCopyCase(TransactionCase):
    def _invoice(self):
        partner = self.env['res.partner'].create({'name': 'Cliente copia'})
        move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id, 'invoice_date': '2026-09-18', 'date': '2026-09-18',
            'invoice_line_ids': [(0, 0, {'name': 'Servicio', 'quantity': 1, 'price_unit': 10})]})
        move.action_post()
        return move

    def test_reversal_and_copy_of_an_ordinary_invoice_still_work(self):
        invoice = self._invoice()
        credit = invoice._reverse_moves([{'ref': 'Devolución'}], cancel=False)
        self.assertEqual(credit.move_type, 'out_refund')
        self.assertFalse(credit.erpec_payroll_id)
        duplicate = invoice.copy()
        self.assertFalse(duplicate.erpec_payroll_id)
        self.assertFalse(duplicate.erpec_payroll_opening_balance_id)

    def test_direct_payroll_link_is_still_protected(self):
        with self.assertRaisesRegex(ValidationError, 'cierre de nómina'):
            self.env['account.move'].create({'move_type': 'entry', 'erpec_payroll_id': 1})
        with self.assertRaisesRegex(ValidationError, 'cierre de nómina'):
            self.env['account.move'].create({'move_type': 'entry', 'erpec_payroll_opening_balance_id': 1})
