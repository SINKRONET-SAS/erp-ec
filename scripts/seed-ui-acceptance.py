"""Prepara escenarios sin ejecutar sus transiciones; solo en una copia operativa."""
import base64
import json
import secrets
from pathlib import Path
from odoo import fields

root = Path.cwd()
state = root / '.cache/windows'
current = json.loads((state / 'operational-current.json').read_text(encoding='utf-8'))
if env.cr.dbname != current['database'] or not env.cr.dbname.startswith('ec_operational_'):
    raise RuntimeError('La aceptación requiere una copia operativa aislada.')
company = env.company
if company.vat or 'DEMO' not in company.name:
    raise RuntimeError('La aceptación solo admite la empresa DEMO sin RUC.')
env = env(context=dict(env.context, no_reset_password=True, mail_create_nosubscribe=True, tracking_disable=True))
if env.ref('erpec_ui_acceptance.production', raise_if_not_found=False):
    raise RuntimeError('El escenario ya existe; conserva su recorrido y resultados.')
env['ir.cron'].search([]).write({'active': False})
env['ir.mail_server'].search([]).write({'active': False})
password = secrets.token_urlsafe(24)
profiles = {
    'operator': ('Operario · Aceptación', ['mrp.group_mrp_user', 'mrp.group_mrp_routings', 'mrp.group_mrp_workorder_dependencies']),
    'supervisor': ('Supervisor · Aceptación', ['mrp.group_mrp_manager', 'mrp.group_mrp_routings', 'mrp.group_mrp_workorder_dependencies']),
    'buyer': ('Compras · Aceptación', ['purchase.group_purchase_user']),
    'warehouse': ('Bodega · Aceptación', ['stock.group_stock_user']),
    'accountant': ('Contabilidad · Aceptación', ['account.group_account_manager', 'purchase.group_purchase_user', 'stock.group_stock_manager']),
}
users = {}
for key, (name, groups) in profiles.items():
    users[key] = env['res.users'].with_context(no_reset_password=True).create({
        'name': name, 'login': 'acceptance_' + key, 'password': password,
        'email': 'acceptance_' + key + '@example.invalid', 'notification_type': 'inbox', 'lang': 'es_EC', 'tz': 'America/Guayaquil',
        'company_id': company.id, 'company_ids': [(6, 0, company.ids)],
        'groups_id': [(6, 0, [env.ref(group).id for group in groups])],
        'action_id': env.ref('erpec_workspace.home_action').id,
    })
category = env['product.category'].create({'name': 'Aceptación · Producción AVCO', 'property_cost_method': 'average', 'property_valuation': 'manual_periodic'})
raw = env['product.product'].create({'name': 'Componente · Aceptación', 'type': 'consu', 'is_storable': True, 'standard_price': 5, 'categ_id': category.id, 'company_id': company.id})
finished = env['product.product'].create({'name': 'Producto terminado · Aceptación', 'type': 'consu', 'is_storable': True, 'categ_id': category.id, 'company_id': company.id})
center = env['mrp.workcenter'].create({'name': 'Centro · Aceptación', 'costs_hour': 60, 'company_id': company.id})
bom = env['mrp.bom'].create({'product_tmpl_id': finished.product_tmpl_id.id, 'company_id': company.id, 'product_qty': 1, 'allow_operation_dependencies': True, 'bom_line_ids': [(0, 0, {'product_id': raw.id, 'product_qty': 2})]})
first = env['mrp.routing.workcenter'].create({'name': 'Preparación · Aceptación', 'bom_id': bom.id, 'workcenter_id': center.id, 'sequence': 10, 'time_cycle_manual': 10})
env['mrp.routing.workcenter'].create({'name': 'Montaje · Aceptación', 'bom_id': bom.id, 'workcenter_id': center.id, 'sequence': 20, 'time_cycle_manual': 10, 'blocked_by_operation_ids': [(4, first.id)]})
location = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1).lot_stock_id
env['stock.quant']._update_available_quantity(raw, location, 4)
production = env['mrp.production'].create({'product_id': finished.id, 'product_qty': 2, 'bom_id': bom.id, 'origin': 'ACEPTACIÓN UI · parcial de 1 + 1; operaciones ficticias'})
accounts = {}
for code, kind in [('VAL', 'asset_current'), ('IN', 'asset_current'), ('OUT', 'asset_current'), ('EXP', 'expense')]:
    accounts[code] = env['account.account'].create({'code': 'UIACC' + code, 'name': 'Aceptación ' + code, 'account_type': kind})
