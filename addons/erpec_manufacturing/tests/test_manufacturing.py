"""Ciclos sintéticos de fabricación; sin emisiones ni movimientos en la demo original."""
from datetime import timedelta
from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install')
class ManufacturingCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, no_reset_password=True))
        self.location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        category = self.env['product.category'].create({'name': 'Ensayo AVCO', 'property_cost_method': 'average', 'property_valuation': 'manual_periodic'})
        self.raw = self.env['product.product'].create({'name': 'Componente sintético', 'is_storable': True, 'type': 'consu', 'standard_price': 5, 'categ_id': category.id})
        self.finished = self.env['product.product'].create({'name': 'Producto sintético', 'is_storable': True, 'type': 'consu', 'categ_id': category.id})
        self.bom = self.env['mrp.bom'].create({'product_tmpl_id': self.finished.product_tmpl_id.id, 'product_qty': 1, 'company_id': self.env.company.id, 'bom_line_ids': [(0, 0, {'product_id': self.raw.id, 'product_qty': 2})]})

    def production(self, quantity=2, stock=10):
        self.env['stock.quant']._update_available_quantity(self.raw, self.location, stock)
        order = self.env['mrp.production'].create({'product_id': self.finished.id, 'product_qty': quantity, 'bom_id': self.bom.id})
        order.action_confirm()
        order.action_assign()
        return order

    def finish(self, order, quantity, backorder=False):
        order.qty_producing = quantity
        order._set_qty_producing()
        order.move_raw_ids.picked = True
        return order.with_context(skip_backorder=True, mo_ids_to_backorder=order.ids if backorder else []).button_mark_done()

    def test_partial_complete_scrap_unbuild_and_cost(self):
        order = self.production()
        self.finish(order, 1, backorder=True)
        remaining = self.env['mrp.production'].search([('procurement_group_id', '=', order.procurement_group_id.id), ('id', '!=', order.id)])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining.product_qty, 1)
        self.finish(remaining, 1)
        self.assertEqual((order | remaining).mapped('state'), ['done', 'done'])
        self.assertEqual(self.raw.with_context(location=self.location.id).qty_available, 6)
        self.assertEqual(self.finished.with_context(location=self.location.id).qty_available, 2)
        self.assertAlmostEqual(sum((order | remaining).move_finished_ids.stock_valuation_layer_ids.mapped('value')), 20)
        scrap = self.env['stock.scrap'].create({'product_id': self.raw.id, 'scrap_qty': 1, 'location_id': self.location.id, 'production_id': remaining.id})
        scrap.action_validate()
        self.assertEqual(scrap.state, 'done')
        self.assertAlmostEqual(sum(scrap.move_ids.stock_valuation_layer_ids.mapped('value')), -5)
        unbuild = self.env['mrp.unbuild'].create({'mo_id': remaining.id, 'product_id': self.finished.id, 'product_qty': 1, 'location_id': self.location.id, 'location_dest_id': self.location.id})
        unbuild.action_unbuild()
        self.assertEqual(unbuild.state, 'done')
        self.assertEqual(self.raw.with_context(location=self.location.id).qty_available, 7)
        self.assertEqual(self.finished.with_context(location=self.location.id).qty_available, 1)

    def test_shortage_rolls_back_and_can_recover(self):
        order = self.production(stock=1)
        with self.assertRaisesRegex(UserError, 'faltan existencias'), self.cr.savepoint():
            self.finish(order, 2)
        self.assertNotEqual(order.state, 'done')
        self.env['stock.quant']._update_available_quantity(self.raw, self.location, 3)
        order.action_assign()
        self.finish(order, 2)
        self.assertEqual(order.state, 'done')
        self.assertEqual(self.raw.with_context(location=self.location.id).qty_available, 0)

    def test_operations_dependency_pause_repeat_and_cost(self):
        center = self.env['mrp.workcenter'].create({'name': 'Centro sintético', 'costs_hour': 60})
        self.bom.allow_operation_dependencies = True
        first = self.env['mrp.routing.workcenter'].create({'name': 'Preparación', 'bom_id': self.bom.id, 'workcenter_id': center.id, 'time_cycle_manual': 10})
        self.env['mrp.routing.workcenter'].create({'name': 'Montaje', 'bom_id': self.bom.id, 'workcenter_id': center.id, 'time_cycle_manual': 10, 'blocked_by_operation_ids': [(4, first.id)]})
        order = self.production(quantity=1)
        stages = order.workorder_ids.sorted('id')
        self.assertEqual(len(stages), 2)
        with self.assertRaisesRegex(UserError, 'precedente'):
            stages[1].button_start()
        with self.assertRaisesRegex(UserError, 'Finaliza'):
            self.finish(order, 1)
        stages[0].button_start()
        stages[0].button_start()
        self.assertEqual(len(stages[0].time_ids.filtered(lambda item: not item.date_end)), 1)
        stages[0].erpec_pause_reason = 'Ajuste sintético de herramienta'
        stages[0].button_pending()
        self.assertFalse(stages[0].time_ids.filtered(lambda item: not item.date_end))
        stages[0].button_start()
        stages[0].button_finish()
        stages[1].button_start()
        stages[1].button_finish()
        for stage in stages:
            stage.time_ids.unlink()
            self.env['mrp.workcenter.productivity'].create({'workorder_id': stage.id, 'workcenter_id': center.id, 'user_id': self.env.uid, 'loss_id': self.env.ref('mrp.block_reason7').id, 'date_start': fields.Datetime.now()-timedelta(minutes=10), 'date_end': fields.Datetime.now()})
        self.assertAlmostEqual(sum(stages.mapped('duration')), 20, places=1)
        self.assertAlmostEqual(sum(stage._cal_cost() for stage in stages), 20, places=1)
        self.finish(order, 1)
        self.assertAlmostEqual(sum(order.move_finished_ids.stock_valuation_layer_ids.mapped('value')), 30, places=1)

    def test_company_access_and_navigation(self):
        other = self.env['res.company'].create({'name': 'Otra organización sintética'})
        operator = new_test_user(self.env, login='manufacturing_test_operator', groups='mrp.group_mrp_user', company_id=other.id, company_ids=[(6, 0, other.ids)])
        order = self.production()
        with self.assertRaises(AccessError):
            order.with_user(operator).read(['product_id'])
        for reference in ['production_menu', 'workorder_menu', 'load_menu', 'bom_menu']:
            self.assertTrue(self.env.ref('erpec_manufacturing.'+reference).action)
        view = order.get_view(view_id=self.env.ref('mrp.mrp_production_form_view').id, view_type='form')
        self.assertIn('repón existencias', view['arch'])
