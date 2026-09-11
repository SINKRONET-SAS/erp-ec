"""Ciclo comercial por perfiles, entregas, cobros bancarios y devolución."""
from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install')
class SalesFlowCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env=self.env(context=dict(self.env.context,no_reset_password=True))
        self.seller=new_test_user(self.env,login='sp02_seller',groups='sales_team.group_sale_salesman')
        self.stock=new_test_user(self.env,login='sp02_sales_stock',groups='stock.group_stock_user')
        self.accountant=new_test_user(self.env,login='sp02_sales_accountant',groups='account.group_account_manager,sales_team.group_sale_salesman_all_leads')
        self.partner=self.env['res.partner'].create({'name':'Cliente SP02 — ensayo'})
        self.income=self.env['account.account'].create({'name':'Ventas SP02 ensayo','code':'SP02REV','account_type':'income'})
        self.tax=self.env['account.tax'].search([('company_id','=',self.env.company.id),('type_tax_use','=','sale'),('amount','=',15),('amount_type','=','percent')],limit=1)
        self.assertTrue(self.tax)
        self.product=self.env['product.product'].create({'name':'Mercadería comercial SP02','type':'consu','is_storable':True,
            'invoice_policy':'delivery','standard_price':5,'property_account_income_id':self.income.id,'taxes_id':[(6,0,self.tax.ids)]})
        self.location=self.env['stock.warehouse'].search([('company_id','=',self.env.company.id)],limit=1).lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.product,self.location,10)
        self.order=self.env['sale.order'].with_user(self.seller).create({'partner_id':self.partner.id,'user_id':self.seller.id,
            'order_line':[(0,0,{'product_id':self.product.id,'product_uom_qty':5,'price_unit':20,'tax_id':[(6,0,self.tax.ids)]})]})
        self.bank=self.env['account.journal'].create({'name':'Cobros SP02 sin conexión','code':'SP2CB','type':'bank'})
        transit=self.env['account.account'].create({'name':'Cobros pendientes SP02','code':'SP02CT','account_type':'asset_current','reconcile':True})
        self.bank.inbound_payment_method_line_ids.payment_account_id=transit
        self.bank.outbound_payment_method_line_ids.payment_account_id=transit

    def deliver(self,picking,quantity):
        picking=picking.with_user(self.stock)
        for move in picking.move_ids:
            move.quantity=quantity
            move.picked=True
        picking.with_context(skip_backorder=True).button_validate()
        self.assertEqual(picking.state,'done')

    def invoice(self,number):
        order=self.order.with_user(self.accountant)
        previous=order.invoice_ids
        wizard=self.env['sale.advance.payment.inv'].with_user(self.accountant).with_context(active_model='sale.order',active_ids=order.ids).create({'advance_payment_method':'delivered'})
        wizard.create_invoices()
        invoice=order.invoice_ids-previous
        self.assertEqual(len(invoice),1)
        invoice.write({'invoice_date':fields.Date.today(),'l10n_latam_document_number':'999-999-'+str(number)})
        invoice.action_post()
        self.assertEqual(invoice.state,'posted')
        self.assertEqual(invoice.invoice_line_ids.account_id,self.income)
        return invoice

    def collect(self,invoice,amount,remaining):
        wizard=self.env['account.payment.register'].with_user(self.accountant).with_context(active_model='account.move',active_ids=invoice.ids).create({
            'journal_id':self.bank.id,'amount':amount,'payment_difference_handling':'open'})
        payment=wizard._create_payments()
        self.assertEqual(invoice.amount_residual,remaining)
        statement=self.env['account.bank.statement'].with_user(self.accountant).create({'name':'Cobro comercial de ensayo','journal_id':self.bank.id})
        line=self.env['account.bank.statement.line'].with_user(self.accountant).create({'statement_id':statement.id,'journal_id':self.bank.id,
            'date':fields.Date.today(),'amount':amount,'partner_id':self.partner.id,'payment_ref':'Cobro SP02 sin fondos externos'})
        self.env['erpec.bank.match'].with_user(self.accountant).create({'statement_line_id':line.id,'payment_id':payment.id}).action_match()
        self.assertTrue(line.is_reconciled)
        return payment

    def test_delivery_invoices_partial_collections_return_and_credit(self):
        self.order.action_confirm()
        delivery=self.order.picking_ids
        self.deliver(delivery,2)
        self.assertEqual(self.order.delivery_status,'partial')
        first=self.invoice(900001101)
        self.assertEqual(first.amount_total,46)
        self.collect(first,20,26)
        self.collect(first,26,0)
        self.assertEqual(first.payment_state,'paid')
        pending=self.order.picking_ids.filtered(lambda p:p.state not in ('done','cancel'))
        self.deliver(pending,3)
        second=self.invoice(900001102)
        self.assertEqual(second.amount_total,69)
        self.assertIn('facturado no significa cobrado',self.order.erpec_sale_guide)
        with self.assertRaises(UserError),self.cr.savepoint():
            self.invoice(900001103)
        returned=self.env['stock.return.picking'].with_user(self.stock).with_context(active_model='stock.picking',active_id=delivery.id,active_ids=delivery.ids).create({'picking_id':delivery.id})
        returned.product_return_moves.write({'quantity':1,'to_refund':True})
        picking=self.env['stock.picking'].browse(returned.action_create_returns()['res_id'])
        self.deliver(picking,1)
        self.assertEqual(first.amount_residual,0)
        self.assertEqual(second.amount_residual,69)
        credit=self.invoice(900001104)
        self.assertEqual(credit.move_type,'out_refund')
        self.assertEqual(credit.amount_total,23)
        (second.line_ids|credit.line_ids).filtered(lambda l:l.account_type=='asset_receivable').reconcile()
        self.assertEqual(second.amount_residual,46)
        self.collect(second,46,0)
        self.assertEqual(credit.amount_residual,0)
        self.assertEqual(self.order.order_line.qty_delivered,4)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product,self.location),6)
        self.assertIn('devolución',self.order.erpec_sale_guide)

    def test_service_invoice_and_role_boundaries(self):
        self.product.write({'type':'service','invoice_policy':'order'})
        self.order.action_confirm()
        self.assertFalse(self.order.picking_ids)
        self.assertIn('En servicios',self.order.erpec_sale_guide)
        invoice=self.invoice(900001105)
        self.assertEqual(invoice.amount_total,115)
        with self.assertRaises(AccessError):
            invoice.with_user(self.stock).read(['amount_residual'])
        self.assertTrue(self.order.with_user(self.seller).erpec_sale_guide)
        arch=self.order.get_view(view_id=self.env.ref('sale.view_order_form').id,view_type='form')['arch']
        self.assertIn('erpec_sale_guide',arch)
        self.assertIn('Preparar anticipo',arch)

    def test_cancelled_order_preserves_published_invoice(self):
        self.product.invoice_policy='order'
        self.order.action_confirm()
        invoice=self.invoice(900001106)
        self.order.with_context(disable_cancel_warning=True).action_cancel()
        self.assertEqual(self.order.state,'cancel')
        self.assertEqual(invoice.state,'posted')
        self.assertEqual(invoice.amount_residual,115)
        self.assertIn('no los revierte',self.order.erpec_sale_guide)

    def test_undelivered_stock_cannot_be_invoiced_as_delivered(self):
        self.order.action_confirm()
        with self.assertRaises(UserError),self.cr.savepoint():
            self.invoice(900001107)
        self.assertFalse(self.order.invoice_ids)
        self.assertIn('Sin cantidades facturables',self.order.erpec_sale_guide)
        self.assertEqual(self.order.order_line.qty_delivered,0)
        workspace=self.env['erpec.workspace'].browse(self.env['erpec.workspace'].action_home()['res_id'])
        action=workspace.with_user(self.seller).with_context(erpec_area='sales').action_area()
        self.assertEqual(action['id'],self.env.ref('erpec_workspace.sale_action').id)
        self.assertNotIn('search_default_my_quotation',str(action['context']))
