"""Reproducción CM28 en transacciones aisladas, sin contactar PayPhone."""
from unittest.mock import patch
from odoo.exceptions import ValidationError
from .test_selfservice import TestSelfserviceRequest, SIGNUP_VALUES
from odoo.addons.erpec_payphone.models.payphone import Provider

class TestCM28Customers(TestSelfserviceRequest):
    def test_two_customers_keep_separate_contracts_and_instances(self):
        requests = self.env['erpec.selfservice.request']
        with patch.object(Provider, '_request', return_value=self._prepare_response()), patch.object(self.env.cr, 'commit', return_value=None):
            first = requests.create_from_signup(dict(SIGNUP_VALUES, plan_id=self.plan.id))
            second = requests.create_from_signup(dict(SIGNUP_VALUES, company_name='Segundo cliente', plan_id=self.plan.id))
            self.env['erpec.payphone.payment']._cron_process()
        self.assertEqual(first.subscription_id.company_id, second.subscription_id.company_id)
        for index, signup in enumerate(first | second):
            payment = signup.payment_id
            reply = {'transactionId': 900 + index, 'clientTransactionId': payment.reference, 'amount': 4900, 'currency': 'USD', 'statusCode': 3}
            with patch.object(Provider, '_request', return_value=reply):
                payment._receive_return(str(900 + index))
        first.payment_id._reconcile()
        second.payment_id._reconcile()
        self.assertNotEqual(first.customer_id, second.customer_id)
        jobs = self.env['erpec.provision'].search([('subscription_id', 'in', (first | second).mapped('subscription_id').ids)])
        self.assertEqual(len(jobs), 2)
        self.assertEqual(len(set(jobs.mapped('name'))), 2)
        self.assertEqual(set(jobs.mapped('customer_id').ids), set((first | second).mapped('customer_id').ids))
        self.assertEqual(first.state, 'paid')

    def test_customer_operator_cannot_be_reassigned(self):
        from odoo.exceptions import AccessError
        customer = self.env['erpec.customer'].create({'name': 'Cliente aislado'})
        with self.assertRaises(AccessError):
            customer.write({'reference': 'otra-identidad'})
        with self.assertRaises(AccessError):
            customer.write({'company_id': self.env.company.id})

    def test_legacy_contract_keeps_legacy_instance(self):
        contract = self.env['erpec.subscription'].create({
            'name': 'Histórico', 'plan_id': self.plan.id, 'ends_on': '2099-01-01',
            'billing_owner': 'manual', 'billing_reference': 'Histórico', 'authorization': 'Prueba'})
        contract.action_activate()
        job = self.env['erpec.provision']._request(contract)
        self.assertFalse(job.customer_id)
        self.assertEqual(job, self.env['erpec.provision']._request(contract))

    def test_idempotency_and_users_amount(self):
        self.plan.write({'max_users':2,'additional_user_price':7})
        values=dict(SIGNUP_VALUES,plan_id=self.plan.id,user_quantity=4,request_key='a'*32)
        first=self.env['erpec.selfservice.request'].create_from_signup(values)
        second=self.env['erpec.selfservice.request'].create_from_signup(values)
        self.assertEqual(first,second)
        self.assertEqual(first.payment_id.amount,63)
        self.assertEqual(first.subscription_id.commercial_snapshot['users'],4)
        self.assertEqual(first.payment_id.state,'queued')

    def test_confirmed_state_and_provision_revision(self):
        signup=self.env['erpec.selfservice.request'].create_from_signup(dict(SIGNUP_VALUES,plan_id=self.plan.id))
        with patch.object(Provider,'_request',return_value=self._prepare_response()),patch.object(self.env.cr,'commit',return_value=None):
            self.env['erpec.payphone.payment']._cron_process()
        payment=signup.payment_id
        reply={'transactionId':997,'clientTransactionId':payment.reference,'amount':4900,'currency':'USD','statusCode':3}
        with patch.object(Provider,'_request',return_value=reply): payment._receive_return('997')
        payment._reconcile();payment._reconcile()
        job=self.env['erpec.provision'].search([('customer_id','=',signup.customer_id.id)])
        claim=self.env['erpec.provision'].claim_next()
        self.assertEqual(claim['snapshot']['total'],49)
        job.finish(claim['token'],True,{'revision':claim['revision'],'active_users':1})
        signup.invalidate_recordset()
        self.assertEqual(signup.state,'provisioned')
        self.assertFalse(self.env['erpec.provision'].claim_next())

    def _pay(self, signup, remote_id):
        payment=signup.payment_id
        with patch.object(Provider,'_request',return_value=self._prepare_response()),patch.object(self.env.cr,'commit',return_value=None):
            self.env['erpec.payphone.payment']._cron_process()
        reply={'transactionId':remote_id,'clientTransactionId':payment.reference,'amount':int(round(payment.amount*100)),'currency':'USD','statusCode':3}
        with patch.object(Provider,'_request',return_value=reply):payment._receive_return(str(remote_id))
        payment._reconcile()

    def test_renewal_changes_users_only_next_period(self):
        from odoo import Command, fields
        from odoo.tests.common import new_test_user
        from datetime import timedelta
        owner=new_test_user(self.env,login='cm28_owner',groups='base.group_portal')
        self.plan.write({'fiscal_reviewed':True,'max_users':2,'additional_user_price':7,
            'option_ids':[Command.create({'capability_id':self.env.ref('erpec_suite.capability_assets').id})]})
        requests=self.env['erpec.selfservice.request']
        first=requests._create_signup(dict(SIGNUP_VALUES,plan_id=self.plan.id),owner_user=owner)
        self._pay(first,1100)
        job=self.env['erpec.provision'].search([('customer_id','=',first.customer_id.id)])
        renewal=requests._create_signup(dict(SIGNUP_VALUES,plan_id=self.plan.id,user_quantity=4),owner_user=owner,customer=first.customer_id,previous=first.subscription_id)
        self._pay(renewal,1101)
        self.assertEqual(renewal.state,'scheduled')
        self.assertEqual(renewal.subscription_id.starts_on,first.subscription_id.ends_on+timedelta(days=1))
        self.assertEqual(job.subscription_id,first.subscription_id)
        self.assertEqual(first.subscription_id.user_quantity,2)
        self.assertEqual(renewal.subscription_id.user_quantity,4)
        with patch.object(fields.Date,'today',return_value=renewal.subscription_id.starts_on):
            claim=self.env['erpec.provision'].claim_next()
            self.assertEqual(claim['snapshot']['users'],4)
            self.assertEqual(job.subscription_id,renewal.subscription_id)

    def test_late_confirmation_keeps_full_month(self):
        from odoo import fields
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        signup=self.env['erpec.selfservice.request'].create_from_signup(dict(SIGNUP_VALUES,plan_id=self.plan.id))
        later=fields.Date.today()+timedelta(days=45)
        with patch.object(fields.Date,'today',return_value=later):self._pay(signup,1102)
        self.assertEqual(signup.subscription_id.starts_on,later)
        self.assertEqual(signup.subscription_id.ends_on,later+relativedelta(months=1)-timedelta(days=1))
