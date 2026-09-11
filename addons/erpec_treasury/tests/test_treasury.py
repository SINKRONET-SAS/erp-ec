"""Ensayos de extracto, nómina por empleado y saneamiento reversible de la demo."""
from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install','-at_install')
class TreasuryCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context,no_reset_password=True))
        self.bank = self.env['account.journal'].create({'name':'Banco tesorería ensayo','code':'TSBN','type':'bank'})
        self.pending = self.env['account.account'].create({'name':'Tránsito bancario ensayo',
            'code':'TSPEND','account_type':'asset_current','reconcile':True})
        self.bank.outbound_payment_method_line_ids.payment_account_id = self.pending
        self.bank.inbound_payment_method_line_ids.payment_account_id = self.pending
        self.manager = new_test_user(self.env,login='treasury_payroll',groups='erpec_payroll.group_payroll_manager')
        self.partner = self.env['res.partner'].create({'name':'Beneficiario de ensayo'})

    def payment(self, amount=100, inbound=False):
        pay = self.env['account.payment'].create({'journal_id':self.bank.id,'partner_id':self.partner.id,
            'payment_type':'inbound' if inbound else 'outbound','partner_type':'customer' if inbound else 'supplier',
            'amount':amount,'payment_method_line_id':(self.bank.inbound_payment_method_line_ids if inbound
                else self.bank.outbound_payment_method_line_ids)[:1].id})
        pay.action_post()
        return pay

    def statement(self, amount, partner=None, bank=None):
        bank = bank or self.bank
        statement = self.env['account.bank.statement'].create({'name':'Extracto de ensayo','journal_id':bank.id})
        return self.env['account.bank.statement.line'].create({'statement_id':statement.id,'journal_id':bank.id,
            'date':fields.Date.today(),'payment_ref':'Movimiento sin banco externo','amount':amount,
            'partner_id':(partner or self.partner).id})

    def match(self, statement, payment):
        wizard=self.env['erpec.bank.match'].create({'statement_line_id':statement.id,'payment_id':payment.id})
        wizard.action_match()
        return wizard

    def test_outbound_inbound_repeat_and_undo(self):
        for inbound in [False,True]:
            pay=self.payment(inbound=inbound)
            line=self.statement(100 if inbound else -100)
            wizard=self.match(line,pay)
            self.assertTrue(line.is_reconciled)
            liquidity=pay._seek_for_lines()[0]
            self.assertTrue(liquidity.reconciled)
            count=self.env['account.partial.reconcile'].search_count([])
            wizard.action_match()
            self.assertEqual(self.env['account.partial.reconcile'].search_count([]),count)
            line.action_undo_reconciliation()
            self.assertFalse(line.is_reconciled)
            self.assertFalse(liquidity.reconciled)

    def test_wrong_amount_partner_journal_and_role(self):
        pay=self.payment()
        for amount in [-99,100]:
            with self.assertRaises(ValidationError),self.cr.savepoint():
                self.match(self.statement(amount),pay)
        other=self.env['res.partner'].create({'name':'Otro tercero'})
        with self.assertRaises(ValidationError),self.cr.savepoint():
            self.match(self.statement(-100,other),pay)
        line=self.statement(-100)
        bank=self.env['account.journal'].create({'name':'Otro banco','code':'TSB2','type':'bank'})
        with self.assertRaises(ValidationError),self.cr.savepoint():
            self.match(self.statement(-100, bank=bank),pay)
        stock=new_test_user(self.env,login='treasury_stock',groups='stock.group_stock_user')
        with self.assertRaises(AccessError):
            self.env['erpec.bank.match'].with_user(stock).create({'statement_line_id':line.id,'payment_id':pay.id})

    def period(self):
        self.env.company.erpec_payroll_bank_journal_id=self.bank
        self.env.company.erpec_payroll_payable_id=self.env['account.account'].create({
            'name':'Nómina por pagar ensayo','code':'TSPAY','account_type':'liability_payable','reconcile':True})
        policy=self.env.ref('erpec_operational_demo.payroll_policy')
        plan=self.env['account.analytic.plan'].create({'name':'Centros tesorería ensayo'})
        values=[]
        for index,wage in enumerate([1200,800]):
            employee=self.env['hr.employee'].create({'name':'Empleado tesorería '+str(index),'company_id':self.env.company.id})
            partner=self.env['res.partner'].create({'name':'Beneficiario '+str(index)})
            analytic=self.env['account.analytic.account'].create({'name':'Centro '+str(index),
                'plan_id':plan.id,'company_id':self.env.company.id})
            values.append((0,0,{'employee_id':employee.id,'partner_id':partner.id,'analytic_id':analytic.id,
                'start_date':'2025-01-01','wage':wage,'approved':True}))
        period=self.env['erpec.payroll.period'].create({'name':'Nómina de ensayo julio','policy_id':policy.id,'month':7,'line_ids':values})
        period.action_calculate();period.action_close();period.action_post()
        return period.with_user(self.manager)

    def test_two_employees_partial_payment_and_statement(self):
        period=self.period(); original=period.move_id
        period.action_prepare_payments(); period.action_prepare_payments()
        self.assertEqual(len(period.disbursement_ids),2)
        self.assertEqual(period.move_id,original)
        for item in period.disbursement_ids:
            self.assertEqual(item.residual,item.amount)
            self.assertTrue(item.move_id.line_ids.filtered(lambda l:l.account_type=='liability_payable').date_maturity)
            for amount in [100,item.amount-100]:
                action=item.action_pay()
                wizard=self.env['account.payment.register'].with_user(self.manager).with_context(**action['context']).create({
                    'journal_id':self.bank.id,'amount':amount,'payment_difference_handling':'open'})
                pay=wizard._create_payments()
                line=self.statement(-amount,item.partner_id)
                self.match(line,pay)
            self.assertEqual(item.residual,0)
            self.assertEqual(item.status,'settled')
        with self.assertRaises(ValidationError):
            period.action_reverse()
        with self.assertRaises(ValidationError):
            period.disbursement_ids[0].move_id.button_draft()

    def test_prepare_reverse_and_correction(self):
        period=self.period();period.action_prepare_payments()
        for item in period.disbursement_ids:
            item.action_reverse()
            self.assertTrue(item.reversal_id)
        period.action_reverse()
        self.assertEqual(period.state,'reversed')
        corrected=self.env['erpec.payroll.period'].browse(period.action_correct()['res_id'])
        self.assertEqual(len(corrected.line_ids),2)
        self.assertEqual(corrected.version,2)

    def test_sanitize_demo_and_repeat(self):
        originals=self.env.ref('erpec_demo_seed.bill') | self.env.ref('erpec_demo_seed.invoice')
        original_balances={move.id:move.line_ids.mapped('balance') for move in originals}
        self.env['erpec.workspace'].action_sanitize_demo()
        result=self.env.ref('erpec_sanitized_demo.bill') | self.env.ref('erpec_sanitized_demo.invoice')
        self.assertEqual(sorted(result.mapped('amount_total')),[230,575])
        self.assertTrue(all(m.l10n_latam_document_type_id.code=='01' for m in result))
        self.assertEqual(originals.ec_accounting_withholding_ids.mapped('state'),['reversed','reversed'])
        for move in originals:
            self.assertEqual(move.amount_residual,0)
            self.assertEqual(move.line_ids.mapped('balance'),original_balances[move.id])
        count=self.env['account.move'].search_count([])
        self.env['erpec.workspace'].action_sanitize_demo()
        self.assertEqual(self.env['account.move'].search_count([]),count)

    def test_sanitize_refuses_changed_source(self):
        source=self.env.ref('erpec_demo_seed.bill')
        retention=source.ec_accounting_withholding_ids
        retention.write({'reversal_date':fields.Date.today(),'reversal_reason':'Ensayo previo modificado'})
        retention.action_reverse()
        source.button_draft()
        with self.assertRaises(ValidationError):
            self.env['erpec.workspace'].action_sanitize_demo()

    def test_supplier_credit_advance_partial_and_bank_reconciliation(self):
        accountant=new_test_user(self.env,login='treasury_supplier',groups='account.group_account_manager')
        expense=self.env['account.account'].create({'name':'Gasto proveedor ensayo','code':'TSSUP','account_type':'expense'})
        def document(kind,amount,number):
            move=self.env['account.move'].with_user(accountant).create({
                'move_type':kind,'partner_id':self.partner.id,'invoice_date':fields.Date.today(),
                'l10n_latam_document_number':'001-001-'+str(number),
                'invoice_line_ids':[(0,0,{'name':'Ensayo contable aislado','account_id':expense.id,
                    'quantity':1,'price_unit':amount,'tax_ids':[(5,0,0)]})]})
            move.action_post()
            return move
        bill=document('in_invoice',100,900000101)
        credit=document('in_refund',20,900000102)
        def payable(move):
            return move.line_ids.filtered(lambda line:line.account_type=='liability_payable')
        (payable(bill)|payable(credit)).reconcile()
        self.assertEqual(bill.amount_residual,80)
        self.assertEqual(credit.amount_residual,0)
        advance=self.payment(30)
        (payable(bill)|payable(advance.move_id)).filtered(lambda line:not line.reconciled).reconcile()
        self.assertEqual(bill.amount_residual,50)
        self.match(self.statement(-30),advance)
        for amount,remaining in [(15,35),(35,0)]:
            wizard=self.env['account.payment.register'].with_user(accountant).with_context(
                active_model='account.move',active_ids=bill.ids).create({
                    'journal_id':self.bank.id,'amount':amount,'payment_difference_handling':'open'})
            payment=wizard._create_payments()
            self.assertEqual(bill.amount_residual,remaining)
            statement=self.statement(-amount)
            self.match(statement,payment)
            self.assertTrue(statement.is_reconciled)
        self.assertTrue(payable(bill).reconciled)
        self.assertEqual(bill.payment_state,'paid')
        with self.assertRaises(AccessError):
            bill.with_user(new_test_user(self.env,login='treasury_supplier_stock',groups='stock.group_stock_user')).read(['amount_residual'])
