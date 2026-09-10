from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError, ValidationError

class TestCommercial(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(user=cls.env.ref('base.user_admin'), su=False, context=dict(cls.env.context, allowed_company_ids=[cls.env.company.id], no_reset_password=True))
        cls.today = fields.Date.today()
        cls.plan = cls.env['erpec.plan'].create({'name': 'Prueba suite', 'code': 'TEST', 'erp': True, 'payroll': True, 'api_access': True, 'terms': 'Datos sintéticos, sin cargo', 'max_connections': 2})

    def contract(self, **extra):
        values = {'name': 'Contrato de prueba', 'plan_id': self.plan.id, 'starts_on': self.today, 'ends_on': self.today + timedelta(days=30), 'billing_owner': 'existing', 'billing_reference': 'Contrato sintético anterior', 'authorization': 'Aprobación sintética'}
        values.update(extra)
        return self.env['erpec.subscription'].create(values)

    def test_activation_duplicate_and_limits(self):
        contract = self.contract()
        self.assertEqual(contract.state, 'draft')
        contract.action_activate()
        activated = contract.activated_at
        contract.action_activate()
        self.assertEqual(contract.activated_at, activated)
        self.assertEqual(contract.state, 'active')
        self.assertTrue(contract.check_capacity('connections', 2))
        with self.assertRaises(AccessError):
            contract.check_capacity('connections', 3)
        with self.assertRaises(AccessError):
            contract.write({'suspended': True})
        self.assertIs(contract.action_suspend(), True)
        with self.assertRaises(AccessError):
            contract.check_capacity('users', 1)
        self.assertIs(contract.action_resume(), True)
        self.assertEqual(contract.state, 'active')

    def test_expiry_future_and_product_api_separation(self):
        expired = self.contract(starts_on=self.today-timedelta(days=4), ends_on=self.today-timedelta(days=1))
        expired.action_activate()
        self.assertEqual(expired.state, 'expired')
        with self.assertRaises(AccessError):
            expired.check_capacity('users', 1)
        plan = self.plan.copy({'code': 'NOAPI', 'api_access': False})
        future = self.contract(name='Futuro', plan_id=plan.id, starts_on=self.today+timedelta(days=1))
        future.action_activate()
        self.assertEqual(future.state, 'future')
        future.action_suspend()
        current = self.contract(name='Actual', plan_id=plan.id)
        current.action_activate()
        self.assertIn('API no incluida', current.rights)
        with self.assertRaises(AccessError):
            current.check_capacity('connections', 1)

    def test_versions_and_explicit_migration(self):
        old = self.contract()
        old.action_activate()
        with self.assertRaises(ValidationError):
            self.plan.write({'max_connections': 10})
        result = self.plan.action_new_version()
        new_plan = self.env['erpec.plan'].browse(result['res_id'])
        new_plan.write({'max_connections': 3})
        new = self.contract(name='Sustitución explícita', plan_id=new_plan.id)
        with self.assertRaises(ValidationError):
            new.action_activate()
        old.action_suspend()
        new.action_activate()
        self.assertEqual(old.plan_id.version, 1)
        self.assertEqual(new.plan_id.version, 2)
        with self.assertRaises(ValidationError):
            old.action_resume()
        with self.assertRaises(ValidationError):
            new.write({'ends_on': self.today})

    def test_foreign_company_and_unprivileged_actions(self):
        contract = self.contract()
        other = self.env['res.company'].create({'name': 'Empresa ajena de prueba'})
        user = new_test_user(self.env, login='erpec-reader', groups='base.group_user', company_id=other.id, company_ids=[(6, 0, other.ids)])
        foreign = contract.with_user(user).with_context(allowed_company_ids=other.ids)
        with self.assertRaises(AccessError):
            foreign.read(['authorization'])
        with self.assertRaises(AccessError):
            foreign.action_activate()
        with self.assertRaises(AccessError):
            foreign.check_capacity('users', 1)
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.contract(name='Ajeno', company_id=other.id)

    def test_validation_and_link(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.plan.copy({'code': 'INVALID', 'max_connections': -1})
        contract = self.contract(authorization=' ')
        with self.assertRaises(ValidationError):
            contract.action_activate()
        with self.assertRaises(AccessError):
            self.contract(name='Estado falso', activated_at=fields.Datetime.now())
        link = self.env['erpec.product.link'].create({'product': 'payroll', 'external_id': 'tenant-sintetico-1', 'authorization': 'Autorización sintética'})
        self.assertEqual(link.status, 'pending')
