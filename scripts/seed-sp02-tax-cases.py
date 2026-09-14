"""Escenario sintético de configuración para revisión visual en copia SP02."""
from odoo import Command
if env.cr.dbname != 'ec_operational_7a74b3c051' or env.company.vat:
    raise RuntimeError('Solo copia sintética SP02 autorizada.')
if env.ref('erpec_sp02_cases.scenario', raise_if_not_found=False):
    raise RuntimeError('El escenario ya existe; conservarlo.')
company = env.company
account = env['account.account'].create({'name': 'Impuesto · ensayo de casos', 'code': 'TXSP02CASE',
    'account_type': 'liability_current', 'company_ids': [Command.set(company.ids)]})
native_tax = env['account.tax'].search([('company_id', '=', company.id), ('type_tax_use', '=', 'purchase'), ('amount', '=', 15), ('erpec_reference_id', '=', False)], limit=1)
if not native_tax:
    raise RuntimeError('Falta el impuesto nativo de referencia para el grupo del ensayo.')
tax = env['account.tax'].create({'name': 'ENSAYO · IVA 15 % · caso compra', 'amount': 15, 'type_tax_use': 'purchase',
    'tax_group_id': native_tax.tax_group_id.id, 'erpec_reference_id': env.ref('erpec_workspace.sri_iva_234_4').id})
(tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
    lambda line: line.repartition_type == 'tax').account_id = account
partner_type = env['erpec.tax.classification'].create({'name': 'ENSAYO · proveedor tipo A', 'kind': 'partner'})
product_type = env['erpec.tax.classification'].create({'name': 'ENSAYO · artículo tipo A', 'kind': 'product'})
partner = env['res.partner'].create({'name': 'ENSAYO · proveedor de casos', 'erpec_tax_type_id': partner_type.id})
product = env['product.product'].create({'name': 'ENSAYO · artículo de casos', 'erpec_tax_type_id': product_type.id,
    'supplier_taxes_id': [Command.clear()], 'taxes_id': [Command.clear()]})
policy = env['erpec.tax.policy'].create({'name': 'ENSAYO SP02 · plan de compras',
    'note': 'Solo validación de configuración. No constituye clasificación tributaria de una operación real.'})
case = env['erpec.tax.case'].create({'name': 'ENSAYO · compra tipo A', 'policy_id': policy.id,
    'tax_ids': [Command.set(tax.ids)]})
assignment = env['erpec.tax.assignment'].create({'case_id': case.id, 'partner_type_id': partner_type.id, 'product_type_id': product_type.id})
scenario = env['erpec.tax.plan'].create({'name': 'ENSAYO · comparación de caso y operación',
    'partner_id': partner.id, 'product_id': product.id})
for name, record in [('scenario', scenario), ('policy', policy), ('case', case), ('assignment', assignment), ('tax', tax)]:
    env['ir.model.data'].create({'module': 'erpec_sp02_cases', 'name': name, 'model': record._name, 'res_id': record.id, 'noupdate': True})
assert scenario.case_id == case
assert 'DIFERENCIA' in scenario.case_status
env.cr.commit()
print('Escenario sintético de casos creado; ningún pedido ni asiento modificado.')
