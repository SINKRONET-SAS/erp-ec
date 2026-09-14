"""Ensayo de intersección por línea: planes distintos, impuestos nativos y bases consolidadas."""
from odoo import Command
import json
from pathlib import Path
if env.cr.dbname != 'ec_operational_7a74b3c051' or env.company.vat:
    raise RuntimeError('Solo copia sintética SP02 autorizada.')
if env.ref('erpec_sp02_intersection.purchase', raise_if_not_found=False):
    raise RuntimeError('El ensayo de intersección ya existe; conservarlo.')
account = env['account.account'].search([('code', '=', 'TXSP02CASE')], limit=1)
def tax(usage, amount, code, kind=None):
    group_type = 'withhold_' + kind + '_' + usage if kind else 'vat' + str(amount).zfill(2)
    group = env['account.tax.group'].search([('company_id', '=', env.company.id), ('l10n_ec_type', '=', group_type)], limit=1)
    if not group:
        raise RuntimeError('Falta grupo nativo: ' + group_type)
    reference = 'sri_retention_' + kind + '_' + code if kind else 'sri_iva_234_' + code
    result = env['account.tax'].create({'name': 'ENSAYO CRUCE · ' + ('Compra' if usage == 'purchase' else 'Venta') + ' · ' + ({'income': 'Renta', 'vat': 'Retención IVA'}.get(kind, 'IVA')) + ' ' + str(amount) + ' %',
        'type_tax_use': 'none' if kind else usage, 'amount': -amount if kind else amount,
        'tax_group_id': group.id, 'erpec_reference_id': env.ref('erpec_workspace.' + reference).id})
    (result.invoice_repartition_line_ids | result.refund_repartition_line_ids).filtered(
        lambda line: line.repartition_type == 'tax').account_id = account
    return result
records = {}
for operation, usage in [('purchase', 'purchase'), ('sale', 'sale')]:
    iva15, iva5 = tax(usage, 15, '4'), tax(usage, 5, '5')
    income = tax(usage, 10, '303', 'income') if operation == 'purchase' else env['account.tax']
    vat = tax(usage, 70, '2', 'vat') if operation == 'purchase' else env['account.tax']
    plans = env['erpec.tax.policy'].create([{'name': 'ENSAYO CRUCE · ' + ('Compra' if operation == 'purchase' else 'Venta') + ' · ' + side}
        for side in ('tercero', 'producto A', 'producto B')])
    for plan, taxes, ret in [(plans[0], iva15 | iva5, True), (plans[1], iva15, True), (plans[2], iva5, False)]:
        env['erpec.tax.case'].create({'name': plan.name, 'policy_id': plan.id, 'operation': operation,
            'tax_ids': [Command.set(taxes.ids)], 'income_withholding_ids': [Command.set(income.ids if ret else [])],
            'vat_withholding_ids': [Command.set(vat.ids if ret else [])], 'withholding_bases_confirmed': True})
    partner = env['res.partner'].create({'name': 'ENSAYO CRUCE · ' + ('proveedor' if operation == 'purchase' else 'cliente'),
        'erpec_policy_ids': [Command.set(plans[0].ids)]})
    products = env['product.product'].create([{'name': 'ENSAYO CRUCE · ' + operation + ' · artículo ' + name,
        'type': 'consu', 'erpec_policy_ids': [Command.set(plan.ids)],
        'taxes_id': [Command.clear()], 'supplier_taxes_id': [Command.clear()]}
        for name, plan in [('A', plans[1]), ('B', plans[2])]])
    rows = [(products[0], 100), (products[0], 50), (products[1], 100)]
    quantity = 'product_qty' if operation == 'purchase' else 'product_uom_qty'
    order = env[operation + '.order'].create({'partner_id': partner.id, 'order_line': [
        Command.create({'product_id': product.id, quantity: 1, 'price_unit': price}) for product, price in rows]})
    assert order.amount_tax == 27.5 and order.amount_total == 277.5
    records[operation] = order
    invoice = env['account.move'].create({'move_type': 'in_invoice' if operation == 'purchase' else 'out_invoice',
        'partner_id': partner.id, 'invoice_line_ids': [Command.create(
            {'product_id': product.id, 'quantity': 1, 'price_unit': price}) for product, price in rows]})
    assert invoice.amount_tax == 27.5 and invoice.amount_total == 277.5
    records[operation + '_invoice'] = invoice
    if operation == 'purchase':
        assert len(invoice.ec_withholding_ids) == 2
        assert invoice.ec_withholding_ids.filtered(lambda w: w.tax_kind == 'income').base_amount == 150
        assert invoice.ec_withholding_ids.filtered(lambda w: w.tax_kind == 'vat').base_amount == 22.5
for name, record in records.items():
    env['ir.model.data'].create({'module': 'erpec_sp02_intersection', 'name': name,
        'model': record._name, 'res_id': record.id, 'noupdate': True})
output = {'database': env.cr.dbname, 'records': {key: {'id': r.id, 'name': r.display_name} for key, r in records.items()},
    'actions': {key: env.ref(xmlid).id for key, xmlid in [('purchase', 'purchase.purchase_rfq'),
        ('sale', 'sale.action_quotations'), ('purchase_invoice', 'account.action_move_in_invoice_type'),
        ('sale_invoice', 'account.action_move_out_invoice_type')]},
    'taxTotal': 27.5, 'documentTotal': 277.5, 'incomeBase': 150, 'vatWithholdingBase': 22.5,
    'incomeEstimate': 15, 'vatEstimate': 15.75, 'posted': False}
text = json.dumps(output, ensure_ascii=False, indent=2) + '\n'
assert text.encode('utf-8').decode('utf-8') == text
Path('.cache/windows/sp02-intersection-seed.json').write_text(text, encoding='utf-8', newline='\n')
env.cr.commit()
print(json.dumps(output, ensure_ascii=True))
