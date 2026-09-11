"""Escenario repetible de producción sobre la demo sintética; ejecutar con Odoo shell."""
from datetime import timedelta
from odoo import fields

company = env.company
if company.vat or 'DEMO' not in company.name:
    raise RuntimeError('El escenario solo se permite en la empresa DEMO sin RUC')
admin = env.ref('base.user_admin')
admin.write({'groups_id': [(4, env.ref(reference).id) for reference in ['mrp.group_mrp_manager', 'mrp.group_mrp_routings', 'mrp.group_mrp_workorder_dependencies']]})
existing = env.ref('erpec_manufacturing_demo.finished_order', raise_if_not_found=False)
if existing:
    print('Escenario de producción existente; se conservan sus datos')
else:
    category = env['product.category'].create({'name': 'Producción DEMO · AVCO periódico', 'property_cost_method': 'average', 'property_valuation': 'manual_periodic'})
    raw = env['product.product'].create({'name': 'Tablero sintético DEMO', 'type': 'consu', 'is_storable': True, 'standard_price': 5, 'categ_id': category.id, 'company_id': company.id})
    product = env['product.product'].create({'name': 'Estante fabricado DEMO', 'type': 'consu', 'is_storable': True, 'categ_id': category.id, 'company_id': company.id})
    center = env['mrp.workcenter'].create({'name': 'Banco de montaje DEMO', 'costs_hour': 60, 'company_id': company.id})
    bom = env['mrp.bom'].create({'product_tmpl_id': product.product_tmpl_id.id, 'company_id': company.id, 'product_qty': 1, 'allow_operation_dependencies': True, 'bom_line_ids': [(0, 0, {'product_id': raw.id, 'product_qty': 2})]})
    first = env['mrp.routing.workcenter'].create({'name': 'Preparación DEMO', 'bom_id': bom.id, 'workcenter_id': center.id, 'time_cycle_manual': 10, 'sequence': 10})
    env['mrp.routing.workcenter'].create({'name': 'Montaje DEMO', 'bom_id': bom.id, 'workcenter_id': center.id, 'time_cycle_manual': 10, 'sequence': 20, 'blocked_by_operation_ids': [(4, first.id)]})
    location = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1).lot_stock_id
    env['stock.quant']._update_available_quantity(raw, location, 20)
    completed = env['mrp.production'].create({'product_id': product.id, 'product_qty': 1, 'bom_id': bom.id, 'origin': 'Ensayo sintético: tiempos de ejemplo, sin operación real'})
    completed.action_confirm()
    completed.action_assign()
    completed.qty_producing = 1
    completed._set_qty_producing()
    for index, stage in enumerate(completed.workorder_ids.sorted('id')):
        stage.button_start()
        if index == 0:
            stage.erpec_pause_reason = 'Ajuste de herramienta DEMO'
            stage.button_pending()
            stage.button_start()
        stage.button_finish()
        stage.time_ids.unlink()
        env['mrp.workcenter.productivity'].create({'workorder_id': stage.id, 'workcenter_id': center.id, 'user_id': env.uid, 'loss_id': env.ref('mrp.block_reason7').id, 'date_start': fields.Datetime.now()-timedelta(minutes=20-index*10), 'date_end': fields.Datetime.now()-timedelta(minutes=10-index*10)})
    completed.move_raw_ids.picked = True
    completed.with_context(skip_backorder=True).button_mark_done()
    pending = env['mrp.production'].create({'product_id': product.id, 'product_qty': 2, 'bom_id': bom.id, 'origin': 'Demostración operativa: iniciar y pausar las etapas'})
    pending.action_confirm()
    pending.action_assign()
    pending.button_plan()
    shortage = env['mrp.production'].create({'product_id': product.id, 'product_qty': 50, 'bom_id': bom.id, 'origin': 'Demostración de faltantes: abastecer antes de fabricar'})
    shortage.action_confirm()
    for name, record in [('finished_order', completed), ('pending_order', pending), ('shortage_order', shortage), ('bom', bom), ('raw', raw), ('product', product), ('center', center)]:
        env['ir.model.data'].create({'module': 'erpec_manufacturing_demo', 'name': name, 'model': record._name, 'res_id': record.id, 'noupdate': True})
    assert completed.state == 'done'
    assert abs(sum(completed.move_finished_ids.stock_valuation_layer_ids.mapped('value'))-30) < 0.1
    print('Escenario sintético: una fabricación de costo 30 USD, dos etapas, orden pendiente y faltantes')
assert not company.vat
assert not env['ir.module.module'].search_count([('state', '=', 'installed'), ('license', 'in', ['OEEL-1', 'OPL-1'])])
env.cr.commit()