journal = env['account.journal'].create({'name': 'Valoración · Aceptación', 'code': 'UIAC', 'type': 'general'})
category = env['product.category'].create({'name': 'Aceptación · Importación AVCO', 'property_cost_method': 'average', 'property_valuation': 'real_time', 'property_stock_journal': journal.id, 'property_stock_valuation_account_id': accounts['VAL'].id, 'property_stock_account_input_categ_id': accounts['IN'].id, 'property_stock_account_output_categ_id': accounts['OUT'].id, 'property_account_expense_categ_id': accounts['EXP'].id})
products = env['product.product'].create([{'name': name + ' · Aceptación', 'type': 'consu', 'is_storable': True, 'categ_id': category.id, 'company_id': company.id, 'supplier_taxes_id': [(5, 0, 0)]} for name in ['Mercadería A', 'Mercadería B']])
euro = env.ref('base.EUR')
euro.active = True
rate_date = fields.Date.to_date('2026-09-11')
rates = env['res.currency.rate'].search([('currency_id', '=', euro.id), ('name', '>=', rate_date), ('company_id', '=', company.id)])
if rates:
    raise RuntimeError('La copia ya tiene tipos de cambio para el ensayo; no sobrescribirlos.')
env['res.currency.rate'].create({'currency_id': euro.id, 'company_id': company.id, 'name': rate_date, 'rate': 1 / 1.1592})
supplier = env['res.partner'].create({'name': 'Proveedor exterior · Aceptación', 'country_id': env.ref('base.es').id, 'email': False})
purchase = env['purchase.order'].create({'partner_id': supplier.id, 'currency_id': euro.id, 'date_order': '2026-09-11 12:00:00', 'order_line': [(0, 0, {'product_id': product.id, 'product_qty': 10, 'price_unit': price, 'taxes_id': [(5, 0, 0)]}) for product, price in zip(products, [10, 20])]})
attachment = env['ir.attachment'].create({'name': 'Aceptacion-sin-validez-aduanera.txt', 'datas': base64.b64encode(b'Escenario ficticio. Sin validez aduanera. Referencia EUR/USD BCE 11-09-2026: 1.1592. No es cotizacion bancaria.')})
dossier = env['erpec.importation'].create({'name': 'IMPORTACIÓN · ACEPTACIÓN UI', 'partner_id': supplier.id, 'currency_id': euro.id, 'purchase_ids': [(6, 0, purchase.ids)], 'shipment': 'ENSAYO-SIN-VALIDEZ', 'customs_reference': 'ENSAYO-NO-AUTORIZADO', 'attachment_ids': [(4, attachment.id)]})
attachment.write({'res_model': dossier._name, 'res_id': dossier.id})
service = env['product.product'].create({'name': 'Flete exterior · Aceptación', 'type': 'service', 'property_account_expense_id': accounts['EXP'].id, 'supplier_taxes_id': [(5, 0, 0)]})
bill = env['account.move'].create({'move_type': 'in_invoice', 'partner_id': supplier.id, 'currency_id': euro.id, 'invoice_date': rate_date, 'date': rate_date, 'ref': 'ACEPTACIÓN UI · flete exterior ficticio', 'invoice_line_ids': [(0, 0, {'product_id': service.id, 'quantity': 1, 'price_unit': 30, 'account_id': accounts['EXP'].id, 'tax_ids': [(5, 0, 0)]})]})
records = {'production': production, 'raw': raw, 'finished': finished, 'center': center, 'purchase': purchase, 'dossier': dossier, 'bill': bill, 'import_a': products[0], 'import_b': products[1]}
for key, record in records.items():
    env['ir.model.data'].create({'module': 'erpec_ui_acceptance', 'name': key, 'model': record._name, 'res_id': record.id, 'noupdate': True})
directory = Path(current['directory'])
def write(path, content):
    assert content.encode('utf-8').decode('utf-8') == content
    path.write_text(content, encoding='utf-8', newline='\n')
write(directory / 'ui-credentials.json', json.dumps({'password': password, 'logins': {key: user.login for key, user in users.items()}}))
write(directory / 'ui-scenario.json', json.dumps({'database': env.cr.dbname, 'records': {key: {'id': record.id, 'name': record.display_name} for key, record in records.items()}, 'rate': {'date': '2026-09-11', 'usdPerEuro': 1.1592, 'source': 'https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.es.html'}, 'transitionsExecutedBySeed': False}, ensure_ascii=False, indent=2) + '\n')
env.cr.commit()
print('Escenarios y perfiles preparados; las confirmaciones y cierres se ejecutarán en pantalla.')
