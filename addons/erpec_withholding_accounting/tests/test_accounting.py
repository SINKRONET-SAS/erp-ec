from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError, UserError


@tagged('post_install','-at_install')
class RetentionCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id':[(4,self.env.ref('account.group_account_user').id)]})
        self.partner=self.env['res.partner'].create({'name':'Tercero sintético retención'})
        self.journal=self.env['account.journal'].search([('company_id','=',self.env.company.id),('type','=','general')],limit=1)
        self.liability=self.env['account.account'].create({'name':'Retenciones sintéticas por pagar','code':'ECRET01','account_type':'liability_current'})
        self.asset=self.env['account.account'].create({'name':'Retenciones sintéticas recibidas','code':'ECRET02','account_type':'asset_current'})

    def invoice(self,kind='in_invoice'):
        invoice=self.env['account.move'].create({'move_type':kind,'partner_id':self.partner.id,'invoice_date':'2026-09-10','date':'2026-09-10','invoice_line_ids':[(0,0,{'name':'Servicio sintético','quantity':1,'price_unit':100,'tax_ids':[(5,0,0)]})]})
        invoice.l10n_latam_document_number='001-001-000000123'
        invoice.action_post()
        return invoice

    def retention(self,invoice,rate=2,reference='RET-SINTETICA-1'):
        return self.env['erpec.withholding'].create({'invoice_id':invoice.id,'reference':reference,'date':'2026-09-10','journal_id':self.journal.id,'line_ids':[(0,0,{'name':'Concepto sintético; no tarifa legal','kind':'income','base':100,'rate':rate,'account_id':(self.liability if invoice.move_type=='in_invoice' else self.asset).id})]})

    def test_issued_post_idempotent_reverse(self):
        invoice=self.invoice()
        retention=self.retention(invoice)
        retention.action_post()
        self.assertEqual(invoice.amount_residual,98)
        self.assertEqual(sum(retention.entry_id.line_ids.mapped('balance')),0)
        self.assertEqual(retention.entry_id.line_ids.filtered(lambda line: line.account_id==self.liability).credit,2)
        entry=retention.entry_id
        retention.action_post()
        self.assertEqual(retention.entry_id,entry)
        retention.write({'reversal_date':'2026-09-10','reversal_reason':'Ensayo de reversión'})
        retention.action_reverse()
        self.assertEqual(invoice.amount_residual,100)
        self.assertEqual(retention.reversal_id.state,'posted')
        reversal=retention.reversal_id
        retention.action_reverse()
        self.assertEqual(retention.reversal_id,reversal)

    def test_received_and_partial_retentions(self):
        invoice=self.invoice('out_invoice')
        retention=self.retention(invoice,rate=10)
        retention.action_post()
        self.assertEqual(invoice.amount_residual,90)
        self.assertEqual(retention.entry_id.line_ids.filtered(lambda line: line.account_id==self.asset).debit,10)
        second=self.retention(invoice,rate=20,reference='RET-SINTETICA-2')
        second.action_post()
        self.assertEqual(invoice.amount_residual,70)
        retention.write({'reversal_date':'2026-09-10','reversal_reason':'Revertir únicamente la primera'})
        retention.action_reverse()
        self.assertEqual(invoice.amount_residual,80)
        self.assertEqual(second.state,'posted')

    def test_over_retention_and_protected_state(self):
        invoice=self.invoice()
        first=self.retention(invoice,80)
        first.action_post()
        second=self.retention(invoice,30,'EXCESO')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            second.action_post()
        self.assertEqual(second.state,'draft')
        self.assertFalse(second.entry_id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            second.write({'state':'posted'})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.withholding'].create({'invoice_id':invoice.id,'reference':'FALSO','journal_id':self.journal.id,'state':'posted'})

    def test_posted_document_and_entry_are_immutable(self):
        invoice=self.invoice()
        retention=self.retention(invoice)
        retention.action_post()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            retention.line_ids.rate=3
        with self.assertRaises(ValidationError), self.cr.savepoint():
            retention.entry_id.button_draft()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            retention.entry_id.line_ids[0].write({'account_id':self.asset.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            invoice.button_draft()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            invoice.line_ids.remove_move_reconcile()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            retention.unlink()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            retention.entry_id._reverse_moves()
        partial=retention.entry_id.line_ids.matched_debit_ids | retention.entry_id.line_ids.matched_credit_ids
        with self.assertRaises(ValidationError), self.cr.savepoint():
            partial.unlink()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['account.move.line'].create({'move_id':retention.entry_id.id,'name':'Inserción prohibida','account_id':self.asset.id,'debit':1})

    def test_wrong_account_and_cross_company(self):
        invoice=self.invoice()
        retention=self.retention(invoice)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            retention.line_ids.account_id=self.asset
        other=self.env['res.company'].create({'name':'Empresa ajena para retenciones','country_id':self.env.ref('base.ec').id})
        outsider=self.env['res.users'].with_context(no_reset_password=True).create({'name':'Contador externo','login':'retention-outsider','company_id':other.id,'company_ids':[(6,0,[other.id])],'groups_id':[(6,0,[self.env.ref('account.group_account_user').id])]})
        with self.assertRaises(AccessError), self.cr.savepoint():
            retention.with_user(outsider).action_post()

    def test_frontend_and_native_invoice_view(self):
        view=self.env['erpec.withholding'].get_view(view_id=self.env.ref('erpec_withholding_accounting.retention_form').id,view_type='form')
        self.assertIn('action_post',view['arch'])
        self.assertIn('action_reverse',view['arch'])
        invoice_view=self.env['account.move'].get_view(view_type='form')
        self.assertIn('ec_accounting_withholding_ids',invoice_view['arch'])

    def test_trial_balance_and_ledger(self):
        # La copia de aceptación puede contener movimientos ajenos al ensayo.
        baseline = sum(self.env['account.move.line'].search([
            ('company_id', '=', self.env.company.id), ('parent_state', '=', 'posted'),
            ('date', '=', '2026-09-11')]).mapped('debit'))
        invoice=self.invoice()
        retention=self.retention(invoice)
        retention.action_post()
        report=self.env['erpec.trial.balance'].create({'company_id':self.env.company.id,'date_from':'2026-09-10','date_to':'2026-09-10'})
        report.action_generate()
        self.assertEqual(report.total_debit,report.total_credit)
        self.assertEqual(report.total_balance,0)
        liability=report.line_ids.filtered(lambda line:line.account_id==self.liability)
        self.assertEqual(liability.credit,2)
        self.assertEqual(liability.closing,-2)
        action=liability.action_ledger()
        self.assertIn(('account_id','=',self.liability.id),action['domain'])
        report.write({'date_from':'2026-09-11','date_to':'2026-09-11'})
        report.action_generate()
        self.assertEqual(report.line_ids.filtered(lambda line:line.account_id==self.liability).opening,-2)
        self.assertEqual(report.total_debit,baseline)
        self.assertEqual(report.line_ids.filtered(lambda line:line.account_id==self.liability).debit,0)
        with self.assertRaises(ValidationError),self.cr.savepoint():
            report.date_from='2026-09-12'
            report.action_generate()

    def test_reimbursement_matches_accounting_before_post(self):
        invoice=self.env['account.move'].create({'move_type':'in_invoice','partner_id':self.partner.id,'invoice_date':'2026-09-10','date':'2026-09-10','invoice_line_ids':[(0,0,{'name':'Reembolso sintético','quantity':1,'price_unit':100,'tax_ids':[(5,0,0)],'ec_reimbursement':True})]})
        invoice.l10n_latam_document_number='001-001-000000987'
        with self.assertRaises(ValidationError),self.cr.savepoint():
            invoice.action_post()
        support=self.env['erpec.reimbursement.support'].create({'move_id':invoice.id,'invoice_line_id':invoice.invoice_line_ids.id,'supplier_id':self.partner.id,'document_type_id':self.env.ref('l10n_ec.ec_dt_01').id,'document_number':'001-001-000000555','issue_date':'2026-09-10','untaxed_amount':90,'tax_amount':0})
        with self.assertRaises(ValidationError),self.cr.savepoint():
            invoice.action_post()
        support.untaxed_amount=100
        invoice.action_post()
        self.assertEqual(invoice.amount_total,100)
        self.assertEqual(sum(invoice.line_ids.mapped('balance')),0)
        with self.assertRaises(ValidationError),self.cr.savepoint():
            support.untaxed_amount=101
