from datetime import timedelta
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

class TestProvision(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(user=self.env.ref('base.user_admin'), su=False, context=dict(self.env.context, allowed_company_ids=[self.env.company.id], no_reset_password=True))
        plan = self.env['erpec.plan'].create({'name':'Piloto','code':'PROVISION-TEST','erp':True,'terms':'Sin cobro'})
        self.contract = self.env['erpec.subscription'].create({'name':'Alta sintética','plan_id':plan.id,'ends_on':fields.Date.today()+timedelta(days=10),'billing_owner':'manual','billing_reference':'Operador de pruebas','authorization':'Caso sintético'})
        self.contract.action_activate()

    def test_duplicate_restart_and_stale_result(self):
        first = self.contract.action_provision()['res_id']
        self.assertEqual(first, self.contract.action_provision()['res_id'])
        claim = self.env['erpec.provision'].claim_next()
        self.assertEqual(claim['id'], first)
        self.assertFalse(self.env['erpec.provision'].claim_next())
        job = self.env['erpec.provision'].browse(first)
        job._update({'lease_until':fields.Datetime.now()-timedelta(seconds=1)})
        recovered = self.env['erpec.provision'].claim_next()
        with self.assertRaises(AccessError):
            job.finish(claim['token'], True)
        job.finish(recovered['token'], True)
        self.assertEqual(job.state, 'ready')
        # Servidor compartido por subdominio (OP08), no un puerto dedicado por cliente.
        self.assertEqual(job.endpoint, 'http://%s.localtest.me:8200' % job.name)
        with self.assertRaises(AccessError):
            job.finish(recovered['token'], True)
        self.contract.action_suspend()
        stop = self.env['erpec.provision'].claim_next()
        self.assertEqual(stop['desired'], 'stop')
        job.finish(stop['token'], True)
        self.assertEqual(job.state, 'suspended')
        self.contract.action_resume()
        start = self.env['erpec.provision'].claim_next()
        self.assertEqual(start['instance'], claim['instance'])

    def test_failure_limit_and_no_browser_activation(self):
        job = self.env['erpec.provision'].browse(self.contract.action_provision()['res_id'])
        for attempt in range(3):
            claim = self.env['erpec.provision'].claim_next()
            job.finish(claim['token'], False)
        self.assertEqual(job.state, 'failed')
        self.assertFalse(self.env['erpec.provision'].claim_next())
        with self.assertRaises(AccessError):
            job.write({'state':'ready'})
        job.action_retry()
        self.assertEqual(job.attempts, 0)
