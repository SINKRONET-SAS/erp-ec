"""Pruebas contables reales en base aislada; ningún comprobante se transmite."""
from datetime import date
from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user

class TestAssets(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env=self.env(context=dict(self.env.context,no_reset_password=True))
        company=self.env.company
        company.currency_id=self.env.ref('base.USD')
        def account(code,kind):
            return self.env['account.account'].create({'name':code,'code':code,'account_type':kind})
        self.asset_account=account('CM28A','asset_fixed')
        self.accumulated=account('CM28D','asset_fixed')
        self.expense=account('CM28E','expense')
        self.clearing=account('CM28C','equity')
        self.loss=account('CM28L','expense')
        self.gain=account('CM28G','income_other')
        self.payable=account('CM28P','liability_payable');self.payable.reconcile=True
        self.receivable=account('CM28R','asset_receivable');self.receivable.reconcile=True
        self.journal=self.env['account.journal'].create({'name':'Activos ensayo','code':'CMA','type':'general'})
        self.category=self.env['erpec.asset.category'].create({'name':'Equipos ensayo','journal_id':self.journal.id,
            'asset_account_id':self.asset_account.id,'accumulated_account_id':self.accumulated.id,'expense_account_id':self.expense.id,
            'clearing_account_id':self.clearing.id,'loss_account_id':self.loss.id,'gain_account_id':self.gain.id,'months':3})
        self.partner=self.env['res.partner'].create({'name':'Proveedor de ensayo','property_account_payable_id':self.payable.id,'property_account_receivable_id':self.receivable.id})

    def asset(self,**kw):
        values={'name':'Equipo ensayo','category_id':self.category.id,'cost':1000,'residual':100,'months':3,'acquisition_date':'2025-01-01','service_date':'2025-01-01'}
        values.update(kw)
        return self.env['erpec.asset'].create(values)

    def ledger(self,account):
        return sum(self.env['account.move.line'].search([('account_id','=',account.id),('parent_state','=','posted')]).mapped('balance'))

    def invoice(self,kind,amount):
        purchase=kind=='in_invoice'
        journal=self.env['account.journal'].create({'name':'Compra' if purchase else 'Venta','code':'CMP' if purchase else 'CMV','type':'purchase' if purchase else 'sale'})
        move=self.env['account.move'].create({'move_type':kind,'partner_id':self.partner.id,'invoice_date':'2025-01-01','date':'2025-01-01',
            'journal_id':journal.id,'invoice_line_ids':[Command.create({'name':'Equipo','account_id':self.expense.id if purchase else self.gain.id,'quantity':1,'price_unit':amount,'tax_ids':[Command.clear()]})]})
        move.action_post()
        return move

    def test_depreciation_idempotent_and_reconciles(self):
        asset=self.asset();asset.action_confirm();asset.action_confirm()
        self.assertEqual(len(asset.move_ids),1)
        asset.action_depreciate();asset.action_depreciate()
        self.assertEqual(len(asset.move_ids),4)
        self.assertEqual(asset.accumulated,900)
        self.assertEqual(asset.book_value,100)
        self.assertEqual(self.ledger(self.asset_account),asset.ledger_cost)
        self.assertEqual(-self.ledger(self.accumulated),asset.ledger_accumulated)

    def test_partial_month_rounding_and_residual(self):
        asset=self.asset(cost=100,residual=1,months=3,service_date='2025-01-16')
        asset.action_confirm()
        self.assertEqual(len(asset.line_ids),4)
        self.assertAlmostEqual(sum(asset.line_ids.mapped('amount')),99)
        self.assertEqual(asset.line_ids[0].amount,17.03)
        asset.action_depreciate()
        self.assertEqual(asset.book_value,1)

    def test_disposal_and_reversal_preserve_entries(self):
        asset=self.asset();asset.action_confirm();asset.action_depreciate()
        asset._dispose(date(2025,4,1))
        self.assertEqual(asset.state,'disposed');self.assertEqual(asset.book_value,0)
        self.assertEqual(self.ledger(self.asset_account),0)
        self.assertEqual(self.ledger(self.accumulated),0)
        asset._reverse(date(2025,4,2))
        self.assertEqual(asset.state,'reversed')
        for account in [self.asset_account,self.accumulated,self.expense,self.clearing,self.loss]:
            self.assertEqual(self.ledger(account),0)
        with self.assertRaises(ValidationError):asset._reverse(date(2025,4,3))

    def test_direct_edits_and_foreign_company_denied(self):
        asset=self.asset();asset.action_confirm()
        with self.assertRaises(AccessError):asset.write({'state':'disposed'})
        with self.assertRaises(ValidationError):asset.write({'cost':5})
        with self.assertRaises(AccessError):asset.line_ids[0].write({'amount':2})
        with self.assertRaises(AccessError):asset.move_ids.line_ids[0].write({'debit':3})
        company=self.env['res.company'].create({'name':'Otra empresa'})
        user=new_test_user(self.env,login='asset_other',groups='account.group_account_manager',company_id=company.id,company_ids=[Command.set(company.ids)])
        with self.assertRaises(AccessError):asset.with_user(user).with_context(allowed_company_ids=company.ids).action_depreciate()

    def test_closed_period_blocked(self):
        asset=self.asset();asset.action_confirm()
        self.env.company.fiscalyear_lock_date=date(2025,1,31)
        with self.assertRaises(ValidationError):asset.action_depreciate()

    def test_change_estimate_only_future(self):
        asset=self.asset();asset.action_confirm();first=asset.line_ids[0];first._post()
        posted=first.move_id
        self.env['erpec.asset.adjustment'].create({'asset_id':asset.id,'effective_date':'2025-02-01','months':2,'residual':200,'reason':'Revisión de vida útil'}).action_apply()
        self.assertEqual(first.move_id,posted)
        self.assertEqual(sum(asset.line_ids.filtered(lambda l:not l.move_id).mapped('amount')),500)
        asset.action_depreciate();self.assertEqual(asset.book_value,200)
        self.assertEqual(len(asset.revision_ids),1)

    def test_purchase_partial_allocation_and_invoice_protection(self):
        bill=self.invoice('in_invoice',1000);line=bill.invoice_line_ids
        a=self.asset(source_line_id=line.id,cost=600,residual=0)
        b=self.asset(source_line_id=line.id,cost=400,residual=0)
        a.action_confirm();b.action_confirm()
        with self.assertRaises(ValidationError),self.cr.savepoint():self.asset(source_line_id=line.id,cost=1,residual=0)
        with self.assertRaises(ValidationError):bill.button_draft()
        self.assertEqual(self.ledger(self.asset_account),1000)
        self.assertEqual(self.ledger(self.expense),0)

    def test_sale_clears_cost_and_records_gain(self):
        asset=self.asset();asset.action_confirm();asset.action_depreciate()
        invoice=self.invoice('out_invoice',150)
        asset._dispose(date(2025,4,1),invoice.invoice_line_ids)
        self.assertEqual(self.ledger(self.asset_account),0)
        self.assertEqual(self.ledger(self.accumulated),0)
        self.assertEqual(self.ledger(self.gain),-50)

    def test_copy_ordinary_invoice_remains_available(self):
        bill=self.invoice('in_invoice',100)
        copied=bill.copy()
        self.assertEqual(copied.state,'draft')
        self.assertFalse(copied.erpec_asset_id)

    def test_source_date_and_excess_capitalization_rejected(self):
        bill=self.invoice('in_invoice',100)
        with self.assertRaises(ValidationError),self.cr.savepoint():
            self.asset(source_line_id=bill.invoice_line_ids.id,cost=100,residual=0,acquisition_date='2024-12-31')
        with self.assertRaises(ValidationError),self.cr.savepoint():
            self.asset(source_line_id=bill.invoice_line_ids.id,cost=101,residual=0)
