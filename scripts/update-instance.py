"""Actualiza una o varias instancias locales sin dejar desfase de esquema (DI26-01).

Por instancia: respalda la base con pg_dump (y la copia de módulos si la instancia usa una propia), sincroniza esa
copia desde addons/ cuando corresponde, actualiza TODOS los módulos erpec_* instalados, comprueba el desfase con
scripts/check-schema-drift.py y, con --restart, reinicia su proceso para que cargue el código nuevo.

Uso:
    python scripts/update-instance.py fundador demo [--restart]
"""
import argparse
import configparser
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
PG_DUMP = Path('C:/Program Files/PostgreSQL/17/bin/pg_dump.exe')


def run(args, **kwargs):
    result = subprocess.run([str(a) for a in args], cwd=str(ROOT), **kwargs)
    if result.returncode != 0:
        raise RuntimeError('Falló: %s' % ' '.join(str(a) for a in args[:4]))
    return result


def options(name):
    parser = configparser.ConfigParser(interpolation=None)
    conf = STATE / name / 'odoo.conf'
    if not parser.read(conf, encoding='utf-8'):
        raise RuntimeError('No existe la instancia %s' % name)
    return conf, parser['options']


def installed_modules(opts, password):
    connection = psycopg2.connect(host=opts.get('db_host', '127.0.0.1'), port=opts.get('db_port', '55487'), user='postgres',
                                  password=password, dbname=opts['db_name'])
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM ir_module_module WHERE state = 'installed' AND name LIKE 'erpec\\_%%' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def own_addons(name, opts):
    own = (STATE / name / 'addons').resolve()
    paths = [Path(p.strip()).resolve() for p in opts['addons_path'].split(',')]
    return own if own in paths else None


def restart(name, conf):
    stopped = 0
    for process in psutil.process_iter(['cmdline']):
        cmdline = process.info.get('cmdline') or []
        if str(conf) in cmdline and any(str(ODOO) == part for part in cmdline):
            process.terminate()
            stopped += 1
    time.sleep(2)
    run([PYTHON, ROOT / 'scripts' / 'supervisor-windows.py', '--once'])
    print('%s: %d proceso(s) reiniciado(s) por el supervisor' % (name, stopped))


def update(name, restart_after, password, stamp):
    conf, opts = options(name)
    modules = installed_modules(opts, password)
    backup = STATE / 'backups' / ('update-%s-%s' % (name, stamp))
    backup.mkdir(parents=True, exist_ok=False)
    run([PG_DUMP, '-h', opts.get('db_host', '127.0.0.1'), '-p', opts.get('db_port', '55487'), '-U', 'postgres', '-Fc',
         '-f', backup / (opts['db_name'] + '.dump'), opts['db_name']], env={**os.environ, 'PGPASSWORD': password})
    copy = own_addons(name, opts)
    if copy:
        shutil.copytree(copy, backup / 'addons', ignore=shutil.ignore_patterns('__pycache__'))
        for source in sorted((ROOT / 'addons').glob('erpec_*')):
            target = copy / source.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    run([PYTHON, ODOO, '-c', conf, '-u', ','.join(modules), '--stop-after-init', '--no-http', '--logfile=' + os.devnull],
        env={**os.environ, 'PYTHONUTF8': '1'})
    drift = subprocess.run([str(PYTHON), str(ROOT / 'scripts' / 'check-schema-drift.py'), name], cwd=str(ROOT),
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
    if restart_after:
        restart(name, conf)
    return {'instancia': name, 'modulos': modules, 'respaldo': str(backup.relative_to(ROOT)).replace('\\', '/'),
            'copiaSincronizada': bool(copy), 'desfase': drift.returncode == 0 and 'sin desfase' or drift.stdout.strip()[-400:]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('instances', nargs='+')
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    password = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))['postgres']
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    results = [update(name, args.restart, password, stamp) for name in args.instances]
    print(json.dumps(results, ensure_ascii=False, indent=1))
    return 0 if all(r['desfase'] == 'sin desfase' for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
