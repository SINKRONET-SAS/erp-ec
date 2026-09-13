"""Recepciones parciales, divisas y ajustes de inventario con datos sintéticos."""
import base64
from datetime import timedelta
from psycopg2.errors import UniqueViolation
from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install')
class ImportCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, no_reset_password=True))
        self.accounts = {}
        for code, kind in [('VAL', 'asset_current'), ('IN', 'asset_current'), ('OUT', 'asset_current'), ('EXP', 'expense')]:
            self.accounts[code] = self.env['account.account'].create({'code': 'IMPTEST'+code, 'name': 'Ensayo '+code, 'account_type': kind})
        self.journal = self.env['account.journal'].create({'name': 'Inventario ensayo', 'code': 'IMPT', 'type': 'general'})
        self.category = self.env['product.category'].create({'name': 'Importación AVCO', 'property_cost_method': 'average', 'property_valuation': 'real_time', 'property_stock_journal': self.journal.id, 'property_stock_valuation_account_id': self.accounts['VAL'].id, 'property_stock_account_input_categ_id': self.accounts['IN'].id, 'property_stock_account_output_categ_id': self.accounts['OUT'].id, 'property_account_expense_categ_id': self.accounts['EXP'].id})
        self.products = self.env['product.product'].create([{'name': 'Mercadería '+name, 'type': 'consu', 'is_storable': True, 'categ_id': self.category.id, 'supplier_taxes_id': [(5, 0, 0)]} for name in ['A', 'B']])
        self.supplier = self.env['res.partner'].create({'name': 'Proveedor extranjero sintético', 'country_id': self.env.ref('base.us').id})
        self.purchase = self.env['purchase.order'].create({'partner_id': self.supplier.id, 'order_line': [(0, 0, {'product_id': product.id, 'product_qty': 10, 'price_unit': 10, 'taxes_id': [(5, 0, 0)]}) for product in self.products]})
        self.purchase.button_confirm()
        picking = self.purchase.picking_ids
        for move in picking.move_ids:
            move.quantity = 5
            move.picked = True
        picking.with_context(skip_backorder=True).button_validate()
        self.receipt = picking
        attachment = self.env['ir.attachment'].create({'name': 'Documento sintético.txt', 'datas': base64.b64encode(b'Sin validez aduanera')})
        self.dossier = self.env['erpec.importation'].create({'name': 'IMP-PRUEBA', 'partner_id': self.supplier.id, 'purchase_ids': [(6, 0, self.purchase.ids)], 'shipment': 'EMBARQUE-SINTETICO', 'customs_reference': 'SIN-VALIDEZ', 'attachment_ids': [(4, attachment.id)]})
        service = self.env['product.product'].create({'name': 'Flete sintético', 'type': 'service', 'property_account_expense_id': self.accounts['EXP'].id, 'supplier_taxes_id': [(5, 0, 0)]})
        self.bill = self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': self.supplier.id, 'invoice_date': fields.Date.today(), 'l10n_latam_document_number': '001-001-000000031', 'invoice_line_ids': [(0, 0, {'product_id': service.id, 'name': 'Flete', 'quantity': 1, 'price_unit': 20, 'account_id': self.accounts['EXP'].id, 'tax_ids': [(5, 0, 0)]})]})
        self.bill.action_post()
        self.charge = self.env['erpec.import.charge'].create({'import_id': self.dossier.id, 'name': 'Flete', 'kind': 'capital', 'bill_line_id': self.bill.invoice_line_ids.id})

    def set_rate(self, currency, date, value):
        # La transacción de prueba restaura la tasa real existente al terminar cada caso.
        rates = self.env['res.currency.rate']
        rate = rates.search([('currency_id', '=', currency.id), ('name', '=', date), ('company_id', '=', self.env.company.id)])
        if rate:
            rate.rate = value
        else:
            rates.create({'currency_id': currency.id, 'name': date, 'company_id': self.env.company.id, 'rate': value})

    def prepare(self):
        return self.env['stock.landed.cost'].browse(self.dossier.action_prepare_cost()['res_id'])

    def test_partial_cost_accounting_and_inverse(self):
        self.assertEqual(self.receipt.state, 'done')
        self.assertTrue(self.purchase.picking_ids.filtered(lambda picking: picking.state != 'done'))
        cost = self.prepare()
        self.assertEqual(cost.amount_total, 20)
        cost.button_validate()
        self.assertEqual(cost.state, 'done')
        self.assertEqual(cost.account_move_id.state, 'posted')
        self.assertAlmostEqual(sum(cost.account_move_id.line_ids.mapped('balance')), 0)
        self.assertEqual(sum(cost.stock_valuation_layer_ids.mapped('value')), 20)
        self.assertEqual(self.products.mapped('standard_price'), [12, 12])
        reverse = self.env['stock.landed.cost'].browse(cost.action_erpec_reverse()['res_id'])
        reverse.button_validate()
        self.assertEqual(reverse.account_move_id.state, 'posted')
        self.assertEqual(self.products.mapped('standard_price'), [10, 10])
        with self.assertRaises(ValidationError):
            cost.action_erpec_reverse()

    def test_duplicate_foreign_receipt_missing_document_and_modified_amount(self):
        with self.assertRaises(UniqueViolation), self.cr.savepoint():
            self.charge.copy()
        self.dossier.customs_reference = False
        with self.assertRaisesRegex(ValidationError, 'referencia'):
            self.prepare()
        self.dossier.customs_reference = 'SINTETICO'
        cost = self.prepare()
        with self.assertRaises(ValidationError):
            self.prepare()
        cost.cost_lines.price_unit = 21
        with self.assertRaisesRegex(ValidationError, 'origen'):
            cost.button_validate()
        cost.cost_lines.price_unit = 20
        alien = self.receipt.copy({'origin': 'Recepción ajena'})
        cost.picking_ids = alien
        with self.assertRaisesRegex(ValidationError, 'recepciones'):
            cost.button_validate()

    def test_currency_and_sold_goods(self):
        euro = self.env.ref('base.EUR')
        euro.active = True
        self.set_rate(euro, fields.Date.today(), 0.5)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.dossier.currency_id = euro
        self.charge.unlink()
        foreign_bill = self.bill.copy({'currency_id': euro.id, 'invoice_date': fields.Date.today(), 'l10n_latam_document_number': '001-001-000000032'})
        foreign_bill.action_post()
        charge = self.env['erpec.import.charge'].create({'import_id': self.dossier.id, 'name': 'Flete EUR', 'kind': 'capital', 'bill_line_id': foreign_bill.invoice_line_ids.id})
        self.assertAlmostEqual(charge.amount, 40)
        location = self.receipt.location_dest_id
        move = self.env['stock.move'].create({'name': 'Entrega sintética previa al costo', 'product_id': self.products[0].id, 'product_uom_qty': 2, 'product_uom': self.products[0].uom_id.id, 'location_id': location.id, 'location_dest_id': self.env.ref('stock.stock_location_customers').id})
        move._action_confirm(); move._action_assign(); move.quantity = 2; move.picked = True; move._action_done()
        cost = self.prepare(); cost.button_validate()
        self.assertAlmostEqual(sum(cost.stock_valuation_layer_ids.mapped('value')), 32)
        self.assertAlmostEqual(sum(cost.account_move_id.line_ids.mapped('balance')), 0)
        self.assertEqual(cost.account_move_id.state, 'posted')

    def test_fifo_supported_and_standard_rejected(self):
        self.category.property_cost_method = 'standard'
        with self.assertRaisesRegex(ValidationError, 'FIFO/AVCO'), self.cr.savepoint():
            self.prepare()
        self.category.property_cost_method = 'fifo'
        cost=self.prepare(); cost.button_validate()
        self.assertEqual(cost.account_move_id.state, 'posted')


    def test_classification_and_original_accounts_are_preserved(self):
        self.charge.kind='expense'
        with self.assertRaises(ValidationError):self.prepare()
        self.charge.kind='recoverable'
        with self.assertRaises(ValidationError):self.prepare()
        self.charge.kind='capital'
        cost=self.prepare()
        original=cost.cost_lines.account_id
        cost.cost_lines.account_id=self.accounts['IN']
        with self.assertRaisesRegex(ValidationError,'origen'):cost.button_validate()
        cost.cost_lines.account_id=original;cost.button_validate()
        with self.assertRaises(ValidationError):cost.cost_lines.price_unit=0
        reverse=self.env['stock.landed.cost'].browse(cost.action_erpec_reverse()['res_id'])
        reverse.cost_lines.price_unit=20
        with self.assertRaisesRegex(ValidationError,'origen'):reverse.button_validate()

    def test_company_and_stock_role_access(self):
        other=self.env['res.company'].create({'name':'Otra DEMO importaciones'})
        outsider=new_test_user(self.env,login='import_other_company',groups='account.group_account_manager',company_id=other.id,company_ids=[(6,0,other.ids)])
        with self.assertRaises(AccessError):self.dossier.with_user(outsider).read(['name'])
        stock=new_test_user(self.env,login='import_stock_reader',groups='stock.group_stock_user',company_id=self.env.company.id,company_ids=[(6,0,self.env.company.ids)])
        self.assertTrue(self.dossier.with_user(stock).read(['name']))
        with self.assertRaises(AccessError):self.dossier.with_user(stock).action_prepare_cost()
        self.assertTrue(self.dossier.get_view(view_type='form')['arch'])


    def test_partial_supplier_payments_and_exchange_difference(self):
        euro=self.env.ref('base.EUR');euro.active=True
        today=fields.Date.today();payment_date=today+timedelta(days=1)
        self.set_rate(euro, today, 0.5)
        self.set_rate(euro, payment_date, 0.4)
        self.charge.unlink()
        bill=self.bill.copy({'currency_id':euro.id,'invoice_date':today,'l10n_latam_document_number':'001-001-000000033'})
        bill.action_post()
        self.env['erpec.import.charge'].create({'import_id':self.dossier.id,'name':'Flete con pago en divisa','kind':'capital','bill_line_id':bill.invoice_line_ids.id})
        cost=self.prepare();cost.button_validate()
        self.assertEqual(cost.amount_total,40)
        bank=self.env['account.journal'].create({'name':'Banco de ensayo sin conexión','code':'IMPBN','type':'bank'})
        bank.outbound_payment_method_line_ids.payment_account_id=self.accounts['IN']
        for amount,expected in [(20,12),(30,0)]:
            wizard=self.env['account.payment.register'].with_context(active_model='account.move',active_ids=bill.ids).create({'journal_id':bank.id,'currency_id':self.env.company.currency_id.id,'payment_date':payment_date,'amount':amount,'payment_difference_handling':'open'})
            payment=wizard._create_payments()
            self.assertEqual(payment.move_id.state,'posted')
            payable=bill.line_ids.filtered(lambda line:line.account_type=='liability_payable')
            self.assertAlmostEqual(abs(sum(payable.mapped('amount_residual_currency'))),expected)
        self.assertTrue(payable.reconciled)
        self.assertAlmostEqual(bill.amount_residual,0)
        self.assertEqual(cost.amount_total,40)
        partials=payable.matched_debit_ids | payable.matched_credit_ids
        exchange=partials.exchange_move_id | payable.full_reconcile_id.exchange_move_id
        self.assertTrue(exchange)
        self.assertTrue(all(move.state=='posted' for move in exchange))
        for move in exchange:
            self.assertAlmostEqual(sum(move.line_ids.mapped('balance')),0)
        losses=exchange.line_ids.filtered(lambda line:line.account_id==self.env.company.expense_currency_exchange_account_id)
        self.assertAlmostEqual(sum(losses.mapped('balance')),10)
