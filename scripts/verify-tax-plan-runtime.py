"""Verifica el plan instalado sin persistir escenarios ni documentos."""
import json
from pathlib import Path
from lxml import etree
if env.cr.dbname not in ('erpec_demo', 'ec_operational_7a74b3c051') or env.company.vat:
    raise RuntimeError('Solo entornos sintéticos autorizados.')
product = env['product.product'].search([('supplier_taxes_id', '!=', False), ('company_id', 'in', [False, env.company.id])], limit=1)
partner = env['res.partner'].search([('supplier_rank', '>', 0), ('company_id', 'in', [False, env.company.id])], limit=1)
assert product and partner
plan = env['erpec.tax.plan'].create({'name': 'Verificación temporal', 'product_id': product.id, 'partner_id': partner.id})
source = product.supplier_taxes_id._filter_taxes_by_company(env.company)
assert plan.source_tax_ids == source
assert plan.effective_tax_ids == plan.fiscal_position_id.map_tax(source)
assert etree.fromstring(plan.get_view(view_type='form')['arch']).xpath("//field[@name='detail']")
home = env['erpec.workspace'].action_home()
action = env['erpec.workspace'].browse(home['res_id']).with_context(erpec_area='tax_plan').action_area()
assert action['res_model'] == 'erpec.tax.plan'
for account in plan.account_ids:
    domain = account.action_open_related_taxes()['domain']
    assert env['account.tax'].search(domain) & plan.effective_tax_ids.flatten_taxes_hierarchy()
result = {'database': env.cr.dbname, 'planAction': action['id'], 'product': product.display_name,
          'source': source.mapped('name'), 'effective': plan.effective_tax_ids.mapped('name'),
          'accounts': plan.account_ids.mapped('code'), 'formCompiled': True,
          'nativeReverseLinks': True, 'businessRecordsCreated': False, 'scenarioRolledBack': True}
env.cr.rollback()
content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
assert content.encode('utf-8').decode('utf-8') == content
Path('.cache/windows/tax-plan-runtime-' + env.cr.dbname + '.json').write_text(content, encoding='utf-8', newline='\n')
print(json.dumps(result, ensure_ascii=True))
