"""Contrasta el recorrido visual SP02 sin modificar documentos de negocio."""
import json
from pathlib import Path

if env.cr.dbname != 'ec_operational_7a74b3c051':
    raise RuntimeError('Esta evidencia pertenece únicamente a la copia visual identificada.')
root = Path.cwd()
origin = env.ref('erpec_ui_acceptance.production')
orders = env['mrp.production'].search([('procurement_group_id', '=', origin.procurement_group_id.id)])
assert len(orders) == 2 and all(order.state == 'done' for order in orders)
assert sum(orders.mapped('qty_produced')) == 2
raw = env.ref('erpec_ui_acceptance.raw')
finished = env.ref('erpec_ui_acceptance.finished')
moves = orders.move_raw_ids.filtered(lambda m: m.state == 'done' and m.product_id == raw)
assert sum(moves.mapped('quantity')) == 4
assert sum(orders.move_finished_ids.filtered(lambda m: m.state == 'done' and m.product_id == finished).mapped('quantity')) == 2
operations = orders.workorder_ids
assert len(operations) == 4 and all(op.state == 'done' for op in operations)
assert not operations.time_ids.filtered(lambda interval: not interval.date_end)
assert operations.time_ids.filtered('erpec_pause')
assert not env.company.vat
data = {
    'database': env.cr.dbname,
    'orders': [{'id': o.id, 'name': o.name, 'state': o.state, 'produced': o.qty_produced} for o in orders],
    'componentsConsumed': 4, 'finishedProduced': 2, 'operationsDone': 4,
    'openIntervals': 0,
    'checks': ['Dos órdenes terminadas; producción total 2', 'Consumo total 4 componentes',
               'Cuatro operaciones terminadas y ningún intervalo abierto', 'RUC demo vacío'],
    'limitation': 'El contador de la primera operación permaneció abierto desde el 11 de septiembre; su costo no es representativo. No valida venta, reversión ni valoración comercial.'
}
text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
assert text.encode('utf-8').decode('utf-8') == text
(root / '.cache/windows/sp02-production-result.json').write_text(text, encoding='utf-8', newline='\n')
env.cr.rollback()
print(json.dumps(data, ensure_ascii=True))
