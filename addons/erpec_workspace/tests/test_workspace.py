from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class WorkspaceCase(TransactionCase):
    def test_home_persisted_and_idempotent(self):
        first = self.env['erpec.workspace'].action_home()
        self.assertEqual(first['res_id'], self.env['erpec.workspace'].action_home()['res_id'])
        self.assertEqual(first['target'], 'main')
        self.assertEqual(first['id'], self.env.ref('erpec_workspace.home_window').id)
        self.assertNotIn('create', first['context'])
        self.assertNotIn('edit', first['context'])
        self.assertTrue(self.env['erpec.workspace'].browse(first['res_id']).exists())

    def test_company_switch(self):
        company = self.env['res.company'].create({'name': 'Empresa ensayo navegación'})
        first = self.env['erpec.workspace'].action_home()
        second = self.env['erpec.workspace'].with_company(company).action_home()
        self.assertNotEqual(first['res_id'], second['res_id'])
        self.assertEqual(self.env['erpec.workspace'].browse(second['res_id']).company_id, company)

    def test_internal_read_does_not_grant_operations(self):
        user = self.env['res.users'].create({'name': 'Consulta ensayo', 'login': 'workspace_test_reader',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]})
        model = self.env['erpec.workspace'].with_user(user)
        action = self.env.ref('erpec_workspace.home_action').with_user(user).run()
        record = model.browse(action['res_id'])
        self.assertTrue(record.read(['company_id']))
        with self.assertRaises(AccessError):
            record.write({'name': 'No permitido'})
        with self.assertRaises(AccessError):
            record.with_context(erpec_area='payroll').action_area()

    def test_area_and_view(self):
        action = self.env['erpec.workspace'].action_home()
        record = self.env['erpec.workspace'].browse(action['res_id'])
        self.assertEqual(record.with_context(erpec_area='invoices').action_area()['res_model'], 'account.move')
        with self.assertRaises(AccessError):
            record.with_context(erpec_area='unknown').action_area()
        arch = record.get_view(view_id=action['views'][0][0], view_type='form')['arch']
        self.assertIn('edit="false"', arch)
        self.assertIn('company_readiness', arch)

    def test_portal_cannot_open(self):
        user = self.env['res.users'].create({'name': 'Portal ensayo', 'login': 'workspace_test_portal',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]})
        with self.assertRaises(AccessError):
            self.env['erpec.workspace'].with_user(user).action_home()
        with self.assertRaises(AccessError):
            self.env.ref('erpec_workspace.home_action').with_user(user).run()
