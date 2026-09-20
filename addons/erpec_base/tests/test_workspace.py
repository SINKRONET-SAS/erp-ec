"""Estado de implementación por empresa: unicidad, valores por defecto y permisos."""
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger


class TestWorkspace(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Empresa sintética base'})

    def test_defaults_do_not_claim_integration(self):
        workspace = self.env['erpec.workspace'].create({'company_id': self.company.id})
        self.assertEqual(workspace.integration_status, 'pending')
        self.assertIn('no acredita autorización fiscal', workspace.next_action)
        self.assertEqual(workspace.name, 'ERP EC')

    def test_one_workspace_per_company(self):
        self.env['erpec.workspace'].create({'company_id': self.company.id})
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.cr.savepoint():
            self.env['erpec.workspace'].create({'company_id': self.company.id})

    def test_only_system_administrators_can_access(self):
        self.env['erpec.workspace'].create({'company_id': self.company.id})
        user = new_test_user(self.env, login='usuario-sin-workspace', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['erpec.workspace'].with_user(user).search([])

    def test_administrators_cannot_delete(self):
        workspace = self.env['erpec.workspace'].create({'company_id': self.company.id})
        admin = new_test_user(self.env, login='admin-workspace', groups='base.group_system')
        with self.assertRaises(AccessError):
            workspace.with_user(admin).unlink()
