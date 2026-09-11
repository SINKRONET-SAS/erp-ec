from odoo.tests import TransactionCase, tagged


@tagged('post_install','-at_install')
class OperationCase(TransactionCase):
    def test_service_sale_to_draft_invoice(self):
        partner = self.env['res.partner'].create({'name':'Ensayo Community'})
        product = self.env['product.product'].create({'name':'Servicio sintético','type':'service','invoice_policy':'order','taxes_id':[(5,0,0)]})
        order = self.env['sale.order'].create({'partner_id':partner.id,'order_line':[(0,0,{'product_id':product.id,'product_uom_qty':2,'price_unit':10,'tax_id':[(5,0,0)]})]})
        order.action_confirm()
        invoice = order._create_invoices()
        self.assertEqual(invoice.state,'draft')
        self.assertEqual(invoice.amount_total,20)
        self.assertEqual(invoice.company_id,order.company_id)

    def test_sale_and_purchase_have_stock_transfers(self):
        partner = self.env['res.partner'].create({'name':'Ensayo logístico'})
        product = self.env['product.product'].create({'name':'Artículo sintético','type':'consu','is_storable':True,'taxes_id':[(5,0,0)],'supplier_taxes_id':[(5,0,0)]})
        order = self.env['sale.order'].create({'partner_id':partner.id,'order_line':[(0,0,{'product_id':product.id,'product_uom_qty':1,'price_unit':10,'tax_id':[(5,0,0)]})]})
        order.action_confirm()
        self.assertTrue(order.picking_ids)
        purchase = self.env['purchase.order'].create({'partner_id':partner.id,'order_line':[(0,0,{'product_id':product.id,'product_qty':1,'price_unit':5,'taxes_id':[(5,0,0)]})]})
        purchase.button_confirm()
        self.assertTrue(purchase.picking_ids)
        self.assertEqual(purchase.picking_ids.company_id,purchase.company_id)

    def test_workspace_links_and_fiscal_limit(self):
        workspace = self.env['erpec.workspace'].search([('company_id','=',self.env.company.id)],limit=1)
        if not workspace:
            workspace = self.env['erpec.workspace'].create({'company_id':self.env.company.id})
        for method,model in [('action_sales','sale.order'),('action_purchases','purchase.order'),('action_inventory','stock.picking.type'),('action_invoices','account.move')]:
            self.assertEqual(getattr(workspace,method)()['res_model'],model)
        self.assertIn('Pendiente',workspace.fiscal_scope)
        self.assertTrue(workspace.company_readiness)
        view = workspace.get_view(view_id=self.env.ref('erpec_operations.operation_form').id,view_type='form')
        self.assertIn('action_sales',view['arch'])
        self.assertIn('company_readiness',view['arch'])
