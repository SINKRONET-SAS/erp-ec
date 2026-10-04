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
            self.assertIn('erpec_selfservice.home_content', view.arch_db)
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

    def test_public_site_defaults_to_spanish_ecuador(self):
        # DI26-14: el sitio quedaba en inglés (en-US) aunque la empresa opera en Ecuador.
        self.env['res.lang']._activate_lang('es_EC')
        website = self.env['website'].search([], limit=1)
        website.default_lang_id = self.env['res.lang']._lang_get('en_US')
        self.env['website']._erpec_apply_entry_language()
        self.assertEqual(website.default_lang_id.code, 'es_EC')
        self.assertIn('es_EC', website.language_ids.mapped('code'))

    def test_custom_home_is_preserved(self):
        home=self.View.search([('key','=','website.homepage')],limit=1)
        home.arch_db='<t name="Inicio" t-name="website.homepage"><t t-call="website.layout"><div id="wrap" class="oe_structure"><h1>Portada propia de mi empresa</h1></div></t></t>'
        before=home.arch_db
        self.env['website']._erpec_apply_entry_branding()
        self.assertEqual(home.arch_db,before)

    def test_legacy_footer_brand_is_migrated_without_replacing_content(self):
        footer = self.View.search([('key', '=', 'website.footer_custom')], limit=1)
        footer.arch_db = footer.arch_db.replace('SINKRONET</p>', 'SINKRONET · Tecnología Odoo Community</p>')
        self.env['website']._erpec_apply_entry_branding()
        self.assertNotIn('Tecnología Odoo Community', footer.arch_db)
        self.assertIn('/derechos-datos', footer.arch_db)
