from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class EntryCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.View = self.env['ir.ui.view'].with_context(lang='en_US', active_test=False)

    def test_template_identity_replaced_and_no_dead_links(self):
        self.assertNotEqual(self.env['website'].search([], limit=1).name, 'My Website')
        for view in self.View.search([('key', '=', 'website.homepage')]):
            self.assertNotIn('oe_empty', view.arch_db)
            self.assertIn('/web/login', view.arch_db)
        for view in self.View.search([('key', '=', 'website.footer_custom')]):
            self.assertNotIn('href="#"', view.arch_db)
            self.assertNotIn('YourCompany', view.arch_db)
            self.assertNotIn('Legal', view.arch_db)

    def test_placeholder_logo_replaced(self):
        website = self.env['website'].search([], limit=1)
        self.assertNotEqual(website.logo, website._default_logo())

    def test_copyright_placeholder_replaced(self):
        for view in self.View.search([('key', '=', 'website.footer_copyright_company_name')]):
            self.assertNotIn('Company name', view.arch_db)

    def test_idempotent_and_respects_customer_edits(self):
        footer = self.View.search([('key', '=', 'website.footer_custom')], limit=1)
        footer.arch_db = footer.arch_db.replace('ERP EC', 'Mi empresa propia')
        self.env['website']._erpec_apply_entry_branding()
        self.assertIn('Mi empresa propia', footer.arch_db)
