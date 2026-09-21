"""Prepara casos editables de aceptación en una demo, sin modificar los existentes."""
from odoo.addons.erpec_payroll.tax_review import CASES, BASE_INPUTS
company = env.company
if company.vat or 'DEMO' not in company.name.upper():
    raise RuntimeError('Solo se permite preparar ensayos en una empresa DEMO sin RUC.')
policy = env['erpec.payroll.policy'].search([
    ('company_id', '=', company.id), ('year', '=', 2026), ('synthetic', '=', True)],
    order='state, id', limit=1)
if not policy:
    raise RuntimeError('Falta una política sintética 2026; revisar Versiones y autoridad.')
for key, case in CASES.items():
    identifier = 'tax_review_' + str(company.id) + '_' + key
    existing = env.ref('erpec_review_demo.'+identifier, raise_if_not_found=False)
    if existing:
        if existing._name != 'erpec.payroll.tax.review' or existing.company_id != company:
            raise RuntimeError('El identificador del ensayo pertenece a otro recurso.')
        print('Caso conservado: '+existing.name)
    else:
        record = env['erpec.payroll.tax.review'].create(dict(
            BASE_INPUTS, **case[1], name=case[0], company_id=company.id, policy_id=policy.id, scenario=key))
        env['ir.model.data'].create({'module': 'erpec_review_demo', 'name': identifier,
                                    'model': record._name, 'res_id': record.id, 'noupdate': True})
        print('Caso creado: '+record.name)
env.cr.commit()
