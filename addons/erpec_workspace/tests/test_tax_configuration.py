"""Ensayos sintéticos de la cadena de configuración; no certifican normativa."""
from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged
from psycopg2 import IntegrityError


@tagged('post_install', '-at_install')
class TaxConfigurationCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({'country_id': self.env.ref('base.ec').id})
        self.reference = self.env['erpec.tax.reference'].create({
            'name': 'Referencia sintética, no normativa', 'family': 'ENSAYO',
            'code': 'TX-SP02', 'version': 'ensayo', 'source_url': 'https://www.sri.gob.ec/facturacion-electronica'})
        self.account = self.env['account.account'].create({'name': 'Cuenta caso ensayo', 'code': 'TXCASE01',
            'account_type': 'liability_current', 'company_ids': [Command.set(self.company.ids)]})
        # Grupo IVA explícito (l10n_ec_type='vat15'): sin él, account.tax.create() sin
        # tax_group_id asigna algún grupo por defecto del que no depende esta prueba pero del
        # que sí depende _retention_bases() (erpec_workspace/tax_intersection.py) para calcular
        # la base de la retención de IVA -- sin un grupo IVA real, esa base queda en cero.
        self.vat_group = self.env['account.tax.group'].create({'name': 'IVA sintético ensayo',
            'company_id': self.company.id, 'l10n_ec_type': 'vat15'})
        self.taxes = self.env['account.tax'].create([
            {'name': 'Detalle sintético A', 'amount': 10, 'type_tax_use': 'purchase',
             'tax_group_id': self.vat_group.id, 'erpec_reference_id': self.reference.id},
            {'name': 'Detalle sintético B', 'amount': 2, 'type_tax_use': 'purchase',
             'tax_group_id': self.vat_group.id, 'erpec_reference_id': self.reference.id}])
        for tax in self.taxes:
            (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
                lambda line: line.repartition_type == 'tax').account_id = self.account
        self.partner_type = self.env['erpec.tax.classification'].create({'name': 'Proveedor ensayo', 'kind': 'partner'})
        self.product_type = self.env['erpec.tax.classification'].create({'name': 'Producto ensayo', 'kind': 'product'})
        self.partner = self.env['res.partner'].create({'name': 'Tercero caso', 'erpec_tax_type_id': self.partner_type.id})
        self.product = self.env['product.product'].create({'name': 'Producto caso', 'erpec_tax_type_id': self.product_type.id,
            'supplier_taxes_id': [Command.clear()], 'taxes_id': [Command.clear()]})
        self.policy = self.env['erpec.tax.policy'].create({'name': 'Plan sintético'})
        self.case = self.env['erpec.tax.case'].create({'name': 'Caso combinado', 'policy_id': self.policy.id,
            'tax_ids': [Command.set(self.taxes.ids)]})
        self.values = {'case_id': self.case.id, 'partner_type_id': self.partner_type.id, 'product_type_id': self.product_type.id}
        self.assignment = self.env['erpec.tax.assignment'].create(self.values)

    def resolve(self):
        return self.env['erpec.tax.assignment']._resolve_case(self.company, 'purchase', self.partner, self.product)

    def test_case_groups_details_and_preserves_native_documents(self):
        case, message = self.resolve()
        self.assertEqual(case, self.case)
        self.assertEqual(case.tax_ids, self.taxes)
        self.assertEqual(self.reference.tax_ids, self.taxes)
        scenario = self.env['erpec.tax.plan'].create({'name': 'Comparación',
            'partner_id': self.partner.id, 'product_id': self.product.id})
        self.assertEqual(scenario.planned_tax_ids, self.taxes)
        self.assertEqual(scenario.planned_account_ids, self.account)
        self.assertIn('DIFERENCIA', scenario.case_status)
        order = self.env['purchase.order'].create({'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_qty': 1, 'price_unit': 100})]})
        self.assertFalse(order.order_line.taxes_id)
        self.assertFalse(self.product.supplier_taxes_id)
        self.assertEqual(self.taxes.compute_all(100)['total_included'], 112)
        self.assertEqual(self.taxes.invoice_repartition_line_ids.account_id, self.account)

    def test_duplicates_and_wrong_operations_rejected(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['erpec.tax.assignment'].create(self.values)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.assignment.operation = 'sale'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.assignment.product_type_id = self.partner_type
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.product.erpec_tax_type_id = self.partner_type

    def test_missing_mapping_and_archived_configuration_visible(self):
        case, message = self.env['erpec.tax.assignment']._resolve_case(self.company, 'sale', self.partner, self.product)
        self.assertFalse(case)
        self.assertIn('No existe', message)
        self.case.operation = 'sale'
        self.assertIn('ya no coincide', self.resolve()[1])
        self.case.operation = 'purchase'
        self.policy.active = False
        self.assertIn('archivado', self.resolve()[1])
        self.policy.active = True
        self.reference.active = False
        self.assertIn('referencia SRI', self.resolve()[1])
        self.reference.active = True
        self.partner_type.active = False
        self.assertIn('tipo archivado', self.resolve()[1])

    def test_missing_accounts_and_reference_rejected(self):
        self.taxes[0].refund_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').account_id = False
        self.assertIn('cuentas contables', self.resolve()[1])
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.assignment.write({'case_id': self.case.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.reference.source_url = 'https://sri.gob.ec.invalid/catalogo'

    def test_company_permissions_and_views(self):
        user = self.env['res.users'].create({'name': 'Sin configuración', 'login': 'txcase_noaccess',
            'groups_id': [Command.set(self.env.ref('base.group_user').ids)]})
        with self.assertRaises(AccessError):
            self.policy.with_user(user).read(['name'])
        other = self.env['res.company'].create({'name': 'Otra empresa casos'})
        case, message = self.env['erpec.tax.assignment'].with_company(other)._resolve_case(other, 'purchase', self.partner, self.product)
        self.assertFalse(case)
        self.assertIn('Falta clasificar', message)
        for model in ('reference', 'classification', 'policy', 'case', 'assignment'):
            self.assertTrue(self.env['erpec.tax.' + model].get_view(view_type='form')['arch'])

    def test_seeded_reference_codes_and_fiscal_position(self):
        references = self.env['erpec.tax.reference'].search([('family', '=', 'IVA · impuesto 2 · tabla 17')])
        self.assertEqual(set(references.mapped('code')), {'0', '2', '3', '4', '5', '6', '7', '8', '10'})
        position = self.env['account.fiscal.position'].create({'name': 'Retirar detalle sintético',
            'company_id': self.company.id,
            'tax_ids': [Command.create({'tax_src_id': self.taxes[0].id, 'tax_dest_id': False})]})
        self.partner.property_account_position_id = position
        scenario = self.env['erpec.tax.plan'].create({'name': 'Caso con posición',
            'partner_id': self.partner.id, 'product_id': self.product.id})
        self.assertEqual(scenario.planned_effective_tax_ids, self.taxes[1])

    def _retention(self, kind, code, amount):
        group = self.env['account.tax.group'].create({'name': 'Retención sintética ' + kind,
            'company_id': self.company.id, 'l10n_ec_type': 'withhold_' + kind + '_purchase'})
        tax = self.env['account.tax'].create({'name': 'Retención ensayo ' + code,
            'type_tax_use': 'none', 'amount': -amount, 'amount_type': 'percent',
            'tax_group_id': group.id,
            'erpec_reference_id': self.env.ref('erpec_workspace.sri_retention_' + kind + '_' + code).id})
        (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
            lambda line: line.repartition_type == 'tax').account_id = self.account
        return tax

    def test_multiple_cases_and_retention_details_remain_separate(self):
        income = self._retention('income', '303', 10) | self._retention('income', '307', 3)
        vat = self._retention('vat', '2', 70)
        self.case.write({'income_withholding_ids': [Command.set(income.ids)],
                         'vat_withholding_ids': [Command.set(vat.ids)]})
        second = self.case.copy({'name': 'Segundo caso del mismo plan'})
        self.assertEqual(len(self.policy.case_ids), 2)
        self.assertEqual(second.income_withholding_ids, income)
        self.assertFalse(self.case._configuration_issue())
        scenario = self.env['erpec.tax.plan'].create({'name': 'Retenciones previstas',
            'partner_id': self.partner.id, 'product_id': self.product.id})
        self.assertEqual(scenario.planned_income_withholding_ids, income)
        self.assertEqual(scenario.planned_vat_withholding_ids, vat)
        self.assertEqual(scenario.withholding_account_ids, self.account)
        self.assertEqual(scenario.planned_tax_ids.compute_all(100)['total_included'], 112)
        self.assertIn('no calcula ni registra retenciones', scenario.case_status)
        self.assertFalse(self.product.supplier_taxes_id)

    def test_retention_kind_direction_and_accounts_checked(self):
        tax = self._retention('income', '303', 10)
        group = self.env['account.tax'].create({'name': 'Grupo con retención incorrecta',
            'type_tax_use': 'purchase', 'amount_type': 'group', 'children_tax_ids': [Command.set(tax.ids)]})
        self.case.tax_ids = group
        self.assertIn('campos separados', self.case._configuration_issue())
        self.case.tax_ids = self.taxes
        self.case.vat_withholding_ids = tax
        self.assertIn('clase', self.case._configuration_issue())
        self.case.vat_withholding_ids = False
        self.case.income_withholding_ids = tax
        tax.refund_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').account_id = False
        self.assertIn('cuentas contables', self.case._configuration_issue())
        tax.erpec_reference_id = self.env.ref('erpec_workspace.sri_retention_vat_2')
        self.assertIn('catálogo SRI', self.case._configuration_issue())
        tax.tax_group_id.l10n_ec_type = 'withhold_income_sale'
        self.assertIn('operación', self.case._configuration_issue())

    def test_retention_catalogs_and_visible_actions(self):
        self.assertEqual(self.env['erpec.tax.reference'].search_count([('category', '=', 'income')]), 123)
        refs = self.env['erpec.tax.reference'].search([('category', '=', 'vat')])
        self.assertEqual(set(refs.mapped('code')), {'1', '2', '3', '7', '8', '9', '10', '11'})
        self.assertIn('NAC-DGERCGC26', self.env.ref('erpec_workspace.sri_retention_income_310').rate_description)
        from odoo.tools.safe_eval import safe_eval
        for kind, code, amount in [('income', '303', 10), ('vat', '2', 70)]:
            tax = self._retention(kind, code, amount)
            action = self.env.ref('erpec_workspace.tax_' + kind + '_detail_action')
            self.assertIn(tax, self.env['account.tax'].search(safe_eval(action.domain)))
            arch = self.env['erpec.tax.case'].get_view(view_type='form')['arch']
            self.assertIn(kind + '_withholding_ids', arch)
        tax.erpec_reference_id = False
        self.assertEqual(tax.erpec_rate_status, 'Referencia SRI pendiente.')
        self.assertEqual(tax.erpec_rate_state, 'missing')

    def test_fixed_retention_rate_is_reconciled_and_mismatch_blocks_case(self):
        tax = self._retention('income', '303', 10)
        self.case.income_withholding_ids = tax
        self.assertEqual(tax.erpec_reference_id.rate_mode, 'single')
        self.assertEqual(tax.erpec_reference_id.fixed_rate, 10)
        self.assertTrue(tax.erpec_rate_review_current)
        self.assertFalse(self.case._configuration_issue())
        tax.amount = -8
        self.assertFalse(tax.erpec_rate_review_current)
        self.assertEqual(tax.erpec_rate_state, 'mismatch')
        self.assertIn('no coincide', self.case._configuration_issue())
        tax.erpec_rate_review_note = 'La operación fue revisada, pero no puede sustituir la tarifa publicada.'
        with self.assertRaises(ValidationError):
            tax.action_erpec_confirm_rate_review()

    def test_conditional_retention_requires_traceable_review_and_invalidates(self):
        tax = self._retention('income', '310', 1)
        self.case.income_withholding_ids = tax
        self.assertEqual(tax.erpec_reference_id.rate_mode, 'conditional')
        self.assertIn('revisión', self.case._configuration_issue())
        with self.assertRaises(ValidationError):
            tax.action_erpec_confirm_rate_review()
        tax.erpec_rate_review_note = 'Caso sintético: porcentaje sustentado por la condición aplicable.'
        tax.action_erpec_confirm_rate_review()
        self.assertTrue(tax.erpec_rate_review_current)
        self.assertEqual(tax.erpec_rate_state, 'reviewed')
        self.assertFalse(self.case._configuration_issue())
        reviewed_at = tax.erpec_rate_reviewed_at
        self.assertEqual(tax.erpec_rate_reviewed_by_id, self.env.user)
        self.assertTrue(reviewed_at)
        tax.amount = -2
        self.assertFalse(tax.erpec_rate_review_current)
        self.assertIn('revisión', self.case._configuration_issue())

    def test_rate_review_permissions_and_protected_audit_fields(self):
        tax = self._retention('income', '310', 1)
        tax.erpec_rate_review_note = 'Condición sintética revisada.'
        user = self.env['res.users'].create({'name': 'Comprador sin revisión', 'login': 'buyer_no_rate_review',
            'groups_id': [Command.set(self.env.ref('purchase.group_purchase_user').ids)]})
        with self.assertRaises(AccessError):
            tax.with_user(user).action_erpec_confirm_rate_review()
        with self.assertRaises(AccessError):
            tax.write({'erpec_rate_review_key': 'no-permitido'})
        tax.action_erpec_confirm_rate_review()
        tax.erpec_reference_id.rate_description = '1 o 2 según condición actualizada'
        self.assertFalse(tax.erpec_rate_review_current)
        self.assertIn('pendiente', tax.erpec_rate_status.lower())
        list_arch = self.env.ref('erpec_workspace.tax_retention_detail_list').arch_db
        form_arch = self.env['account.tax'].get_view(view_type='form')['arch']
        self.assertIn('erpec_rate_status', list_arch)
        self.assertIn('action_erpec_confirm_rate_review', form_arch)
        self.assertEqual(self.env.ref('erpec_workspace.tax_income_detail_action').view_id,
                         self.env.ref('erpec_workspace.tax_retention_detail_list'))
        self.assertEqual(self.env.ref('erpec_workspace.tax_vat_detail_action').view_id,
                         self.env.ref('erpec_workspace.tax_retention_detail_list'))

    def _intersection_setup(self, retention=False):
        self.taxes[1].erpec_reference_id = self.reference.copy({'code': 'TX-SP02-B'})
        right = self.env['erpec.tax.policy'].create({'name': 'Plan del producto distinto del tercero'})
        right_case = self.case.copy({'policy_id': right.id, 'tax_ids': [Command.set(self.taxes[0].ids)]})
        self.partner.erpec_policy_ids = self.policy
        self.product.erpec_policy_ids = right
        if retention:
            income = self._retention('income', '303', 10)
            vat = self._retention('vat', '2', 70)
            for case in self.case | right_case:
                case.write({'income_withholding_ids': [Command.set(income.ids)],
                    'vat_withholding_ids': [Command.set(vat.ids)], 'withholding_bases_confirmed': True})
        return right, right_case

    def test_intersection_per_purchase_line_and_native_consolidation(self):
        right, case = self._intersection_setup()
        third = self.env['erpec.tax.policy'].create({'name': 'Plan de otro artículo'})
        self.case.copy({'policy_id': third.id, 'tax_ids': [Command.set(self.taxes[1].ids)]})
        product2 = self.env['product.product'].create({'name': 'Otro artículo', 'erpec_tax_type_id': self.product_type.id, 'erpec_policy_ids': [Command.set(third.ids)]})
        order = self.env['purchase.order'].create({'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': product.id, 'product_qty': 1, 'price_unit': price})
                           for product, price in [(self.product, 100), (self.product, 50), (product2, 100)]]})
        self.assertEqual(order.order_line[0].taxes_id, self.taxes[0])
        self.assertEqual(order.order_line[1].taxes_id, self.taxes[0])
        self.assertEqual(order.order_line[2].taxes_id, self.taxes[1])
        self.assertEqual(order.amount_tax, 17)
        self.assertNotEqual(self.partner.erpec_policy_ids, self.product.erpec_policy_ids)
        self.product.erpec_policy_ids |= self.policy
        selected = self.env['erpec.tax.policy']._intersection(self.company, 'purchase', self.partner, self.product)
        self.assertEqual(selected['taxes'], self.taxes)

    def test_intersection_invoice_retention_consolidation_and_update(self):
        self._intersection_setup(retention=True)
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': self.partner.id,
            'invoice_line_ids': [Command.create({'product_id': self.product.id, 'quantity': 1, 'price_unit': price})
                                 for price in (100, 50)]})
        self.assertEqual(invoice.amount_tax, 15)
        self.assertEqual(len(invoice.ec_withholding_ids), 2)
        income = invoice.ec_withholding_ids.filtered(lambda w: w.tax_kind == 'income')
        vat = invoice.ec_withholding_ids.filtered(lambda w: w.tax_kind == 'vat')
        self.assertEqual(income.base_amount, 150)
        self.assertEqual(income.estimated_amount, 15)
        self.assertEqual(vat.base_amount, 15)
        self.assertEqual(vat.estimated_amount, 10.5)
        invoice.invoice_line_ids[1].price_unit = 100
        self.assertEqual(income.base_amount, 200)
        self.assertEqual(vat.base_amount, 20)
        self.assertEqual(len(invoice.ec_withholding_ids), 2)
        invoice.invoice_line_ids[1].unlink()
        self.assertEqual(income.base_amount, 100)
        self.assertEqual(vat.base_amount, 10)
        self.assertIn('Línea 1', invoice.erpec_retention_summary)
        self.assertFalse(invoice.line_ids.filtered(lambda l: l.tax_line_id in (income.tax_id | vat.tax_id)))

    def test_intersection_sale_customer_and_product_changes(self):
        self._intersection_setup()
        self.assignment.unlink()
        self.case.operation = 'sale'
        self.taxes.type_tax_use = 'sale'
        right_case = self.product.erpec_policy_ids.case_ids
        right_case.operation = 'sale'
        order = self.env['sale.order'].create({'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_uom_qty': 1, 'price_unit': 100})]})
        self.assertEqual(order.order_line.tax_id, self.taxes[0])
        self.assertEqual(order.amount_tax, 10)
        invoice = self.env['account.move'].create({'move_type': 'out_invoice', 'partner_id': self.partner.id,
            'invoice_line_ids': [Command.create({'product_id': self.product.id, 'quantity': 1, 'price_unit': 100})]})
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.taxes[0])
        self.assertEqual(invoice.amount_tax, 10)
        other = self.env['res.partner'].create({'name': 'Cliente sin plan'})
        order.partner_id = other
        self.assertFalse(order.order_line.tax_id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.action_confirm()

    def test_intersection_no_common_detail_and_company_isolation(self):
        right, case = self._intersection_setup()
        case.tax_ids = False
        with self.assertRaises(ValidationError):
            self.env['erpec.tax.policy']._intersection(self.company, 'purchase', self.partner, self.product)
        case.tax_ids = self.taxes[1]
        self.case.tax_ids = self.taxes[0]
        result = self.env['erpec.tax.policy']._intersection(self.company, 'purchase', self.partner, self.product)
        self.assertFalse(result['taxes'])
        self.assertIn('Sin detalles', result['message'])
        other = self.env['res.company'].create({'name': 'Empresa sin planes comunes'})
        result = self.env['erpec.tax.policy'].with_company(other)._intersection(other, 'purchase', self.partner, self.product)
        self.assertFalse(result['configured'])

    def test_intersection_buyer_can_consume_without_editing_plan(self):
        self._intersection_setup()
        buyer = self.env['res.users'].create({'name': 'Comprador cruce', 'login': 'buyer_intersection',
            'company_id': self.company.id, 'company_ids': [Command.set(self.company.ids)],
            'groups_id': [Command.set(self.env.ref('purchase.group_purchase_user').ids)]})
        order = self.env['purchase.order'].with_user(buyer).create({'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_qty': 1, 'price_unit': 100})]})
        self.assertEqual(order.order_line.taxes_id, self.taxes[0])
        self.assertIn('automáticamente', order.order_line.erpec_tax_notice)
        with self.assertRaises(AccessError):
            self.policy.with_user(buyer).write({'name': 'No permitido'})
