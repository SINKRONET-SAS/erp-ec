"""Prepara venta visual del producto ya fabricado, sin confirmar la cotización."""
import json
from pathlib import Path
if env.cr.dbname != 'ec_operational_7a74b3c051' or env.company.vat:
    raise RuntimeError('Solo se admite la copia sintética de aceptación.')
env = env(context=dict(env.context, no_reset_password=True, tracking_disable=True, mail_create_nosubscribe=True))
if env.ref('erpec_sp02_sale.order', raise_if_not_found=False):
    raise RuntimeError('Ya existe el recorrido; no repetir la preparación.')
product = env.ref('erpec_sp02_value.finished')
assert product.qty_available == 2 and not product.taxes_id
assert not env['ir.mail_server'].search_count([('active', '=', True)])
directory = Path('.cache/windows/operational-tests/ec_operational_7a74b3c051')
credentials = json.loads((directory / 'ui-credentials.json').read_text(encoding='utf-8'))
seller = env['res.users'].create({
    'name': 'Ventas · Aceptación', 'login': 'acceptance_seller', 'password': credentials['password'],
    'email': 'acceptance_seller@example.invalid', 'notification_type': 'inbox',
    'lang': 'es_EC', 'tz': 'America/Guayaquil',
    'company_id': env.company.id, 'company_ids': [(6, 0, env.company.ids)],
    'groups_id': [(6, 0, env.ref('sales_team.group_sale_salesman').ids)],
    'action_id': env.ref('erpec_workspace.home_action').id})
customer = env['res.partner'].create({'name': 'Cliente · Venta visual SP02', 'customer_rank': 1, 'email': False})
order = env['sale.order'].with_user(seller).create({
    'partner_id': customer.id, 'user_id': seller.id, 'client_order_ref': 'ENSAYO SP02 · venta y devolución visual',
    'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 2, 'price_unit': 30})]})
assert order.state == 'draft' and order.amount_total == 60
for name, record in {'order': order, 'customer': customer, 'seller': seller}.items():
    env['ir.model.data'].create({'module': 'erpec_sp02_sale', 'name': name, 'model': record._name, 'res_id': record.id, 'noupdate': True})
credentials['logins']['seller'] = seller.login
text = json.dumps(credentials)
assert text.encode('utf-8').decode('utf-8') == text
(directory / 'ui-credentials.json').write_text(text, encoding='utf-8', newline='\n')
report = {'database': env.cr.dbname, 'saleId': order.id, 'sale': order.name, 'amount': order.amount_total,
          'state': order.state, 'product': product.display_name, 'stockBefore': product.qty_available}
text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
assert text.encode('utf-8').decode('utf-8') == text
Path('.cache/windows/sp02-sale-visual-scenario.json').write_text(text, encoding='utf-8', newline='\n')
env.cr.commit()
print(json.dumps(report, ensure_ascii=True))
