"""Ejecuta las pruebas de un módulo sobre una COPIA aislada de una instancia sembrada (DI25-07.1): las pruebas de Tesorería que se
omiten en una base limpia por requerir la demo sembrada corren aquí con sus datos. Base, rol y directorio propios (prefijo
reservado ec_restore_drill_), copia por pg_dump/pg_restore, sin cron ni correo; solo elimina lo que creó. La instancia de origen
solo se lee.

Uso: python scripts/test-seeded-copy.py --instance demo --module erpec_treasury [--report ruta.json]
"""
import argparse
import configparser
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
PG_BIN = Path('C:/Program Files/PostgreSQL/17/bin')


def run(args, env=None, **kw):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding='utf-8', errors='replace', env={**os.environ, **(env or {})}, **kw)
    if result.returncode != 0:
        raise RuntimeError('Falló %s: %s' % (Path(str(args[0])).name, (result.stderr or result.stdout)[-400:]))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', default='demo')
    parser.add_argument('--module', required=True)
    parser.add_argument('--report', default=None)
    args = parser.parse_args()
    if not re.fullmatch(r'erpec_[a-z0-9_]+', args.module):
        raise ValueError('Módulo inválido.')
    source = configparser.ConfigParser(interpolation=None)
    source.read(STATE / args.instance / 'odoo.conf', encoding='utf-8')
    options = source['options']
    db, data_dir = options['db_name'], Path(options['data_dir'])
    cluster = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))
    pg_env = {'PGPASSWORD': cluster['postgres']}
    name = 'ec_restore_drill_' + secrets.token_hex(4)
    password = secrets.token_urlsafe(20)
    work = STATE / 'restore-drill' / name
    dump = Path(tempfile.gettempdir()) / (name + '.dump')
    created_db = created_role = False
    connection = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=cluster['postgres'], dbname='postgres')
    connection.autocommit = True
    report = {'instance': args.instance, 'module': args.module, 'copy': name}
    try:
        cursor = connection.cursor()
        run([PG_BIN / 'pg_dump.exe', '-h', '127.0.0.1', '-p', '55487', '-U', 'postgres', '-Fc', '-f', dump, db], env=pg_env)
        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)), [password])
        created_role = True
        cursor.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0 ENCODING %s OWNER {}').format(sql.Identifier(name), sql.Identifier(name)), ['UTF8'])
        created_db = True
        run([PG_BIN / 'pg_restore.exe', '-h', '127.0.0.1', '-p', '55487', '-U', 'postgres', '-d', name, '--no-owner', '--no-privileges', '--role=' + name, dump], env=pg_env)
        (work / 'data' / 'filestore').mkdir(parents=True)
        shutil.copytree(data_dir / 'filestore' / db, work / 'data' / 'filestore' / name)
        conf = configparser.ConfigParser(interpolation=None)
        conf['options'] = {'db_host': '127.0.0.1', 'db_port': '55487', 'db_user': name, 'db_password': password, 'db_name': name, 'dbfilter': '^' + name + '$',
                           'addons_path': options['addons_path'], 'list_db': 'False', 'without_demo': 'all', 'workers': '0', 'max_cron_threads': '0',
                           'data_dir': str(work / 'data'), 'logfile': str(work / 'odoo.log')}
        conf_path = work / 'odoo.conf'
        with open(conf_path, 'w', encoding='utf-8') as handle:
            conf.write(handle)
        result = subprocess.run([str(PYTHON), str(ODOO), '-c', str(conf_path), '-u', args.module, '--test-tags', '/' + args.module, '--stop-after-init', '--no-http'],
                                cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace', env={**os.environ, 'PYTHONUTF8': '1'}, timeout=3600)
        log = (work / 'odoo.log').read_text(encoding='utf-8', errors='replace')
        summary = re.findall(r'odoo\.tests\.result: (\d+) failed, (\d+) error\(s\) of (\d+) tests', log)
        stats = re.findall(r'odoo\.tests\.stats: ' + re.escape(args.module) + r': (\d+) tests', log)
        skipped = re.findall(r'skipped', log)
        report.update({'exit': result.returncode, 'summary': list(summary[-1]) if summary else None, 'module_tests': stats[-1] if stats else None,
                       'skip_mentions_in_log': len(skipped), 'passed': bool(summary) and result.returncode == 0 and summary[-1][0] == '0' and summary[-1][1] == '0' and int(summary[-1][2]) > 0})
        report['skipped_lines'] = [l[-160:] for l in log.splitlines() if 'skip' in l.lower()][:8]
    finally:
        cursor = connection.cursor()
        if created_db:
            cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', [name])
            row = cursor.fetchone()
            if row and row[0] == name:
                cursor.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
        if created_role:
            cursor.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(name)))
        connection.close()
        shutil.rmtree(work, ignore_errors=True)
        dump.unlink(missing_ok=True)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        Path(args.report).write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0 if report.get('passed') else 1


if __name__ == '__main__':
    sys.exit(main())
