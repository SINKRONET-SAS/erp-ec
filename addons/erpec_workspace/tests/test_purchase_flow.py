"""Recorrido nativo de compra con roles, parciales, saldo y devolución."""
from odoo import fields
from odoo.tests import TransactionCase, tagged, new_test_user
from odoo.exceptions import AccessError, UserError


@tagged('post_install', '-at_install')
class PurchaseFlowCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, no_reset_password=True))
        self.buyer = new_test_user(self.env, login='sp02_buyer', groups='purchase.group_purchase_user')
        self.stock = new_test_user(self.env, login='sp02_stock', groups='stock.group_stock_user')
        self.accountant = new_test_user(self.env, login='sp02_accountant', groups='account.group_account_manager')
        self.supplier = self.env['res.partner'].create({'name': 'Proveedor SP02 — ensayo'})
        self.expense = self.env['account.account'].create({'name':'Compras de ensayo SP02',
            'code':'SP02EXP','account_type':'expense'})
        self.products = self.env['product.product'].create([
            {'name': 'Mercadería SP02 '+name, 'type': 'consu', 'is_storable': True,
             'purchase_method': 'receive', 'property_account_expense_id': self.expense.id, 'supplier_taxes_id': [(5,0,0)]} for name in ['A','B']])
        self.order = self.env['purchase.order'].with_user(self.buyer).create({
            'partner_id': self.supplier.id, 'order_line': [(0,0,{'product_id':p.id,
                'product_qty':5,'price_unit':10,'taxes_id':[(5,0,0)]}) for p in self.products]})

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
        bill.write({'invoice_date':fields.Date.today(),
                    'l10n_latam_document_number':'001-001-'+str(number).zfill(9)})
        bill.action_post()
        self.assertEqual(bill.state, 'posted')
        self.assertEqual(bill.invoice_line_ids.account_id, self.expense)
        self.assertAlmostEqual(sum(bill.line_ids.mapped('balance')), 0)
        return bill

    def test_partial_receipt_payment_and_supplier_return(self):
        self.assertIn('Confirma', self.order.erpec_purchase_guide)
        self.order.button_confirm()
        self.assertIn('registra únicamente', self.order.erpec_purchase_guide)
        receipt = self.order.picking_ids
        self.receive(receipt, 2)
        self.assertEqual(self.order.receipt_status, 'partial')
        self.assertIn('Recepción parcial', self.order.erpec_purchase_guide)
        first = self.bill(810001)
        self.assertEqual(first.amount_total, 40)
        pending = self.order.picking_ids.filtered(lambda p:p.state not in ('done','cancel'))
        self.assertEqual(len(pending), 1)
        self.receive(pending, 3)
        second = self.bill(810002)
        self.assertEqual(second.amount_total, 60)
        self.assertEqual(self.order.order_line.mapped('qty_received'), [5,5])
        self.assertIn('facturado no significa pagado', self.order.erpec_purchase_guide)

        pending_account = self.env['account.account'].create({'name':'Pagos pendientes SP02',
            'code':'SP02PEND','account_type':'asset_current','reconcile':True})
        bank = self.env['account.journal'].create({'name':'Banco SP02 sin conexión','code':'SP2BN','type':'bank'})
        bank.outbound_payment_method_line_ids.payment_account_id = pending_account
        for amount, remaining in [(15,25),(25,0)]:
            wizard = self.env['account.payment.register'].with_user(self.accountant).with_context(
                active_model='account.move',active_ids=first.ids).create({
                    'journal_id':bank.id,'amount':amount,'payment_difference_handling':'open'})
            payment = wizard._create_payments()
            self.assertEqual(payment.move_id.state, 'posted')
            self.assertEqual(first.amount_residual, remaining)
        self.assertTrue(first.line_ids.filtered(lambda l:l.account_type=='liability_payable').reconciled)
        self.assertEqual(second.amount_residual, 60)
        with self.assertRaises(UserError):
            self.order.with_user(self.accountant).action_create_invoice()
        self.assertEqual(len(self.order.invoice_ids), 2)

        wizard = self.env['stock.return.picking'].with_user(self.stock).with_context(
            active_model='stock.picking',active_id=receipt.id,active_ids=receipt.ids).create({'picking_id':receipt.id})
        wizard.product_return_moves.write({'quantity':1,'to_refund':True})
        returned = self.env['stock.picking'].browse(wizard.action_create_returns()['res_id'])
        self.receive(returned, 1)
        self.assertEqual(self.order.order_line.mapped('qty_received'), [4,4])
        self.assertIn('devolver mercancía no revierte la factura', self.order.erpec_purchase_guide)
        self.assertEqual(first.amount_residual, 0)
        credit = self.bill(810003)
        self.assertEqual(credit.move_type, 'in_refund')
        self.assertEqual(credit.amount_total, 20)
        self.assertEqual(self.order.order_line.mapped('qty_invoiced'), [4,4])
        # La nota de crédito queda abierta: no se inventa una devolución bancaria.
        self.assertEqual(credit.amount_residual, 20)

    def test_service_guidance_and_financial_access(self):
        service = self.env['product.product'].create({'name':'Servicio SP02','type':'service',
            'purchase_method':'purchase','property_account_expense_id':self.expense.id,'supplier_taxes_id':[(5,0,0)]})
        self.order.order_line.unlink()
        self.order.write({'order_line':[(0,0,{'product_id':service.id,'product_qty':1,
            'price_unit':50,'taxes_id':[(5,0,0)]})]})
        self.order.button_confirm()
        self.assertFalse(self.order.picking_ids)
        self.assertIn('En servicios', self.order.erpec_purchase_guide)
        bill = self.bill(810004)
        with self.assertRaises(AccessError):
            bill.with_user(self.stock).read(['amount_residual'])
        arch = self.order.get_view(view_id=self.env.ref('purchase.purchase_order_form').id,view_type='form')['arch']
        self.assertIn('erpec_purchase_guide', arch)
