"""Recorrido HTTP de contratación y separación entre titulares; sin llamadas a PayPhone."""
from lxml import html
from odoo import Command
from odoo.tests.common import HttpCase,new_test_user,tagged
from .test_selfservice import SIGNUP_VALUES

@tagged('post_install','-at_install')
class TestCommercialPortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env=cls.env(context=dict(cls.env.context,no_reset_password=True))
        cls.owner=new_test_user(env,login='cm28_http_a',password='EnsayoCM28-local',groups='base.group_portal')
        cls.other=new_test_user(env,login='cm28_http_b',password='EnsayoCM28-local',groups='base.group_portal')
        cls.plan=env['erpec.plan'].create({'name':'Oferta protegida HTTP','code':'CM28-HTTP','erp':True,'terms':'Ensayo',
            'price':40,'max_users':2,'additional_user_price':8,'fiscal_reviewed':True,'published':True,
            'option_ids':[Command.create({'capability_id':env.ref('erpec_suite.capability_assets').id})]})
        env['erpec.payphone.provider'].create({'company_id':env.company.id,'token':'TOKEN-SINTETICO','store_id':'STORE-SINTETICO',
            'test_acknowledged':True,'public_url':'https://pruebas.sinkronet.com.ec'})
        cls.signup=env['erpec.selfservice.request']._create_signup(dict(SIGNUP_VALUES,plan_id=cls.plan.id),owner_user=cls.owner)

    def test_tracking_rejects_another_owner(self):
        self.authenticate('cm28_http_a','EnsayoCM28-local')
        response=self.url_open('/mi-servicio/alta/'+self.signup.reference)
        self.assertEqual(response.status_code,200)
        self.assertIn(self.signup.company_name,response.text)
        self.authenticate('cm28_http_b','EnsayoCM28-local')
        self.assertEqual(self.url_open('/mi-servicio/alta/'+self.signup.reference).status_code,404)
        self.assertEqual(self.url_open('/mi-servicio/cliente/'+self.signup.customer_id.reference+'/renovar').status_code,404)
        self.assertNotIn(self.signup.company_name,self.url_open('/mi-servicio').text)

    def test_quote_and_amount_tampering(self):
        self.authenticate('cm28_http_a','EnsayoCM28-local')
        response=self.url_open('/autoservicio/contratar?plan_id=%s&amp;user_quantity=3'.replace('&amp;','&') % self.plan.id)
        self.assertEqual(response.status_code,200)
        doc=html.fromstring(response.content)
        token=doc.xpath('//input[@name="csrf_token"]/@value')[0]
        values=dict(SIGNUP_VALUES,plan_id=self.plan.id,user_quantity=3,period='monthly',request_key='f'*32,csrf_token=token,amount='0.01')
        response=self.url_open('/autoservicio/solicitar',data=values)
        self.assertEqual(response.status_code,200)
        created=self.env['erpec.selfservice.request'].search([('request_key','=','f'*32)])
        self.assertEqual(created.payment_id.amount,48)
        self.assertEqual(created.customer_id.portal_user_id,self.owner)
        response=self.url_open('/autoservicio/solicitar',data=values)
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.env['erpec.selfservice.request'].search_count([('request_key','=','f'*32)]),1)

    def test_unreviewed_and_demo_offers_not_public(self):
        self.plan.published=False
        response=self.url_open('/autoservicio')
        self.assertEqual(response.status_code,200)
        self.assertNotIn(self.plan.name,response.text)
        self.assertIn('Estamos preparando las ofertas',response.text)

    def test_invalid_users_rejected_without_contract(self):
        self.authenticate('cm28_http_a','EnsayoCM28-local')
        response=self.url_open('/autoservicio/contratar?plan_id=%s&user_quantity=99999' % self.plan.id)
        self.assertEqual(response.status_code,400)
        self.assertIn('cantidad de usuarios',response.text)
