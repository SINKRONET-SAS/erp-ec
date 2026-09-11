from unittest.mock import patch, Mock
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError
from odoo.addons.erpec_fiscal_connector.connector import ProtocolError


@tagged('post_install', '-at_install')
class FiscalConnectorCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id':[(4,self.env.ref('account.group_account_user').id)]})
        self.connection=self.env['erpec.fiscal.connection'].create({'company_id':self.env.company.id,'base_url':'http://127.0.0.1:3099','organization_ref':'organizacion-sintetica','empresa_ref':901,'workspace_ref':902,'emission_point_ref':903,'api_key':'sk_test_sintetica_sin_validez'})
        self.capabilities={'contractVersion':'1.0','source':'CUSTOM','ambiente':'PRUEBAS','identity':{'empresaId':901,'workspaceId':902,'empresaAmbiente':'1','ownerAmbiente':'1'},'scopes':['emit:factura','read:comprobantes']}
        with patch.object(type(self.connection),'_request',return_value=self.capabilities):
            self.connection.action_verify()
        self.partner=self.env['res.partner'].create({'name':'Cliente sintético fiscal','vat':'1790012345001','street':'Dirección sintética'})
        group=self.env['account.tax.group'].create({'name':'IVA sintético para prueba técnica','l10n_ec_type':'vat15'})
        self.tax=self.env['account.tax'].create({'name':'IVA técnico 15%','amount_type':'percent','amount':15,'type_tax_use':'sale','tax_group_id':group.id})
        self.move=self.env['account.move'].create({'move_type':'out_invoice','partner_id':self.partner.id,'invoice_date':'2026-09-10','date':'2026-09-10','ec_fiscal_payment_code':'20','invoice_line_ids':[(0,0,{'name':'Servicio técnico','quantity':2,'price_unit':100,'discount':10,'tax_ids':[(6,0,self.tax.ids)]})]})
        self.move.l10n_latam_document_number='001-001-000000123'
        self.move.action_post()

    def job(self):
        result=self.move.action_queue_fiscal()
        return self.env['erpec.fiscal.job'].browse(result['res_id'])

    def result(self, job, status='invoice_requested', **values):
        return dict({'contractVersion':'1.0','source':'CUSTOM','externalReference':job.external_reference,'idempotencyKey':job.external_reference,'estado':status,'facturaId':'8001','numero':'001-001-000000777','claveAcceso':'0'*23+'1'+'0'*25,'rawStatus':'AUTORIZADA' if status=='invoice_authorized' else 'PENDIENTE_FIRMA','xmlUrl':None,'rideUrl':None},**values)

    def test_queue_duplicate_snapshot(self):
        job=self.job(); reference=job.external_reference
        self.assertEqual(self.job(),job)
        self.assertEqual(job.payload['invoice']['payments'][0]['amount'],207)
        self.assertEqual(job.payload['invoice']['items'][0]['discount'],10)
        self.partner.name='Nombre editado después'
        self.assertEqual(job.payload['customer']['legalName'],'Cliente sintético fiscal')
        self.assertEqual(job.external_reference,reference)
        with self.assertRaises(ValidationError):
            self.move.button_draft()
        with self.assertRaises(ValidationError):
            self.move.invoice_line_ids.write({'price_unit':999})
        with self.assertRaises(ValidationError):
            self.move.write({'ec_fiscal_payment_code':'01'})
        with self.assertRaises(ValidationError):
            job.write({'state':'authorized'})
        with self.assertRaises(ValidationError):
            self.env['erpec.fiscal.job'].create({'move_id':self.move.id})

    def test_timeout_recovery_uses_lookup(self):
        job=self.job()
        with patch.object(type(self.connection),'_capabilities'), patch.object(type(self.connection),'_request',side_effect=[None,ProtocolError('CONEXION_NO_CONFIRMADA',True)]) as request:
            job.action_process()
            self.assertEqual(request.call_count,2)
        self.assertEqual(job.state,'retry')
        job._save(next_attempt=False)
        self.env.flush_all(); self.env.invalidate_all()
        with patch.object(type(self.connection),'_capabilities'), patch.object(type(self.connection),'_request',return_value=self.result(job,'invoice_authorized')) as request:
            job.action_process()
            self.assertEqual(request.call_count,1)
            self.assertEqual(request.call_args.args[0],'GET')
        self.assertEqual(job.state,'authorized')
        self.assertIn('no entregó',job.message)
        with patch.object(type(self.connection),'_request') as request:
            job.action_process(); request.assert_not_called()

    def test_pending_not_authorized_then_rejected(self):
        job=self.job()
        with patch.object(type(self.connection),'_capabilities'), patch.object(type(self.connection),'_request',side_effect=[None,self.result(job)]) as request:
            job.action_process()
            self.assertEqual(request.call_args.kwargs['key'],job.external_reference)
            self.assertEqual(request.call_args.kwargs['payload'],job.payload)
        self.assertEqual(job.state,'waiting')
        job._save(next_attempt=False)
        with patch.object(type(self.connection),'_capabilities'), patch.object(type(self.connection),'_request',return_value=self.result(job,'invoice_rejected')):
            job.action_process()
        self.assertEqual(job.state,'rejected')
        with self.assertRaises(ProtocolError):
            job._apply(self.result(job))
        self.assertEqual(job.state,'rejected')

    def test_identity_environment_and_scope(self):
        for data in [dict(self.capabilities,ambiente='PRODUCCION'),dict(self.capabilities,identity={**self.capabilities['identity'],'empresaId':999}),dict(self.capabilities,identity={**self.capabilities['identity'],'ownerAmbiente':'2'}),dict(self.capabilities,scopes=[])]:
            with patch.object(type(self.connection),'_request',return_value=data):
                self.connection.action_verify()
            self.assertFalse(self.connection.verified)
        with self.assertRaises(ValidationError): self.job()
        with self.assertRaises(ValidationError): self.connection.write({'verified':True})

    def test_authorization_validation_and_foreign_reference(self):
        job=self.job()
        for changes in [{'externalReference':'otra'},{'idempotencyKey':'otra'},{'claveAcceso':'0'*23+'2'+'0'*25},{'rawStatus':'PENDIENTE_FIRMA'},{'facturaId':None},{'xmlUrl':'https://otro.example/secret'}]:
            with self.assertRaises(ProtocolError): job._apply(self.result(job,'invoice_authorized',**changes))
            self.assertEqual(job.state,'queued')
        job._apply(self.result(job,'invoice_authorized',xmlUrl=self.connection.base_url+'/documento.xml',rideUrl=self.connection.base_url+'/documento.pdf'))
        self.assertEqual(job.state,'authorized')
        with self.assertRaises(ProtocolError): job._apply(self.result(job))
        self.assertEqual(job.state,'authorized')

    def test_attempt_limit_and_resume_same_payload(self):
        job=self.job(); original=job.payload
        with patch.object(type(self.connection),'_capabilities',side_effect=ProtocolError('CONEXION_NO_CONFIRMADA',True)):
            for index in range(5):
                job._save(next_attempt=False); job.action_process()
        job._save(next_attempt=False); job.action_process()
        self.assertEqual(job.state,'blocked'); self.assertEqual(job.attempts,5)
        job.action_resume()
        self.assertEqual(job.state,'queued'); self.assertEqual(job.attempts,0)
        self.assertEqual(job.payload,original)

    def test_transport_credentials_redirects_and_errors(self):
        target='odoo.addons.erpec_fiscal_connector.connector.requests.request'
        with patch(target,return_value=Mock(status_code=200,json=lambda:{'success':True,'data':self.capabilities})) as request:
            self.connection._capabilities('corr-sintetica')
            self.assertFalse(request.call_args.kwargs['allow_redirects'])
            self.assertEqual(request.call_args.kwargs['headers']['Authorization'],'Bearer sk_test_sintetica_sin_validez')
        for status in (301,401,403,500):
            with patch(target,return_value=Mock(status_code=status)), self.assertRaises(ProtocolError):
                self.connection._request('POST','/api/integrations/v1/invoices','corr')
        self.connection.api_key='sk_live_no_utilizar'
        with patch(target) as request, self.assertRaises(ProtocolError):
            self.connection._request('GET','/api/integrations/v1/capabilities','corr')
        request.assert_not_called()

    def test_company_isolation_and_secret_access(self):
        job=self.job()
        other=self.env['res.company'].create({'name':'Empresa ajena sintética'})
        user=self.env['res.users'].with_context(no_reset_password=True).create({'name':'Contable ajeno','login':'contable-fiscal-ajeno','company_id':other.id,'company_ids':[(6,0,other.ids)],'groups_id':[(6,0,[self.env.ref('account.group_account_user').id])]})
        with self.assertRaises(AccessError): job.with_user(user).action_process()
        with self.assertRaises(AccessError): self.connection.with_user(user).read(['api_key'])
        with self.assertRaises(ValidationError): self.connection.write({'empresa_ref':99})
        self.assertIn('ec_fiscal_job_ids',self.move.get_view(view_type='form')['arch'])
        workspace=self.env['erpec.workspace'].search([],limit=1)
        self.assertIn('Conector de pruebas instalado',workspace.fiscal_scope)

    def test_unsupported_tax_blocks_queue(self):
        self.tax.tax_group_id.l10n_ec_type='exempt_vat'
        with self.assertRaises(ValidationError): self.job()
        self.assertFalse(self.move.ec_fiscal_job_ids)
