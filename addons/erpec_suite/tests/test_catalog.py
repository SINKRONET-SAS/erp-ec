"""Precios por periodo, módulos y usuarios; condiciones contractuales inmutables."""
from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from .test_commercial import TestCommercial

class TestCatalog(TestCommercial):
    def offer(self):
        return self.env['erpec.plan'].create({'name':'Oferta sintética','code':'CM28-QUOTE','erp':True,'terms':'Ensayo',
            'price':40,'annual_enabled':True,'annual_price':400,'max_users':2,'user_limit':10,
            'additional_user_price':8,'additional_user_annual_price':80})

    def test_users_and_options_in_monthly_and_annual_quotes(self):
        plan=self.offer()
        option=self.env['erpec.plan.option'].create({'plan_id':plan.id,'capability_id':self.env.ref('erpec_suite.capability_payroll').id,
            'kind':'optional','monthly_price':12,'annual_price':120})
        monthly=plan._quote('monthly',5,[option.id])
        annual=plan._quote('annual',5,[option.id])
        self.assertEqual(monthly['total'],76)
        self.assertEqual(annual['total'],760)
        self.assertEqual(monthly['additional_users'],3)
        self.assertEqual(monthly['capabilities'],['payroll'])
        with self.assertRaises(ValidationError): plan._quote('monthly',11,[])
        with self.assertRaises(ValidationError): plan._quote('monthly',True,[])
        with self.assertRaises(ValidationError): plan._quote('monthly',2,[option.id,option.id])

    def test_freeze_users_and_unpublish_used_offer(self):
        plan=self.offer()
        plan.published=True
        contract=self.contract(plan_id=plan.id,user_quantity=4)
        contract.action_activate()
        self.assertEqual(contract.commercial_snapshot['total'],56)
        self.assertTrue(contract.check_capacity('users',4))
        with self.assertRaises(AccessError): contract.check_capacity('users',5)
        plan.published=False
        self.assertEqual(contract.commercial_snapshot['total'],56)
        with self.assertRaises(ValidationError): plan.write({'additional_user_price':99})
        with self.assertRaises(AccessError): contract.write({'commercial_snapshot':{}})
        version=self.env['erpec.plan'].browse(plan.action_new_version()['res_id'])
        self.assertFalse(version.published)

    def test_child_lines_cannot_modify_contracted_rights(self):
        plan=self.offer()
        line=self.env['erpec.plan.option'].create({'plan_id':plan.id,'capability_id':self.env.ref('erpec_suite.capability_sales').id})
        self.contract(plan_id=plan.id)
        with self.assertRaises(ValidationError): line.write({'kind':'optional'})
        with self.assertRaises(ValidationError): line.unlink()
        with self.assertRaises(ValidationError): self.env['erpec.plan.option'].create({'plan_id':plan.id,'capability_id':self.env.ref('erpec_suite.capability_inventory').id})

    def test_native_tax_computation(self):
        plan=self.offer()
        group=self.env['account.tax.group'].create({'name':'Grupo de ensayo','company_id':self.env.company.id})
        tax=self.env['account.tax'].create({'name':'Impuesto sintético 7%','amount':7,'tax_group_id':group.id,'country_id':self.env.ref('base.ec').id,'type_tax_use':'sale','company_id':self.env.company.id})
        plan.tax_ids=tax
        quote=plan._quote('monthly',3)
        self.assertAlmostEqual(quote['untaxed'],48)
        self.assertAlmostEqual(quote['tax'],3.36)
        self.assertAlmostEqual(quote['total'],51.36)

    def test_assets_is_available_as_optional_capability(self):
        plan=self.offer()
        option=self.env['erpec.plan.option'].create({'plan_id':plan.id,'capability_id':self.env.ref('erpec_suite.capability_assets').id,'kind':'optional','monthly_price':10})
        quote=plan._quote('monthly',2,[option.id])
        self.assertEqual(quote['modules'],['erpec_assets'])
        self.assertEqual(quote['total'],50)

    def test_manufacturing_requires_contracted_inventory(self):
        plan=self.offer()
        self.env['erpec.plan.option'].create({'plan_id':plan.id,'capability_id':self.env.ref('erpec_suite.capability_manufacturing').id})
        with self.assertRaisesRegex(ValidationError,'Inventario'):
            plan._quote()
        with self.assertRaisesRegex(ValidationError,'Inventario'),self.cr.savepoint():
            plan.published=True
        self.env['erpec.plan.option'].create({'plan_id':plan.id,'capability_id':self.env.ref('erpec_suite.capability_inventory').id})
        self.assertEqual(plan._quote()['capabilities'],['inventory','manufacturing'])
