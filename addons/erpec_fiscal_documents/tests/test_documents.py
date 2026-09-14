from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError, UserError
from psycopg2 import IntegrityError

@tagged('post_install', '-at_install')
class FiscalCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name':'Proveedor sintético'})
        self.bill = self.env['account.move'].create({'move_type':'in_invoice','partner_id':self.partner.id,'invoice_line_ids':[(0,0,{'name':'Servicio','quantity':1,'price_unit':100,'tax_ids':[(5,0,0)]})]})
        group = self.env['account.tax.group'].create({'name':'Retención sintética','l10n_ec_type':'withhold_income_purchase'})
        self.tax = self.env['account.tax'].create({'name':'Concepto sintético 2% — no tarifa legal','amount':-2,'amount_type':'percent','type_tax_use':'none','tax_group_id':group.id})

    def support(self, **extra):
        values = {'move_id':self.bill.id,'supplier_id':self.partner.id,'document_type_id':self.env.ref('l10n_ec.ec_dt_01').id,'document_number':'001-001-000000123','issue_date':'2026-09-10','untaxed_amount':10,'tax_amount':1.5}
        values.update(extra)
        return self.env['erpec.reimbursement.support'].create(values)

    def test_preview_does_not_change_accounting(self):
        before = (self.bill.amount_total, self.bill.amount_residual, self.bill.line_ids.ids)
        line = self.env['erpec.purchase.withholding'].create({'move_id':self.bill.id,'tax_id':self.tax.id,'base_amount':100})
        self.assertEqual(line.estimated_amount,2)
        self.assertEqual(line.tax_kind,'income')
        self.assertEqual((self.bill.amount_total,self.bill.amount_residual,self.bill.line_ids.ids),before)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            line.write({'base_amount':-1})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.bill.write({'move_type':'out_invoice'})

    def test_reimbursement_and_copy(self):
        support = self.support()
        self.assertEqual(support.total_amount,11.5)
        self.assertEqual(self.bill.amount_total,100)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.support(document_number='001001000000123')
        duplicate = self.bill.copy()
        self.assertFalse(duplicate.ec_reimbursement_ids)
        self.assertFalse(duplicate.ec_withholding_ids)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            support.write({'untaxed_amount':-1})

    def test_reject_sales_parent_and_invalid_tax(self):
        original=self.bill
        self.bill=self.env['account.move'].create({'move_type':'out_invoice','partner_id':self.partner.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.support()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.purchase.withholding'].create({'move_id':self.bill.id,'tax_id':self.tax.id,'base_amount':100})
        self.bill=original
        self.tax.amount=2
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.purchase.withholding'].create({'move_id':self.bill.id,'tax_id':self.tax.id,'base_amount':100})

    def test_native_sale_and_purchase_links(self):
        product=self.env['product.product'].create({'name':'Servicio sintético','type':'service','invoice_policy':'order','purchase_method':'purchase','taxes_id':[(5,0,0)],'supplier_taxes_id':[(5,0,0)]})
        sale=self.env['sale.order'].create({'partner_id':self.partner.id,'order_line':[(0,0,{'product_id':product.id,'product_uom_qty':1,'price_unit':10})]})
        sale.action_confirm()
        invoice=sale._create_invoices()
        self.assertEqual(invoice.ec_sale_order_ids,sale)
        purchase=self.env['purchase.order'].create({'partner_id':self.partner.id,'order_line':[(0,0,{'product_id':product.id,'product_qty':1,'price_unit':10})]})
        purchase.button_confirm()
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_ids.ec_purchase_order_ids,purchase)
        view=invoice.get_view(view_type='form')
        self.assertIn('ec_withholding_ids',view['arch'])
        self.assertIn('ec_reimbursement_ids',view['arch'])

    def test_company_and_permissions(self):
        support=self.support()
        other=self.env['res.company'].create({'name':'Empresa ajena sintética','country_id':self.env.ref('base.ec').id})
        outsider=self.env['res.users'].with_context(no_reset_password=True).create({'name':'Contador otra empresa','login':'fiscal-test-outsider','company_id':other.id,'company_ids':[(6,0,[other.id])],'groups_id':[(6,0,[self.env.ref('account.group_account_invoice').id])]})
        with self.assertRaises(AccessError), self.cr.savepoint():
            support.with_user(outsider).write({'notes':'No permitido'})
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.env['erpec.reimbursement.support'].with_user(outsider).create({'move_id':self.bill.id,'supplier_id':self.partner.id,'document_type_id':self.env.ref('l10n_ec.ec_dt_01').id,'document_number':'999','issue_date':'2026-09-10','untaxed_amount':10})
        foreign=self.env['res.partner'].create({'name':'Proveedor otra empresa','company_id':other.id})
        with self.assertRaises(UserError), self.cr.savepoint():
            self.support(supplier_id=foreign.id,document_number='456')

    def test_posted_support_immutable(self):
        support=self.support()
        if 'invoice_line_id' in support._fields:
            # El módulo contable exige conciliar el sustento antes de publicar.
            self.bill.invoice_line_ids.ec_reimbursement = True
            support.write({'invoice_line_id': self.bill.invoice_line_ids.id, 'untaxed_amount': 100, 'tax_amount': 0})
        self.bill.invoice_date='2026-09-10'
        self.bill.l10n_latam_document_number='001-001-000000999'
        self.bill.action_post()
        self.assertEqual(self.bill.state,'posted')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            support.write({'notes':'Cambio bloqueado'})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            support.unlink()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.support(document_number='999')


        draft=self.bill.copy()
        other=self.support(move_id=draft.id,document_number='888')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            other.write({'move_id':self.bill.id})
