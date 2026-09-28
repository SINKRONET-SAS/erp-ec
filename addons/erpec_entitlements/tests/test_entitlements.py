"""Derechos aplicados por servidor, incluyendo RPC/ORM y cupos de usuarios."""
from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged

@tagged('post_install','-at_install')
class TestEntitlements(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env=self.env(context=dict(self.env.context,no_reset_password=True))
        self.used=self.env['res.users'].search_count([('active','=',True),('share','=',False),('id','!=',1)])
        self.snapshot={'schema':1,'users':self.used+1,'max_companies':1,'capabilities':[],'modules':[]}

    def sync(self,**values):
        snapshot=dict(self.snapshot,**values)
        return self.env['erpec.tenant.entitlement']._sync('cliente-sintetico','revision-ensayo',snapshot,'2099-01-01')

    def test_internal_user_quantity_excludes_portal(self):
        rights=self.sync()
        new_test_user(self.env,login='cm28_internal',groups='base.group_user')
        new_test_user(self.env,login='cm28_portal',groups='base.group_portal')
        with self.assertRaises(AccessError),self.cr.savepoint():
            new_test_user(self.env,login='cm28_over_limit',groups='base.group_user')
        rights.invalidate_recordset()
        self.assertEqual(rights.active_users,self.used+1)

    def test_cannot_rewrite_rights_or_add_companies(self):
        rights=self.sync()
        with self.assertRaises(AccessError):rights.write({'snapshot':{'users':999}})
        with self.assertRaises(AccessError),self.cr.savepoint():self.env['res.company'].create({'name':'No contratada'})
        with self.assertRaises(ValidationError):self.env['erpec.tenant.entitlement']._sync('otro-cliente','x',self.snapshot,'2099-01-01')

    def test_removed_module_is_readonly_and_never_bought_is_denied(self):
        if 'erpec.asset' not in self.env:
            self.skipTest('Este caso requiere ejecutar la suite junto con erpec_assets.')
        self.sync()
        with self.assertRaises(AccessError):self.env['erpec.asset'].search([])
        self.sync(capabilities=['assets'])
        self.env['erpec.asset'].search([])
        self.sync(capabilities=[])
        self.env['erpec.asset'].search([])
        with self.assertRaises(AccessError):self.env['erpec.asset'].create({'name':'Sin derecho de alta'})

    def test_active_users_must_fit_downgrade(self):
        self.sync()
        new_test_user(self.env,login='cm28_last_seat',groups='base.group_user')
        with self.assertRaises(ValidationError):self.sync(users=self.used)
        self.assertEqual(self.env['erpec.tenant.entitlement'].search([]).snapshot['users'],self.used+1)

    def test_reactivation_and_portal_promotion_consume_seats(self):
        inactive=new_test_user(self.env,login='cm28_inactive',groups='base.group_user',active=False)
        portal=new_test_user(self.env,login='cm28_promotion',groups='base.group_portal')
        self.sync(users=self.used)
        with self.assertRaises(AccessError),self.cr.savepoint():inactive.write({'active':True})
        with self.assertRaises(AccessError),self.cr.savepoint():portal.write({'groups_id':[Command.set(self.env.ref('base.group_user').ids)]})
        with self.assertRaises(AccessError):self.env.ref('base.user_root').write({'password':'NO-VALIDA-ENSAYO'})

    def test_activation_token_expires_and_is_invalidated_after_use(self):
        user=new_test_user(self.env,login='cm28_token',groups='base.group_user')
        partner=user.partner_id
        partner.signup_prepare('reset')
        token=partner._generate_signup_token(expiration=4)
        self.assertEqual(partner._get_partner_from_token(token),partner)
        expired=partner._generate_signup_token(expiration=-1)
        self.assertFalse(partner._get_partner_from_token(expired))
        partner.signup_cancel()
        self.assertFalse(partner._get_partner_from_token(token))

    def test_group_membership_cannot_bypass_user_quota(self):
        user=new_test_user(self.env,login='cm28_group_promotion',groups='base.group_portal')
        self.sync(users=self.used)
        with self.assertRaises(AccessError),self.cr.savepoint():
            self.env.ref('base.group_portal').write({'users':[Command.unlink(user.id)]})
            self.env.ref('base.group_user').write({'users':[Command.link(user.id)]})
