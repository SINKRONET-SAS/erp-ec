"""Autoservicio: casos sintéticos, no contactan PayPhone ni crean cargos externos."""
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged
from odoo.addons.erpec_payphone.models.payphone import Provider

SIGNUP_VALUES = {
    'company_name': 'Cliente de autoservicio S.A.S.', 'company_vat': '1793235327001',
    'company_regime': 'general', 'street': 'Av. Siempre Viva 123',
    'contact_name': 'Persona de contacto', 'contact_email': 'contacto@ejemplo.com',
    'contact_phone': '0999999999',
}


class TestSelfserviceRequest(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(user=self.env.ref('base.user_admin'), su=False,
                            context=dict(self.env.context, allowed_company_ids=[self.env.company.id], no_reset_password=True))
        self.plan = self.env['erpec.plan'].create({
            'name': 'Plan autoservicio', 'code': 'SS-TEST', 'erp': True,
            'terms': 'Plan sintético para pruebas de autoservicio', 'price': 49.0, 'published': True,
        })
        self.unpublished_plan = self.env['erpec.plan'].create({
            'name': 'Plan sin publicar', 'code': 'SS-DRAFT', 'erp': True,
            'terms': 'No debe aparecer en el autoservicio', 'price': 10.0,
        })
        self.provider = self.env['erpec.payphone.provider'].create({
            'company_id': self.env.company.id, 'token': 'TOKEN-SINTETICO', 'store_id': 'STORE-SINTETICO',
            'test_acknowledged': True, 'public_url': 'https://pruebas.sinkronet.com.ec',
        })

    def _prepare_response(self):
        return {'paymentId': 1, 'payWithPayPhone': 'https://pay.payphonetodoesposible.com/pay/test'}

    def test_signup_creates_subscription_and_prepares_payment(self):
        with patch.object(Provider, '_request', return_value=self._prepare_response()), \
                patch.object(self.env.cr, 'commit', return_value=None):
            signup_request = self.env['erpec.selfservice.request'].create_from_signup(
                dict(SIGNUP_VALUES, plan_id=self.plan.id))
        self.assertEqual(signup_request.state, 'awaiting_payment')
        self.assertTrue(signup_request.subscription_id)
        self.assertEqual(signup_request.subscription_id.plan_id, self.plan)
        self.assertEqual(signup_request.subscription_id.billing_owner, 'payphone_test')
        self.assertFalse(signup_request.subscription_id.activated_at)
        self.assertEqual(signup_request.payment_id.state, 'queued')
        self.assertEqual(signup_request.payment_id.amount, self.plan.price)

    def test_unpublished_plan_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['erpec.selfservice.request'].create_from_signup(
                dict(SIGNUP_VALUES, plan_id=self.unpublished_plan.id))

    def test_invalid_vat_is_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.selfservice.request'].create(dict(SIGNUP_VALUES, company_vat='123', plan_id=self.plan.id))

    def test_invalid_email_is_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.selfservice.request'].create(dict(SIGNUP_VALUES, contact_email='no-es-correo', plan_id=self.plan.id))

    def test_missing_provider_raises_user_error(self):
        other_company = self.env['res.company'].create({'name': 'Empresa sin PayPhone configurado'})
        with self.assertRaises(UserError):
            self.env['erpec.selfservice.request'].with_company(other_company).create_from_signup(
                dict(SIGNUP_VALUES, plan_id=self.plan.id))

    def test_no_public_orm_access(self):
        user = new_test_user(self.env, login='selfservice_public_test', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['erpec.selfservice.request'].with_user(user).search([])
        with self.assertRaises(AccessError):
            self.env['erpec.selfservice.request'].with_user(user).create(dict(SIGNUP_VALUES, plan_id=self.plan.id))

    def test_extra_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['erpec.selfservice.request'].create_from_signup(
                dict(SIGNUP_VALUES, plan_id=self.plan.id, state='provisioned'))

    def test_full_chain_to_provision_job(self):
        with patch.object(Provider, '_request', return_value=self._prepare_response()), \
                patch.object(self.env.cr, 'commit', return_value=None):
            signup_request = self.env['erpec.selfservice.request'].create_from_signup(
                dict(SIGNUP_VALUES, plan_id=self.plan.id))
            self.env['erpec.payphone.payment']._cron_process()
        payment = signup_request.payment_id
        confirmation = {'transactionId': 999, 'clientTransactionId': payment.reference,
                        'amount': int(round(self.plan.price * 100)), 'currency': 'USD', 'statusCode': 3}
        with patch.object(Provider, '_request', return_value=confirmation):
            payment._receive_return('999')
        self.assertEqual(payment.state, 'approved')
        payment._reconcile()
        self.assertTrue(signup_request.subscription_id.activated_at)
        self.assertEqual(self.env['erpec.provision'].search_count(
            [('subscription_id', '=', signup_request.subscription_id.id)]), 1)


@tagged('post_install', '-at_install')
class TestSelfserviceHttp(HttpCase):
    def test_landing_lists_only_published_plans(self):
        published = self.env['erpec.plan'].sudo().create({
            'name': 'Plan público HTTP', 'code': 'SS-HTTP-PUB', 'erp': True,
            'terms': 'Sintético', 'price': 25.0, 'published': True, 'fiscal_reviewed': True,
            'option_ids': [(0,0,{'capability_id':self.env.ref('erpec_suite.capability_assets').id})],
        })
        hidden = self.env['erpec.plan'].sudo().create({
            'name': 'Plan oculto HTTP', 'code': 'SS-HTTP-HIDDEN', 'erp': True,
            'terms': 'Sintético', 'price': 25.0,
        })
        response = self.url_open('/autoservicio')
        self.assertEqual(response.status_code, 200)
        self.assertIn(published.name, response.text)
        self.assertNotIn(hidden.name, response.text)

    def test_signup_without_csrf_token_is_rejected(self):
        # Odoo rechaza un POST sin csrf_token con 400 (no 403); confirma que la protección está activa.
        self.authenticate('admin','admin')
        response = self.url_open('/autoservicio/solicitar', data={'company_vat': '1793235327001'})
        self.assertEqual(response.status_code, 400)
