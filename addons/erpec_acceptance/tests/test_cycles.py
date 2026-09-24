"""DI25-07.1: ciclo de compras completo que cruza módulos: recepción parcial -> factura -> retención -> pago ->
devolución. erpec_workspace prueba recepción/factura/pago/devolución y erpec_withholding_accounting la retención
por separado; aquí se encadenan sobre la misma factura para comprobar que el saldo, la conciliación y la nota de
crédito siguen siendo coherentes cuando la retención se interpone entre factura y pago."""
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class PurchaseCycleCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, no_reset_password=True))
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.buyer = new_test_user(self.env, login='acc_buyer', groups='purchase.group_purchase_user')
        self.stock = new_test_user(self.env, login='acc_stock', groups='stock.group_stock_user')
        self.accountant = new_test_user(self.env, login='acc_accountant', groups='account.group_account_manager,account.group_account_user')
        self.supplier = self.env['res.partner'].create({'name': 'Proveedor aceptación — ensayo'})
        self.expense = self.env['account.account'].create({'name': 'Compras de aceptación', 'code': 'ACCEXP', 'account_type': 'expense'})
        self.liability = self.env['account.account'].create({'name': 'Retenciones de aceptación por pagar', 'code': 'ACCRET', 'account_type': 'liability_current'})
        self.general = self.env['account.journal'].search([('company_id', '=', self.env.company.id), ('type', '=', 'general')], limit=1)
        self.products = self.env['product.product'].create([
            {'name': 'Mercadería aceptación ' + name, 'type': 'consu', 'is_storable': True, 'purchase_method': 'receive',
             'property_account_expense_id': self.expense.id, 'supplier_taxes_id': [(5, 0, 0)]} for name in ('A', 'B')])
        self.order = self.env['purchase.order'].with_user(self.buyer).create({
            'partner_id': self.supplier.id,
            'order_line': [(0, 0, {'product_id': p.id, 'product_qty': 5, 'price_unit': 10, 'taxes_id': [(5, 0, 0)]}) for p in self.products]})

    def receive(self, picking, quantity):
        picking = picking.with_user(self.stock)
        for move in picking.move_ids:
            move.quantity = quantity
            move.picked = True
        picking.with_context(skip_backorder=True).button_validate()
        self.assertEqual(picking.state, 'done')

    def bill(self, number):
        order = self.order.with_user(self.accountant)
        before = order.invoice_ids
        order.action_create_invoice()
        bill = order.invoice_ids - before
        bill.write({'invoice_date': fields.Date.today(), 'l10n_latam_document_number': '001-001-' + str(number).zfill(9)})
        bill.action_post()
        self.assertEqual(bill.state, 'posted')
        return bill

    def pay(self, bill, amount):
        pending = self.env['account.account'].create({'name': 'Pagos pendientes aceptación %s' % amount, 'code': 'ACCP%d' % int(amount * 100),
                                                      'account_type': 'asset_current', 'reconcile': True})
        bank = self.env['account.journal'].create({'name': 'Banco aceptación %s' % amount, 'code': 'AC%d' % int(amount * 100 % 1000), 'type': 'bank'})
        bank.outbound_payment_method_line_ids.payment_account_id = pending
        wizard = self.env['account.payment.register'].with_user(self.accountant).with_context(
            active_model='account.move', active_ids=bill.ids).create({'journal_id': bank.id, 'amount': amount, 'payment_difference_handling': 'open'})
        return wizard._create_payments()

    def test_purchase_cycle_with_withholding_between_bill_and_payment(self):
        self.order.button_confirm()
        receipt = self.order.picking_ids
        self.receive(receipt, 2)
        self.assertEqual(self.order.receipt_status, 'partial')
        first = self.bill(820001)
        self.assertEqual(first.amount_total, 40)

        withholding = self.env['erpec.withholding'].with_user(self.accountant).create({
            'invoice_id': first.id, 'reference': 'RET-ACEPTACION-1', 'date': fields.Date.today(), 'journal_id': self.general.id,
            'line_ids': [(0, 0, {'name': 'Renta ficticia; no tarifa legal', 'kind': 'income', 'base': 40, 'rate': 5, 'account_id': self.liability.id})]})
        withholding.action_post()
        self.assertEqual(withholding.state, 'posted')
        self.assertAlmostEqual(first.amount_residual, 38)
        self.assertEqual(sum(withholding.entry_id.line_ids.mapped('balance')), 0)
        entry = withholding.entry_id
        withholding.action_post()
        self.assertEqual(withholding.entry_id, entry, 'Repetir contabilizar no debe crear otro asiento.')

        self.pay(first, 38)
        self.assertEqual(first.payment_state, 'paid')
        self.assertTrue(first.line_ids.filtered(lambda l: l.account_type == 'liability_payable').reconciled)

        pending = self.order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        self.receive(pending, 3)
        second = self.bill(820002)
        self.assertEqual(second.amount_total, 60)
        with self.assertRaises(UserError):
            self.order.with_user(self.accountant).action_create_invoice()

        wizard = self.env['stock.return.picking'].with_user(self.stock).with_context(
            active_model='stock.picking', active_id=receipt.id, active_ids=receipt.ids).create({'picking_id': receipt.id})
        wizard.product_return_moves.write({'quantity': 1, 'to_refund': True})
        returned = self.env['stock.picking'].browse(wizard.action_create_returns()['res_id'])
        self.receive(returned, 1)
        credit = self.bill(820003)
        self.assertEqual(credit.move_type, 'in_refund')
        self.assertEqual(credit.amount_total, 20)
        # La retención ya conciliada y el pago no se deshacen por la devolución: la nota queda abierta.
        self.assertEqual(first.payment_state, 'paid')
        self.assertEqual(withholding.state, 'posted')
        self.assertEqual(credit.amount_residual, 20)


