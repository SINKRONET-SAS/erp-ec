"""Verificación de configuración tributaria instalada, sin escrituras de negocio."""
import json
from pathlib import Path
from lxml import etree
if env.cr.dbname not in ('erpec_demo', 'ec_operational_7a74b3c051') or env.company.vat:
    raise RuntimeError('Solo entornos sintéticos autorizados.')
views = {}
actions = {}
for suffix in ('reference', 'policy', 'case', 'classification', 'assignment'):
    model = env['erpec.tax.' + suffix]
    views[suffix] = bool(etree.fromstring(model.get_view(view_type='form')['arch']))
    actions[suffix] = env.ref('erpec_workspace.tax_' + suffix + '_action').id
reference = env.ref('erpec_workspace.sri_iva_234_4')
assert reference.code == '4'
assert '2.34' in reference.version
assert env['erpec.tax.reference'].search_count([('family', '=', 'IVA · impuesto 2 · tabla 17')]) == 9
scenario_arch = env['erpec.tax.plan'].get_view(view_type='form')['arch']
assert 'planned_account_ids' in scenario_arch and 'case_status' in scenario_arch
home_arch = env['erpec.workspace'].get_view(view_id=env.ref('erpec_workspace.home_form').id, view_type='form')['arch']
assert 'Configurar planes y casos' in home_arch
for model, view in [('res.partner', 'base.view_partner_form'), ('product.template', 'product.product_template_form_view')]:
    assert 'erpec_tax_type_id' in env[model].get_view(view_id=env.ref(view).id, view_type='form')['arch']
for model, view in [('purchase.order', 'purchase.purchase_order_form'), ('sale.order', 'sale.view_order_form'), ('account.move', 'account.view_move_form')]:
    assert 'erpec_retention_ids' in env[model].get_view(view_id=env.ref(view).id, view_type='form')['arch']
assert 'erpec_reference_id' in env['account.tax'].get_view(view_id=env.ref('account.view_tax_form').id, view_type='form')['arch']
assert env['erpec.tax.reference'].search_count([('category', '=', 'income')]) == 123
assert env['erpec.tax.reference'].search_count([('category', '=', 'vat')]) == 8
for kind in ('income', 'vat'):
    actions[kind + '_details'] = env.ref('erpec_workspace.tax_' + kind + '_detail_action').id
    assert 'planned_' + kind + '_withholding_ids' in scenario_arch
scenario = env.ref('erpec_sp02_cases.scenario', raise_if_not_found=False)
result = {'database': env.cr.dbname, 'views': views, 'actions': actions,
    'ivaReferences': 9, 'incomeReferences': 123, 'vatWithholdingReferences': 8, 'homeConfigurationLink': True, 'nativeDetailAndClassificationFields': True,
    'businessWrites': False, 'automaticDocumentApplication': True}
if scenario:
    assert scenario.case_id == env.ref('erpec_sp02_cases.case')
    assert scenario.planned_account_ids.code == 'TXSP02CASE'
    assert 'DIFERENCIA' in scenario.case_status
    assert scenario.case_id.note.startswith('Ensayo visual SP02:')
    assert len(scenario.planned_income_withholding_ids) == 2
    assert len(scenario.planned_vat_withholding_ids) == 1
    assert scenario.withholding_account_ids.code == 'TXSP02CASE'
    assert len(scenario.case_id.policy_id.case_ids) == 2
    assert not scenario.case_id._configuration_issue()
    result.update({'scenarioId': scenario.id, 'caseId': scenario.case_id.id, 'plannedAccount': scenario.planned_account_ids.code,
                   'uiNotePersisted': True, 'differenceVisible': True})
cross = env.ref('erpec_sp02_intersection.purchase', raise_if_not_found=False)
if cross:
    sale = env.ref('erpec_sp02_intersection.sale')
    bill = env.ref('erpec_sp02_intersection.purchase_invoice')
    invoice = env.ref('erpec_sp02_intersection.sale_invoice')
    for document in (cross, sale, bill, invoice):
        assert document.state == 'draft'
        assert document.amount_tax == 27.5 and document.amount_total == 277.5
    assert len(bill.ec_withholding_ids) == 2
    assert bill.ec_withholding_ids.filtered(lambda w: w.tax_kind == 'income').base_amount == 150
    assert bill.ec_withholding_ids.filtered(lambda w: w.tax_kind == 'vat').base_amount == 22.5
    assert 'Línea 2' in bill.erpec_retention_summary
    result['intersection'] = {'differentPlans': True, 'linesPerDocument': 3, 'nativeTaxTotal': 27.5,
        'purchaseWithholdingGroups': 2, 'incomeBase': 150, 'vatBase': 22.5, 'posted': False}
env.cr.rollback()
text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
assert text.encode('utf-8').decode('utf-8') == text
Path('.cache/windows/tax-cases-runtime-' + env.cr.dbname + '.json').write_text(text, encoding='utf-8', newline='\n')
print(json.dumps(result, ensure_ascii=True))
