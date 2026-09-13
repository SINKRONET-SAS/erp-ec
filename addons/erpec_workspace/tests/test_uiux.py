"""Regresión de acciones comerciales visibles y acceso por perfil."""
from lxml import etree
from odoo.tests import TransactionCase, tagged, new_test_user
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class UiUxCase(TransactionCase):
    def test_confirmation_and_responsive_views(self):
        seller = new_test_user(self.env, login='uiux_seller', groups='sales_team.group_sale_salesman')
        partner = self.env['res.partner'].create({'name': 'Cliente UIUX con nombre largo para comprobar tarjetas'})
        product = self.env['product.product'].create({'name': 'Servicio UIUX', 'type': 'service', 'taxes_id': [(5, 0, 0)]})
        order = self.env['sale.order'].with_user(seller).create({
            'partner_id': partner.id, 'user_id': seller.id,
            'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 1, 'price_unit': 100, 'tax_id': [(5, 0, 0)]})]})
        arch = etree.fromstring(order.get_view(view_id=self.env.ref('sale.view_order_form').id, view_type='form')['arch'].encode())
        buttons = arch.xpath("//sheet//button[@name='action_confirm']")
        self.assertEqual(len(buttons), 1)
        self.assertEqual(safe_eval(buttons[0].get('context')), {'validate_analytic': True})
        condition = buttons[0].get('invisible')
        for state in ['draft', 'sent', 'sale', 'cancel']:
            self.assertEqual(safe_eval(condition, {'state': state}), state in ['sale', 'cancel'])
        for state in ['draft', 'sent']:
            candidate = order.copy()
            candidate.write({'state': state})
            candidate.with_context(validate_analytic=True).action_confirm()
            self.assertEqual(candidate.state, 'sale')
            self.assertEqual(candidate.amount_total, 100)
        action = self.env.ref('erpec_workspace.sale_action').read()[0]
        self.assertEqual(action['mobile_view_mode'], 'kanban')
        self.assertEqual([item[1] for item in action['views']], ['list', 'kanban', 'form'])
        cards = order.get_view(view_id=self.env.ref('erpec_workspace.sale_cards').id, view_type='kanban')['arch']
        for name in ['partner_id', 'state', 'amount_total', 'invoice_status']:
            self.assertIn(name, cards)

    def test_reader_does_not_gain_sales_access(self):
        reader = new_test_user(self.env, login='uiux_reader', groups='base.group_user')
        action = self.env['erpec.workspace'].with_user(reader).action_home()
        workspace = self.env['erpec.workspace'].with_user(reader).browse(action['res_id'])
        with self.assertRaises(AccessError):
            workspace.with_context(erpec_area='sales').action_area()
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(reader).create({'partner_id': self.env.user.partner_id.id})
