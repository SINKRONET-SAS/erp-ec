"""Comprueba los resultados persistidos del recorrido visual de venta, sin cambiarlos."""
import hashlib
import json
from pathlib import Path
if env.cr.dbname != 'ec_operational_7a74b3c051' or env.company.vat:
    raise RuntimeError('Solo copia sintética SP02 autorizada.')
order = env.ref('erpec_sp02_sale.order')
product = env.ref('erpec_sp02_value.finished')
assert order.state == 'sale'
assert abs(order.amount_total - 60) < 0.001
pickings = order.picking_ids
out = pickings.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'done')
pending = pickings.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state not in ('done', 'cancel'))
returns = env['stock.picking'].search([('move_ids.origin_returned_move_id', 'in', out.move_ids.ids), ('state', '=', 'done')])
assert len(out) == len(pending) == len(returns) == 1
assert sum(out.move_ids.mapped('quantity')) == sum(returns.move_ids.mapped('quantity')) == 1
assert sum(pending.move_ids.mapped('product_uom_qty')) == 1
assert order.order_line.qty_delivered == 0
layers = env['stock.valuation.layer'].search([('stock_move_id', 'in', (out.move_ids | returns.move_ids).ids)])
assert sorted(round(value, 2) for value in layers.mapped('value')) == [-10.32, 10.32]
for move in layers.account_move_id:
    assert move.state == 'posted'
    assert abs(sum(move.line_ids.mapped('balance'))) < 0.001
assert product.qty_available == 2
all_layers = env['stock.valuation.layer'].search([('product_id', '=', product.id)])
assert abs(sum(all_layers.mapped('value')) - 20.63) < 0.001
result = {'database': env.cr.dbname, 'order': order.name, 'total': order.amount_total,
          'delivery': out.name, 'pendingDelivery': pending.name, 'return': returns.name,
          'netDelivered': order.order_line.qty_delivered, 'inventory': product.qty_available,
          'valuation': round(sum(all_layers.mapped('value')), 2),
          'journals': layers.account_move_id.mapped('name'), 'balancedPosted': True,
          'invoiceCreated': bool(order.invoice_ids),
          'screenshots': {str(p).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in Path('docs/evidencias/sp02-venta-visual').glob('*.png')}}
env.cr.rollback()
text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
assert text.encode('utf-8').decode('utf-8') == text
Path('docs/evidencias/ERPEC26-SP02-VENTA-VISUAL.json').write_text(text, encoding='utf-8', newline='\n')
print(json.dumps(result, ensure_ascii=True))
