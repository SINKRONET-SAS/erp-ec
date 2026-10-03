"""Regresión de accesos tributarios y marca en ajustes."""
from lxml import etree
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class NavigationSettingsCase(TransactionCase):
    def test_account_manager_sees_tax_application(self):
        user = self.env['res.users'].create({
            'name': 'Responsable tributario de prueba', 'login': 'navigation_tax_manager',
            'groups_id': [(6, 0, [self.env.ref('account.group_account_manager').id])],
        })
        visible = self.env['ir.ui.menu'].with_user(user)._visible_menu_ids()
        root = self.env.ref('erpec_workspace.tax_configuration_root')
        self.assertFalse(root.parent_id)
        for name in ['tax_configuration_root', 'tax_policy_menu', 'tax_detail_menu',
                     'tax_partner_class_menu', 'tax_item_class_menu']:
            self.assertIn(self.env.ref('erpec_workspace.' + name).id, visible)
        basic = self.env['res.users'].create({
            'name': 'Consulta sin contabilidad', 'login': 'navigation_basic',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.assertNotIn(root.id, self.env['ir.ui.menu'].with_user(basic)._visible_menu_ids())

    def test_class_actions_preserve_existing_model(self):
        for name, kind in [('tax_partner_class_action', 'partner'), ('tax_item_class_action', 'product')]:
            action = self.env.ref('erpec_workspace.' + name)
            self.assertEqual(action.res_model, 'erpec.tax.classification')
            self.assertIn(kind, action.domain)
            self.assertIn(kind, action.context)

    def test_settings_identity_and_credits(self):
        arch = self.env['res.config.settings'].get_view(view_type='form')['arch']
        tree = etree.fromstring(arch)
        self.assertFalse(tree.xpath("//widget[@name='mobile_apps_funnel' or @name='res_config_edition']"))
        self.assertTrue(tree.xpath("//div[contains(@class, 'erpec_product_about')]"))
        self.assertIn('GNU LGPL', arch)

    def test_footer_identity(self):
        rendered = self.env['ir.ui.view']._render_template('web.brand_promotion_message', {'_utm_medium': 'test', '_message': ''})
        self.assertIn('ERP EC', rendered)
        self.assertNotIn('odoo.com', rendered)
        self.assertNotIn('odoo_logo', rendered)
