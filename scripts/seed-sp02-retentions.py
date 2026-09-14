"""Añade retenciones sintéticas al caso visual existente, solo en copia SP02."""
from odoo import Command
if env.cr.dbname != 'ec_operational_7a74b3c051' or env.company.vat:
    raise RuntimeError('Solo copia sintética SP02 autorizada.')
case = env.ref('erpec_sp02_cases.case')
if case.income_withholding_ids or case.vat_withholding_ids:
    raise RuntimeError('El ensayo ya tiene retenciones; conservarlo.')
account = env['account.account'].search([('code', '=', 'TXSP02CASE')], limit=1)
for kind, code, amount in [('income', '303', 10), ('income', '307', 3), ('vat', '2', 70)]:
    group = env['account.tax.group'].search([('company_id', '=', env.company.id),
        ('l10n_ec_type', '=', 'withhold_' + kind + '_purchase')], limit=1)
    if not group:
        raise RuntimeError('Falta grupo nativo de retención.')
    tax = env['account.tax'].create({'name': 'ENSAYO · retención ' + kind + ' · ' + code,
        'type_tax_use': 'none', 'amount': -amount, 'tax_group_id': group.id,
        'erpec_reference_id': env.ref('erpec_workspace.sri_retention_' + kind + '_' + code).id})
    (tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids).filtered(
        lambda line: line.repartition_type == 'tax').account_id = account
    case.write({kind + '_withholding_ids': [Command.link(tax.id)]})
assert not case._configuration_issue()
case.copy({'name': 'ENSAYO · segundo caso con varios detalles', 'note': 'Demostración de cardinalidad; no asignado a operaciones reales.'})
assert len(case.policy_id.case_ids) == 2
env.cr.commit()
print('Retenciones sintéticas añadidas; sin pedidos ni asientos modificados.')
