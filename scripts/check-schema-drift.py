"""Detecta desfase de esquema (DI26-01): carga el registro de Odoo con el código que usa cada instancia y lista los
campos almacenados sin columna en su base. Solo lee; nunca confirma cambios en la base.

Uso:
    python scripts/check-schema-drift.py                 # todas las instancias de .cache/windows con odoo.conf
    python scripts/check-schema-drift.py fundador demo   # instancias concretas
Sale con 1 si alguna instancia tiene desfase o no se pudo revisar.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'

SHELL_CODE = '''import json
missing = []
cr = env.cr
for name, model in env.registry.models.items():
    if not model._auto or model._abstract:
        continue
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s", [model._table])
    columns = {row[0] for row in cr.fetchall()}
    if not columns:
        if (model._module or '').startswith('erpec'):
            missing.append('%s (tabla %s ausente)' % (name, model._table))
        continue
    for field_name, field in model._fields.items():
        if field.store and field.column_type and field_name not in columns:
            missing.append('%s.%s' % (name, field_name))
print('DESFASE ' + json.dumps(missing, ensure_ascii=False))
cr.rollback()
'''


def instances(selected):
    names = selected or sorted(p.parent.name for p in STATE.glob('*/odoo.conf'))
    return [(name, STATE / name / 'odoo.conf') for name in names]


def check(name, conf):
    result = subprocess.run([str(PYTHON), str(ODOO), 'shell', '-c', str(conf), '--no-http', '--logfile=' + os.devnull],
                            input=SHELL_CODE, capture_output=True, text=True, encoding='utf-8', errors='replace',
                            cwd=str(ROOT), env={**os.environ, 'PYTHONUTF8': '1'}, timeout=900)
    for line in result.stdout.splitlines():
        if line.startswith('DESFASE '):
            return json.loads(line[len('DESFASE '):])
    raise RuntimeError('No se pudo revisar %s: %s' % (name, (result.stderr or result.stdout)[-300:]))


def main():
    report, failed = {}, False
    for name, conf in instances(sys.argv[1:]):
        try:
            missing = check(name, conf)
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            report[name] = {'error': str(error)}
            failed = True
            continue
        report[name] = {'desfase': missing}
        failed = failed or bool(missing)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
