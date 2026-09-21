"""Auditoría reproducible de la demo; ejecutar con Odoo shell y --no-http.

Solo lee registros. Emite JSON entre marcas DI25_AUDIT_BEGIN/END, sin credenciales.
No restaura ejemplos editados ni convierte coincidencia aritmética en aceptación.
"""
import hashlib
import json
from datetime import datetime, timezone
from lxml import etree
from odoo.addons.erpec_payroll.engine import money
from odoo.addons.erpec_payroll.tax_review import CASES, BASE_INPUTS
from odoo.addons.erpec_payroll.parameters_ec2026 import PARAMS

if 'env' not in globals():
    raise RuntimeError('Ejecutar dentro de Odoo shell, en la base demo autorizada.')
if env.cr.dbname != 'erpec_demo' or env.company.vat or 'DEMO' not in env.company.name.upper():
    raise RuntimeError('La verificación está limitada a erpec_demo y empresa DEMO sin RUC.')

queries = {
    'account_move': 'SELECT id,state,amount_total,amount_residual FROM account_move ORDER BY id',
    'account_move_line': 'SELECT id,move_id,debit,credit,balance FROM account_move_line ORDER BY id',
    'payroll_period': 'SELECT id,state,move_id FROM erpec_payroll_period ORDER BY id',
    'payroll_line': 'SELECT id,period_id,result FROM erpec_payroll_line ORDER BY id',
}

def fingerprints():
    result = {}
    for key, query in queries.items():
        env.cr.execute(query)
        rows = env.cr.fetchall()
        result[key] = {'count': len(rows), 'sha256': hashlib.sha256(
            json.dumps(rows, default=str, sort_keys=True).encode('utf-8')).hexdigest()}
    return result

before = fingerprints()
checks, problems = [], []
for key, case in CASES.items():
    record = env.ref('erpec_review_demo.tax_review_%s_%s' % (env.company.id, key), raise_if_not_found=False)
    if not record or record._name != 'erpec.payroll.tax.review' or record.company_id != env.company:
        problems.append({'case': key, 'reason': 'Falta el ejemplo o pertenece a otro recurso.'})
        continue
    data, parameters, result = record._review_values()
    original = data == dict(BASE_INPUTS, **case[1])
    if any(parameters.get(field) != PARAMS[field] for field in ('tax_brackets', 'expense_limit', 'rebate_rate')):
        problems.append({'case': key, 'reason': 'La política difiere de los parámetros fiscales 2026 de referencia.'})
    actual = [float(money(result[field])) for field in ('annual_base', 'tax_caused', 'annual_tax', 'pending_tax')]
    expected = [float(money(value)) for value in case[2:6]]
    ok = original and actual == expected
    checks.append({'case': key, 'record': record.id, 'originalInputs': original,
                   'actual': actual, 'expected': expected, 'passed': ok})
    if not ok:
        problems.append({'case': key, 'reason': 'Entradas editadas o diferencia aritmética; se conserva el ejemplo.'})
    if 'rebate_applied' in result and not 0 <= result['rebate_applied'] <= result['tax_caused']:
        problems.append({'case': key, 'reason': 'Rebaja aplicada fuera del impuesto causado.'})

views = []
for model in ('hr.employee', 'erpec.payroll.period', 'erpec.payroll.tax.review', 'erpec.payroll.rdep'):
    architecture = env[model].get_view(view_type='form')['arch']
    etree.fromstring(architecture.encode('utf-8'))
    views.append(model)
after = fingerprints()
if before != after:
    problems.append({'reason': 'La auditoría alteró una huella económica.'})
report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'database': env.cr.dbname,
          'moduleVersion': env['ir.module.module'].search([('name', '=', 'erpec_payroll')]).latest_version,
          'cases': checks, 'viewsCompiled': views, 'fingerprintQueries': queries,
          'fingerprintSerialization': 'Odoo cursor + json.dumps(rows, default=str, sort_keys=True), UTF-8',
          'economicBefore': before, 'economicAfter': after,
          'problems': problems, 'passed': not problems, 'expertAccepted': False,
          'limits': ['Solo aritmética y carga de vistas; no aceptación legal ni ensayo visual.',
                     'No se valida autenticidad sanitaria ni compatibilidad oficial del RDEP 2026.']}
print('DI25_AUDIT_BEGIN')
print(json.dumps(report, ensure_ascii=False, indent=2))
print('DI25_AUDIT_END')
env.cr.rollback()
if problems:
    raise RuntimeError('La auditoría DI25 detectó incidencias; revisar el informe sin sobrescribir datos.')