@tagged('post_install', '-at_install')
class ErasureVersusFiscalRetentionCase(TransactionCase):
    """DI25-05.3: solicitud de eliminación de un contacto con comprobantes dentro de los 7 años mínimos de conservación fiscal
    (Reglamento de Comprobantes de Venta, Retención y Documentos Complementarios, Art. 41)."""

    def setUp(self):
        super().setUp()
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.partner = self.env['res.partner'].create({'name': 'Titular con comprobantes — ensayo'})
        self.officer = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Responsable DP aceptación', 'login': 'acc_dpo', 'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('erpec_data_protection.group_data_protection_officer').id])]})

    def invoice(self, date):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner.id, 'invoice_date': date, 'date': date,
            'invoice_line_ids': [(0, 0, {'name': 'Servicio de ensayo', 'quantity': 1, 'price_unit': 10, 'tax_ids': [(5, 0, 0)]})]})
        move.action_post()
        return move

    def request(self):
        return self.env['erpec.data.subject.request'].with_user(self.officer).create({
            'name': 'Eliminación - titular con comprobantes', 'request_type': 'eliminacion', 'requester_name': 'Titular', 'partner_id': self.partner.id,
            'responsible_id': self.officer.id, 'identity_verified': True, 'response_notes': 'Se eliminan los datos no fiscales.'})

    def test_recent_fiscal_documents_block_a_plain_erasure_answer(self):
        self.invoice(fields.Date.today())
        request = self.request()
        self.assertIn('Art. 41', request.retention_blockers)
        with self.assertRaisesRegex(UserError, 'sin documentar la excepción'):
            request.action_mark_answered()
        request.exception_notes = 'Los comprobantes se conservan 7 años por obligación legal (Art. 18 LOPDP).'
        request.action_mark_answered()
        self.assertEqual(request.state, 'answered')

    def test_documents_older_than_seven_years_do_not_block(self):
        old = fields.Date.today().replace(year=fields.Date.today().year - 8)
        self.invoice(old)
        request = self.request()
        self.assertFalse(request.retention_blockers)
        request.action_mark_answered()
        self.assertEqual(request.state, 'answered')
