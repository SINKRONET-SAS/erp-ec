"""Comprueba valoración nueva y su propagación a una entrega; ensayo aislado."""
import json
from pathlib import Path
if env.cr.dbname != 'ec_operational_7a74b3c051' or env.company.vat:
    raise RuntimeError('Solo copia sintética de aceptación.')
mo = env.ref('erpec_sp02_value.production')
raw = env.ref('erpec_sp02_value.raw')
finished = env.ref('erpec_sp02_value.finished')
assert mo.state == 'done' and mo.qty_produced == 2
assert sum(mo.move_raw_ids.mapped('quantity')) == 4
intervals = mo.workorder_ids.time_ids
assert len(intervals) == 2 and all(t.date_end and t.date_start >= mo.create_date for t in intervals)
assert all(w.state == 'done' for w in mo.workorder_ids)
materials = -sum(mo.move_raw_ids.stock_valuation_layer_ids.mapped('value'))
labor = sum(w.duration / 60 * w.costs_hour for w in mo.workorder_ids)
value = sum(mo.move_finished_ids.stock_valuation_layer_ids.mapped('value'))
assert materials == 20 and abs(value - env.company.currency_id.round(materials + labor)) < 0.001
assert raw.qty_available == 0 and finished.qty_available == 2
entries = (mo.move_raw_ids | mo.move_finished_ids).stock_valuation_layer_ids.account_move_id
assert all(entry.state == 'posted' and abs(sum(entry.line_ids.mapped('balance'))) < 0.001 for entry in entries)
report = {'database': env.cr.dbname, 'production': mo.name, 'quantity': 2,
          'materials': materials, 'labor': labor, 'value': value,
          'unitCost': finished.standard_price,
          'intervals': [{'start': str(t.date_start), 'end': str(t.date_end), 'minutes': t.duration} for t in intervals],
          'journals': entries.mapped('name'), 'openIntervals': 0}
# La entrega se ensaya por ORM en transacción revertida, sin factura ni emisión.
order = env['sale.order'].create({'partner_id': env.ref('erpec_ui_acceptance.purchase').partner_id.id,
    'order_line': [(0, 0, {'product_id': finished.id, 'product_uom_qty': 1, 'price_unit': 30, 'tax_id': [(5, 0, 0)]})]})
order.action_confirm()
picking = order.picking_ids
picking.move_ids.quantity = 1
picking.move_ids.picked = True
picking.button_validate()
assert picking.state == 'done'
out_value = -sum(picking.move_ids.stock_valuation_layer_ids.mapped('value'))
assert abs(out_value - env.company.currency_id.round(value / 2)) < 0.001
report['deliveryRollbackTest'] = {'quantity': 1, 'value': out_value, 'remainingQuantity': finished.qty_available}
assert finished.qty_available == 1
wizard = env['stock.return.picking'].with_context(active_model='stock.picking', active_id=picking.id, active_ids=picking.ids).create({'picking_id': picking.id})
wizard.product_return_moves.write({'quantity': 1, 'to_refund': True})
returned = env['stock.picking'].browse(wizard.action_create_returns()['res_id'])
returned.move_ids.quantity = 1
returned.move_ids.picked = True
returned.button_validate()
return_value = sum(returned.move_ids.stock_valuation_layer_ids.mapped('value'))
assert returned.state == 'done' and abs(return_value - out_value) < 0.001
assert finished.qty_available == 2
for entry in (picking | returned).move_ids.stock_valuation_layer_ids.account_move_id:
    assert entry.state == 'posted' and abs(sum(entry.line_ids.mapped('balance'))) < 0.001
report['returnRollbackTest'] = {'quantity': 1, 'value': return_value, 'remainingQuantity': finished.qty_available}
env.cr.rollback()
content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
assert content.encode('utf-8').decode('utf-8') == content
Path('.cache/windows/sp02-valuation-result.json').write_text(content, encoding='utf-8', newline='\n')
print(json.dumps(report, ensure_ascii=True))
