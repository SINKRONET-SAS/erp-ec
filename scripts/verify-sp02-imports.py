"""Verificación de solo lectura del expediente visual SP02."""
import json
from pathlib import Path
if env.cr.dbname != 'ec_operational_7a74b3c051':
    raise RuntimeError('Copia de aceptación incorrecta.')
dossier = env.ref('erpec_ui_acceptance.dossier')
purchase = env.ref('erpec_ui_acceptance.purchase')
bill = env.ref('erpec_ui_acceptance.bill')
products = env.ref('erpec_ui_acceptance.import_a') | env.ref('erpec_ui_acceptance.import_b')
assert purchase.currency_id.name == 'EUR' and purchase.amount_total == 300
assert len(purchase.picking_ids) == 2 and set(purchase.picking_ids.mapped('state')) == {'done'}
assert purchase.order_line.mapped('qty_received') == [10, 10]
assert bill.state == 'posted' and bill.amount_total == 30
cost = dossier.cost_ids.filtered(lambda c: not c.erpec_reversal_of_id)
assert len(cost) == 1 and cost.state == 'done'
assert abs(cost.amount_total - 34.78) < 0.001
reverse = dossier.cost_ids.filtered('erpec_reversal_of_id')
for entry in (cost | reverse).account_move_id:
    assert entry.state == 'posted' and abs(sum(entry.line_ids.mapped('balance'))) < 0.001
values = []
for product in products:
    receipts = purchase.picking_ids.move_ids.filtered(lambda m: m.product_id == product).stock_valuation_layer_ids
    layers = env['stock.valuation.layer'].search([('product_id', '=', product.id)])
    values.append({'product': product.display_name, 'quantity': product.qty_available, 'unitCost': product.standard_price, 'value': sum(layers.mapped('value')), 'receiptLinkedValue': sum(receipts.mapped('value'))})
report = {'database': env.cr.dbname, 'purchase': purchase.name, 'receipts': purchase.picking_ids.mapped('name'), 'bill': bill.name, 'foreignFreight': bill.amount_total, 'companyFreight': cost.amount_total, 'cost': cost.name, 'reversals': reverse.mapped('name'), 'costJournal': cost.account_move_id.name, 'reversalJournals': reverse.account_move_id.mapped('name'), 'values': values}
suffix = 'reversed' if reverse and all(r.state == 'done' for r in reverse) else 'cost'
if suffix == 'reversed':
    assert abs(sum((cost | reverse).stock_valuation_layer_ids.mapped('value'))) < 0.001
    assert abs(sum(v['value'] for v in values) - 347.76) < 0.001
    assert all(abs(v['unitCost'] - expected) < 0.00001 for v, expected in zip(values, [11.592, 23.184]))
else:
    assert abs(sum(v['value'] for v in values) - 382.54) < 0.001
content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
assert content.encode('utf-8').decode('utf-8') == content
Path('.cache/windows/sp02-import-' + suffix + '.json').write_text(content, encoding='utf-8', newline='\n')
env.cr.rollback()
print(json.dumps(report, ensure_ascii=True))
