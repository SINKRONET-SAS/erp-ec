"""Suite integrada en base, rol y filestore propios; nunca reutiliza recursos existentes."""
import argparse
import configparser
import json
import os
import re
import secrets
import socket
import subprocess
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
ADDONS = ','.join(str(p) for p in (ROOT / '.cache/odoo-community/addons', ROOT / '.cache/odoo-community/odoo/addons', ROOT / 'addons'))


def validate_name(name):
    if not re.fullmatch(r'ec_integrated_test_[a-z0-9_]{1,44}', name):
        raise ValueError('El nombre debe usar el prefijo reservado ec_integrated_test_.')
    return name


def free_port():
    """Puerto HTTP propio para cada ejecución: dos suites simultáneas no pueden compartir el 8069 de las pruebas HTTP."""
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def ensure_absent(cursor, name):
    validate_name(name)
    cursor.execute('SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=%s) OR EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)', [name, name])
    if cursor.fetchone()[0]:
        raise ValueError('La base o el rol ya existen; el ensayo no los reutiliza ni elimina.')


def cleanup_owned(connection, name, database_created, role_created):
    validate_name(name)
    cursor = connection.cursor()
    if database_created:
        cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', [name])
        row = cursor.fetchone()
        if row and row[0] != name:
            raise RuntimeError('Cambió el propietario de la base; limpieza bloqueada.')
        cursor.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
    if role_created:
        cursor.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(name)))


def assess(log, returncode, modules):
    summary = re.findall(r'odoo\.tests\.result: (\d+) failed, (\d+) error\(s\) of (\d+) tests', log)
    if not summary:
        raise ValueError('No existe resumen final de pruebas.')
    failed, errors, total = map(int, summary[-1])
    missing = [module for module in modules if not re.search(r'odoo\.tests\.stats: ' + re.escape(module) + r': [1-9]\d* tests', log)]
    if returncode or failed or errors or total <= 0 or missing:
        raise ValueError('Suite no aprobada: salida=%s fallos=%s errores=%s total=%s módulos sin pruebas=%s' % (returncode, failed, errors, total, missing))
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('modules', nargs='*')
    parser.add_argument('--python', default=str(ROOT / '.venv' / 'Scripts' / 'python.exe'))
    parser.add_argument('--name', default='ec_integrated_test_' + secrets.token_hex(6))
    parser.add_argument('--timeout', type=int, default=5400)
    args = parser.parse_args()
    name = validate_name(args.name)
    available = {p.name for p in (ROOT / 'addons').iterdir() if (p / '__manifest__.py').exists()}
    modules = args.modules or sorted(available)
    if not modules or set(modules) - available:
        raise ValueError('Se requieren módulos propios existentes.')
    cluster = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))
    role_password = secrets.token_urlsafe(24)
    conf_path = STATE / (name + '.conf')
    data_dir = STATE / 'test-data' / name

    def admin_connection():
        connection = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=cluster['postgres'], dbname='postgres')
        connection.autocommit = True
        return connection

    database_created = role_created = config_created = False
    connection = admin_connection()
    try:
        cursor = connection.cursor()
        ensure_absent(cursor, name)
        if conf_path.exists() or data_dir.exists():
            raise ValueError('Ya existen archivos del ensayo; utiliza otro nombre.')
        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)), [role_password])
        role_created = True
        cursor.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0 ENCODING %s OWNER {}').format(sql.Identifier(name), sql.Identifier(name)), ['UTF8'])
        database_created = True
        cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
        data_dir.mkdir(parents=True, exist_ok=False)
        config = configparser.ConfigParser(interpolation=None)
        config['options'] = {
            'db_host': '127.0.0.1', 'db_port': '55487', 'db_user': name, 'db_password': role_password, 'db_name': name,
            'addons_path': ADDONS, 'list_db': 'False', 'without_demo': 'all', 'logfile': str(STATE / (name + '.log')),
            'data_dir': str(data_dir), 'http_interface': '127.0.0.1', 'http_port': str(free_port()),
        }
        with open(conf_path, 'x', encoding='utf-8') as handle:
            config_created = True
            config.write(handle)
        tags = ','.join('/' + module for module in modules)
        result = subprocess.run([args.python, str(ODOO), '-c', str(conf_path), '-i', ','.join(modules), '--test-tags', tags, '--stop-after-init', '--no-http'],
                                cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8',
                                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}, timeout=args.timeout)
    finally:
        try:
            cleanup_owned(connection, name, database_created, role_created)
        finally:
            connection.close()
            if config_created:
                conf_path.unlink(missing_ok=True)
    # El filestore de ensayo se conserva dentro de .cache para diagnóstico; no contiene credenciales.
    log = (STATE / (name + '.log')).read_text(encoding='utf-8')
    try:
        total = assess(log, result.returncode, modules)
    except ValueError as error:
        print(str(error), 'Registro:', name + '.log')
        return 1
    omitted = len(re.findall(r'\bskipped\b', log))
    print('%d pruebas reportadas, 0 fallos, 0 errores, %d omisiones; base %s; registro %s.log' % (total, omitted, name, name))
    return 0


if __name__ == '__main__':
    sys.exit(main())
