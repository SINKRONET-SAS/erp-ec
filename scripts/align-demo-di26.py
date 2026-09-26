"""DI26-B.4, DI26-E.5 y DI26-E.6 sobre la demo local (nunca sobre fundador ni los pilotos).

1. Marca como empresa de ensayo la empresa ficticia que comparte el RUC real de SINKRONET (DI26-12): sus anexos salen con
   el prefijo ENSAYO-NO-PRESENTAR.
2. Retira de la demo las aplicaciones ajenas al producto aprovisionado (DI26-16) sin tocar nada de lo que necesita un
   módulo erpec_*: se calcula el cierre de dependencias descendentes y se aborta si alcanzaría a un módulo propio.
3. Desactiva el usuario de ensayo que seguía activo (P3).

Respalda la base con pg_dump antes de cambiar nada. Requiere que la demo ya tenga los módulos erpec_* actualizados
(scripts/update-instance.py demo).

Uso:
    python scripts/align-demo-di26.py [--dry-run]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
PG_DUMP = Path('C:/Program Files/PostgreSQL/17/bin/pg_dump.exe')
INSTANCE = 'demo'
TEST_COMPANY_VAT = '1793235327001'
TEST_USERS = ['selfservice_test_2']
# Aplicaciones raíz ajenas al producto; Odoo desinstala también lo que depende de ellas.
FOREIGN_ROOTS = ['crm', 'fleet', 'im_livechat', 'website_blog', 'website_forum', 'mass_mailing', 'gamification', 'project']

SHELL = r'''
import json
dry = %(dry)s
Module = env['ir.module.module']
roots = Module.search([('name', 'in', %(roots)r), ('state', '=', 'installed')])
removed = roots | roots.downstream_dependencies()
own = removed.filtered(lambda m: m.name.startswith('erpec_'))
assert not own, 'Retirar %%s alcanzaría módulos propios: %%s' %% (roots.mapped('name'), own.mapped('name'))
companies = env['res.company'].with_context(active_test=False).search([('vat', '=', %(vat)r), ('ec_test_company', '=', False)])
fundador_like = companies.filtered(lambda c: not c.name or 'ensayo' not in c.name.lower())
users = env['res.users'].with_context(active_test=False).search([('login', 'in', %(users)r), ('active', '=', True)])
result = {'retirar': sorted(removed.mapped('name')), 'empresasEnsayo': companies.mapped('name'),
          'empresasSinPalabraEnsayo': fundador_like.mapped('name'), 'usuariosDesactivados': users.mapped('login')}
if not dry:
    companies.write({'ec_test_company': True})
    users.write({'active': False})
    env.cr.commit()
    if roots:
        roots.button_immediate_uninstall()
    env.cr.commit()
print('RESULTADO ' + json.dumps(result, ensure_ascii=False))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    conf = STATE / INSTANCE / 'odoo.conf'
    password = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))['postgres']
    backup = None
    if not args.dry_run:
        backup = STATE / 'backups' / ('align-demo-di26-%s' % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
        backup.mkdir(parents=True, exist_ok=False)
        subprocess.run([str(PG_DUMP), '-h', '127.0.0.1', '-p', '55487', '-U', 'postgres', '-Fc', '-f', str(backup / 'erpec_demo.dump'),
                        'erpec_demo'], env={**os.environ, 'PGPASSWORD': password}, check=True)
    code = SHELL % {'dry': args.dry_run, 'roots': FOREIGN_ROOTS, 'vat': TEST_COMPANY_VAT, 'users': TEST_USERS}
    result = subprocess.run([str(PYTHON), str(ODOO), 'shell', '-c', str(conf), '--no-http', '--log-level=warn'], input=code,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT),
                            env={**os.environ, 'PYTHONUTF8': '1'})
    line = next((l for l in result.stdout.splitlines() if l.startswith('RESULTADO ')), None)
    if result.returncode != 0 or not line:
        print(result.stdout[-2000:], result.stderr[-3000:], file=sys.stderr)
        return 1
    outcome = json.loads(line[len('RESULTADO '):])
    outcome['respaldo'] = backup and str(backup.relative_to(ROOT)).replace('\\', '/')
    outcome['simulacion'] = args.dry_run
    print(json.dumps(outcome, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
