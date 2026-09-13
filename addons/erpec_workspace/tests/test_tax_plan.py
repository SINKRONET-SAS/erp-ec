from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError, UserError
from lxml import etree


@tagged('post_install', '-at_install')
class TaxPlanCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.account = self.env['account.account'].create({
            'name': 'Cuenta tributaria ensayo', 'code': 'TXSP0201',
            'account_type': 'liability_current', 'company_ids': [Command.set(self.company.ids)]})
        self.origin = self.env['account.tax'].create({'name': 'Origen sintético', 'amount': 10, 'type_tax_use': 'purchase'})
        self.target = self.env['account.tax'].create({'name': 'Destino sintético', 'amount': 5, 'type_tax_use': 'purchase'})
        (self.target.invoice_repartition_line_ids | self.target.refund_repartition_line_ids).filtered(
            lambda line: line.repartition_type == 'tax').account_id = self.account
        self.position = self.env['account.fiscal.position'].create({
            'name': 'Transformación de ensayo', 'company_id': self.company.id,
            'tax_ids': [Command.create({'tax_src_id': self.origin.id, 'tax_dest_id': self.target.id})]})
        self.partner = self.env['res.partner'].create({'name': 'Proveedor ensayo tributario',
                                                     'property_account_position_id': self.position.id})
        self.product = self.env['product.product'].create({
            'name': 'Artículo ensayo tributario', 'supplier_taxes_id': [Command.set(self.origin.ids)],
            'taxes_id': [Command.clear()]})
        self.plan = self.env['erpec.tax.plan'].create({
            'name': 'Compra de ensayo', 'product_id': self.product.id, 'partner_id': self.partner.id})

    def test_mapping_matches_purchase(self):
        self.assertEqual(self.plan.source_tax_ids, self.origin)
        self.assertEqual(self.plan.effective_tax_ids, self.target)
        self.assertEqual(self.plan.account_ids, self.account)
        self.assertIn('Factura', self.plan.detail)
        self.assertIn('Devolución', self.plan.detail)
        order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_qty': 1, 'price_unit': 100})]})
        self.assertEqual(order.order_line.taxes_id, self.plan.effective_tax_ids)
        for operation in ('bill', 'import'):
            self.plan.operation = operation
            self.assertEqual(self.plan.effective_tax_ids, self.target)
        self.plan.operation = 'sale'
        self.assertFalse(self.plan.effective_tax_ids)
        self.assertIn('No equivale a una exención', self.plan.detail)
        branch = self.env['res.company'].create({'name': 'Sucursal tributaria', 'parent_id': self.company.id})
        branch_plan = self.plan.with_company(branch).copy({'company_id': branch.id, 'operation': 'purchase'})
        self.assertEqual(branch_plan.source_tax_ids, self.origin)

    def test_group_tax_and_live_configuration(self):
        group = self.env['account.tax'].create({
            'name': 'Grupo de ensayo', 'amount_type': 'group', 'type_tax_use': 'purchase',
            'children_tax_ids': [Command.set(self.target.ids)]})
        self.position.tax_ids.tax_dest_id = group
        self.env.invalidate_all()
        self.assertEqual(self.plan.effective_tax_ids, group)
        self.assertEqual(self.plan.account_ids, self.account)
        self.assertIn('Destino sintético', self.plan.detail)
        self.position.tax_ids.tax_dest_id = False
        self.env.invalidate_all()
        self.assertFalse(self.plan.effective_tax_ids)
        self.assertIn('retira los impuestos', self.plan.detail)

    def test_missing_account_and_no_position(self):
        self.partner.property_account_position_id = False
        self.assertFalse(self.plan.fiscal_position_id)
        self.assertEqual(self.plan.effective_tax_ids, self.origin)
        self.assertIn('Sin cuenta explícita', self.plan.detail)
        self.assertIn('Sin posición fiscal', self.plan.detail)

    def test_permissions_and_company_isolation(self):
        user = self.env['res.users'].create({'name': 'Gestor plan', 'login': 'tax_plan_manager_test',
            'company_id': self.company.id, 'company_ids': [Command.set(self.company.ids)],
            'groups_id': [Command.set(self.env.ref('account.group_account_manager').ids)]})
        self.assertTrue(self.plan.with_user(user).read(['detail']))
        other = self.env['res.company'].create({'name': 'Otra empresa tributaria'})
        foreign = self.plan.with_company(other).copy({'company_id': other.id})
        with self.assertRaises(AccessError):
            foreign.with_user(user).read(['name'])
        reader = self.env['res.users'].create({'name': 'Sin acceso tributario', 'login': 'tax_plan_reader_test',
            'groups_id': [Command.set(self.env.ref('base.group_user').ids)]})
        with self.assertRaises(AccessError):
            self.plan.with_user(reader).read(['detail'])
        product = self.env['product.product'].with_company(other).create({'name': 'Artículo de otra empresa', 'company_id': other.id, 'taxes_id': [Command.clear()], 'supplier_taxes_id': [Command.clear()]})
        self.env.flush_all()
        with self.assertRaises(UserError):
            self.plan.write({'product_id': product.id})

    def test_navigation_and_native_journal_visible(self):
        self.assertEqual(self.plan.with_context(tax_plan_target='taxes').action_catalog()['res_model'], 'account.tax')
        self.assertEqual(self.plan.with_context(tax_plan_target='accounts').action_catalog()['res_model'], 'account.account')
        self.assertEqual(self.plan.with_context(tax_plan_target='positions').action_catalog()['res_model'], 'account.fiscal.position')
        with self.assertRaises(AccessError):
            self.plan.with_context(tax_plan_target='invalid').action_catalog()
        user = self.env['res.users'].create({'name': 'Gestor cuentas', 'login': 'tax_plan_account_view_test',
            'groups_id': [Command.set(self.env.ref('account.group_account_manager').ids)]})
        arch = self.env['account.move'].with_user(user).get_view(
            view_id=self.env.ref('account.view_move_form').id, view_type='form')['arch']
        self.assertTrue(etree.fromstring(arch).xpath("//page[@name='aml_tab']"))
        self.assertIn('name="detail"', self.plan.get_view(view_type='form')['arch'])
