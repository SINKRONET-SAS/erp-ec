"""Casos sintéticos: no contactan PayPhone ni crean cargos externos."""
from datetime import timedelta
from unittest.mock import patch
import requests
from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user
from odoo.addons.erpec_payphone.models.payphone import MAX_AMOUNT_CENTS, Provider, cents

class TestPayphone(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(user=self.env.ref('base.user_admin'), su=False,
                            context=dict(self.env.context, allowed_company_ids=[self.env.company.id], no_reset_password=True))
        self.plan = self.env['erpec.plan'].create({'name': 'Plan ensayo PayPhone', 'code': 'PP-TEST', 'erp': True, 'terms': 'Ensayo sintético, sin servicio productivo'})
        self.contract = self.env['erpec.subscription'].create({'name': 'Ensayo PayPhone', 'plan_id': self.plan.id,
            'ends_on': fields.Date.today() + timedelta(days=10), 'billing_owner': 'payphone_test',
            'billing_reference': 'PayPhone de pruebas', 'authorization': 'Caso sintético'})
        self.provider = self.env['erpec.payphone.provider'].create({'company_id': self.env.company.id,
            'token': 'TOKEN-SINTETICO-NO-VALIDO', 'store_id': 'STORE-SINTETICO', 'test_acknowledged': True,
            'public_url': 'https://pruebas.sinkronet.com.ec'})
        self.payment = self.env['erpec.payphone.payment'].create({'subscription_id': self.contract.id,
            'provider_id': self.provider.id, 'amount_without_tax': 1.0})

    def prepared(self):
        self.payment.action_prepare()
        response = {'paymentId': 123, 'payWithPayPhone': 'https://pay.payphonetodoesposible.com/pay/test'}
        with patch.object(Provider, '_request', return_value=response) as call:
            self.payment._prepare()
            payload = call.call_args.args[1]
            self.assertEqual(payload['amount'], 100)
            self.assertEqual(payload['responseUrl'], 'https://pruebas.sinkronet.com.ec/payment/payphone/return')
        return self.payment

    def confirmation(self, **values):
        return dict({'transactionId': 123, 'clientTransactionId': self.payment.reference,
                    'amount': 100, 'currency': 'USD', 'statusCode': 3}, **values)

    def test_server_confirmation_and_duplicate_provision(self):
        payment = self.prepared()
        with patch.object(Provider, '_request', return_value=self.confirmation()) as call:
            payment._receive_return('123')
            payment._receive_return('123')
            self.assertEqual(call.call_count, 1)
        self.assertEqual(payment.state, 'approved')
        self.assertFalse(self.contract.activated_at)
        payment._reconcile()
        payment._reconcile()
        self.assertTrue(payment.reconciled)
        self.assertTrue(self.contract.activated_at)
        self.assertEqual(self.env['erpec.provision'].search_count([('subscription_id', '=', self.contract.id)]), 1)

    def test_browser_and_rpc_cannot_approve(self):
        with self.assertRaises(ValidationError):
            self.contract.action_activate()
        with self.assertRaises(AccessError):
            self.payment.write({'state': 'approved', 'remote_id': '123'})
        with self.assertRaises(AccessError):
            self.payment.write({'reconciled': True})
        with self.assertRaises(ValidationError):
            self.payment._receive_return('123')
        self.assertFalse(self.contract.activated_at)

    def test_mismatched_amount_currency_reference_and_id(self):
        self.prepared()
        for key, value in [('amount', 101), ('currency', 'EUR'), ('clientTransactionId', 'wrong'), ('transactionId', 999), ('statusCode', True)]:
            data = self.confirmation()
            data[key] = value
            with patch.object(Provider, '_request', return_value=data):
                self.payment._receive_return('123')
            self.assertNotEqual(self.payment.state, 'approved')
            self.assertFalse(self.contract.activated_at)
        self.assertEqual(self.payment.state, 'review')

    def test_cancel_does_not_activate(self):
        self.prepared()
        with patch.object(Provider, '_request', return_value=self.confirmation(statusCode=2)):
            self.payment._receive_return('123')
        self.payment._reconcile()
        self.assertEqual(self.payment.state, 'canceled')
        self.assertFalse(self.contract.activated_at)

    def test_timeout_then_confirmation_recovers(self):
        self.prepared()
        with patch.object(Provider, '_request', side_effect=ValidationError('PAYPHONE_CONNECTION')):
            self.payment._receive_return('123')
        self.assertEqual(self.payment.state, 'confirming')
        self.assertEqual(self.payment.pending_remote_id, '123')
        with patch.object(Provider, '_request', return_value=self.confirmation()):
            self.payment._try_confirm()
        self.assertEqual(self.payment.state, 'approved')

    def test_changed_contract_blocks_reconciliation(self):
        self.prepared()
        self.contract.write({'authorization': 'Condiciones posteriores distintas'})
        with patch.object(Provider, '_request', return_value=self.confirmation()):
            self.payment._receive_return('123')
        with self.assertRaises(ValidationError):
            self.payment._reconcile()
        self.assertFalse(self.contract.activated_at)

    def test_credentials_frozen_and_amount_immutable(self):
        self.prepared()
        with self.assertRaises(ValidationError):
            self.provider.write({'token': 'OTRO-TOKEN-SINTETICO'})
        with self.assertRaises(ValidationError):
            self.payment.write({'amount_without_tax': 2})
        with self.assertRaises(ValidationError):
            self.payment.action_prepare()

    def test_permissions_and_organization(self):
        user = new_test_user(self.env, login='payphone_employee', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.provider.with_user(user).read(['token'])
        with self.assertRaises(AccessError):
            self.payment.with_user(user).read(['amount'])
        other = self.env['res.company'].create({'name': 'Otra organización sintética'})
        foreign = self.env['erpec.payphone.provider'].sudo().create({'company_id': other.id,
            'public_url': 'https://otra-organizacion-sintetica.example.com'})
        with self.assertRaises(AccessError):
            foreign.with_user(self.env.user).read(['name'])

    def test_amount_cap_is_a_safety_ceiling_not_a_test_limit(self):
        big = self.contract.copy({'name': 'Contrato de monto alto'})
        payment = self.env['erpec.payphone.payment'].create({'subscription_id': big.id,
            'provider_id': self.provider.id, 'amount_without_tax': 5000.0})
        self.assertEqual(payment.amount, 5000.0)
        too_big = self.contract.copy({'name': 'Contrato sobre el techo de seguridad'})
        with self.assertRaises(ValidationError):
            self.env['erpec.payphone.payment'].create({'subscription_id': too_big.id,
                'provider_id': self.provider.id, 'amount_without_tax': MAX_AMOUNT_CENTS / 100 + 1})

    def test_cents_and_provider_validation(self):
        self.assertEqual(cents(1.15), 115)
        for amount in (-1, 1.001, float('nan')):
            with self.assertRaises(ValidationError):
                cents(amount)
        with patch('odoo.addons.erpec_payphone.models.payphone.requests.post', side_effect=requests.Timeout):
            with self.assertRaises(ValidationError):
                self.provider._request('Prepare', {})
        with patch('odoo.addons.erpec_payphone.models.payphone.requests.post') as post:
            post.return_value.status_code = 200
            post.return_value.json.return_value = {'errorCode': 20, 'message': 'No existe'}
            with self.assertRaises(ValidationError):
                self.provider._request('V2/Confirm', {})

    def test_invalid_checkout_is_rejected(self):
        self.payment.action_prepare()
        with patch.object(Provider, '_request', return_value={'paymentId': 1, 'payWithPayPhone': 'https://example.org/fake'}):
            with self.assertRaises(ValidationError):
                self.payment._prepare()

    def test_queue_timeout_does_not_repeat_prepare(self):
        self.payment.action_prepare()
        with patch.object(Provider, '_request', side_effect=ValidationError('PAYPHONE_CONNECTION')) as call:
            with patch.object(self.env.cr, 'commit', return_value=None):
                self.env['erpec.payphone.payment']._cron_process()
                self.env['erpec.payphone.payment']._cron_process()
            self.assertEqual(call.call_count, 1)
        self.payment.invalidate_recordset()
        self.assertEqual(self.payment.state, 'review')
        self.assertFalse(self.contract.activated_at)

    def test_queue_confirmation_and_reconciliation(self):
        self.prepared()
        self.payment._update({'state': 'confirming', 'pending_remote_id': '123'})
        with patch.object(Provider, '_request', return_value=self.confirmation()) as call:
            with patch.object(self.env.cr, 'commit', return_value=None):
                self.env['erpec.payphone.payment']._cron_process()
                self.env['erpec.payphone.payment']._cron_process()
                self.env['erpec.payphone.payment']._cron_process()
            self.assertEqual(call.call_count, 1)
        self.payment.invalidate_recordset()
        self.assertTrue(self.payment.reconciled)

    def test_payment_form_can_be_saved(self):
        from odoo.tests import Form
        contract = self.contract.copy({'name': 'Segundo ensayo de formulario'})
        with Form(self.env['erpec.payphone.payment']) as form:
            form.subscription_id = contract
            form.provider_id = self.provider
            form.amount_without_tax = 1.0
        self.assertEqual(form.record.amount, 1.0)


    def test_rejected_credentials_allow_correction(self):
        from odoo.addons.erpec_payphone.models.payphone import ConfigurationError
        self.payment.action_prepare()
        with patch.object(Provider, '_request', side_effect=ConfigurationError('Credenciales rechazadas')):
            with patch.object(self.env.cr, 'commit', return_value=None):
                self.env['erpec.payphone.payment']._cron_process()
        self.payment.invalidate_recordset()
        self.assertEqual(self.payment.state, 'draft')
        self.provider.write({'token': 'CREDENCIAL-SINTETICA-CORREGIDA'})


    def test_contract_change_before_prepare_never_calls_provider(self):
        self.payment.action_prepare()
        self.contract.write({'authorization': 'Condiciones modificadas antes de preparar'})
        with patch.object(Provider, '_request') as call:
            with self.assertRaises(ValidationError):
                self.payment._prepare()
            call.assert_not_called()

    def test_provider_cannot_move_organization_after_payment(self):
        other = self.env['res.company'].create({'name': 'Organización de ensayo separada'})
        with self.assertRaises(ValidationError):
            self.provider.write({'company_id': other.id})


from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestPayphoneHttp(HttpCase):
    def test_checkout_link_is_reachable_without_login(self):
        # El autoservicio redirige aquí a un visitante anónimo; debe responder sin exigir sesión.
        response = self.url_open('/payment/payphone/checkout/' + 'a' * 32)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('/web/login', response.url)

    def test_public_return_does_not_accept_forged_payment(self):
        response = self.url_open('/payment/payphone/return')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Faltan', response.text)
        response = self.url_open('/payment/payphone/return?id=123&clientTransactionId=' + 'a' * 32)
        self.assertEqual(response.status_code, 404)
        response = self.url_open('/payment/payphone/return?id=bad&clientTransactionId=<script>')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('<script>', response.text)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_queued_checkout_has_waiting_state(self):
        plan=self.env['erpec.plan'].sudo().create({'name':'Cola HTTP','code':'CM28-QUEUE-HTTP','erp':True,'terms':'Ensayo'})
        contract=self.env['erpec.subscription'].sudo().create({'name':'Cola HTTP','plan_id':plan.id,'ends_on':'2099-01-01','billing_owner':'payphone_test','billing_reference':'Ensayo','authorization':'Ensayo'})
        provider=self.env['erpec.payphone.provider'].sudo().create({'company_id':self.env.company.id,'public_url':'https://example.invalid'})
        payment=self.env['erpec.payphone.payment'].sudo().create({'subscription_id':contract.id,'provider_id':provider.id,'amount_without_tax':1})
        payment._update({'state':'queued'})
        response=self.url_open('/payment/payphone/checkout/'+payment.reference)
        self.assertEqual(response.status_code,202)
        self.assertIn('Preparando el pago',response.text)
        self.assertNotIn('Contraseña',response.text)
