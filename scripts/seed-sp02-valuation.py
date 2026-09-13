"""Prepara una fabricación nueva para medir tiempos reales de esta sesión."""
import json
from pathlib import Path
if env.cr.dbname != 'ec_operational_7a74b3c051' or env.company.vat:
    raise RuntimeError('Solo se permite la copia sintética con RUC vacío.')
if env.ref('erpec_sp02_value.production', raise_if_not_found=False):
    raise RuntimeError('El escenario ya existe; no sobrescribirlo.')
company = env.company
category = env.ref('erpec_ui_acceptance.import_a').categ_id
raw = env['product.product'].create({'name': 'Componente · Valoración nueva SP02', 'type': 'consu', 'is_storable': True, 'categ_id': category.id, 'company_id': company.id, 'supplier_taxes_id': [(5, 0, 0)]})
finished = env['product.product'].create({'name': 'Terminado · Valoración nueva SP02', 'type': 'consu', 'is_storable': True, 'categ_id': category.id, 'company_id': company.id, 'taxes_id': [(5, 0, 0)]})
partner = env.ref('erpec_ui_acceptance.purchase').partner_id
purchase = env['purchase.order'].create({'partner_id': partner.id, 'currency_id': company.currency_id.id, 'order_line': [(0, 0, {'product_id': raw.id, 'product_qty': 4, 'price_unit': 5, 'taxes_id': [(5, 0, 0)]})]})
purchase.button_confirm()
receipt = purchase.picking_ids
receipt.move_ids.quantity = 4
receipt.move_ids.picked = True
receipt.button_validate()
assert receipt.state == 'done'
center = env['mrp.workcenter'].create({'name': 'Centro · Valoración nueva SP02', 'costs_hour': 60, 'company_id': company.id})
bom = env['mrp.bom'].create({'product_tmpl_id': finished.product_tmpl_id.id, 'company_id': company.id, 'product_qty': 1, 'allow_operation_dependencies': True, 'bom_line_ids': [(0, 0, {'product_id': raw.id, 'product_qty': 2})]})
first = env['mrp.routing.workcenter'].create({'name': 'Preparación · Valoración nueva', 'bom_id': bom.id, 'workcenter_id': center.id, 'sequence': 10, 'time_mode': 'manual', 'time_cycle_manual': 1})
env['mrp.routing.workcenter'].create({'name': 'Montaje · Valoración nueva', 'bom_id': bom.id, 'workcenter_id': center.id, 'sequence': 20, 'time_mode': 'manual', 'time_cycle_manual': 1, 'blocked_by_operation_ids': [(4, first.id)]})
production = env['mrp.production'].create({'product_id': finished.id, 'product_qty': 2, 'bom_id': bom.id, 'origin': 'SP02 · tiempo medido en sesión nueva; costo sintético 60 USD/h'})
records = {'production': production, 'raw': raw, 'finished': finished, 'receipt': receipt, 'center': center}
for name, record in records.items():
    env['ir.model.data'].create({'module': 'erpec_sp02_value', 'name': name, 'model': record._name, 'res_id': record.id, 'noupdate': True})
report = {'database': env.cr.dbname, 'records': {k: {'id': v.id, 'name': v.display_name} for k, v in records.items()}, 'materialCost': 20, 'hourlyCost': 60, 'productionState': production.state, 'setup': 'Compra y recepción de cuatro componentes por ORM; fabricación sin confirmar y sin temporizadores.'}
content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
assert content.encode('utf-8').decode('utf-8') == content
Path('.cache/windows/sp02-value-scenario.json').write_text(content, encoding='utf-8', newline='\n')
env.cr.commit()
print(json.dumps(report, ensure_ascii=True))
