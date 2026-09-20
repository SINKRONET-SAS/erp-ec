"""Suite integrada: instala TODOS los módulos erpec_* juntos en una base nueva y aislada,
ejecuta todas sus pruebas y elimina la base al terminar.

Los módulos se probaban por separado y por eso un defecto de combinación (p. ej. nómina
bloqueando notas de crédito) pasaba inadvertido. Ejecutar antes de cerrar cada fase.

Uso (desde la raíz del repositorio):
    python scripts/test-integrated.py                    # todos los módulos
    python scripts/test-integrated.py erpec_fiscal_sri   # solo esos (con sus dependencias)
    python scripts/test-integrated.py --python RUTA      # otro intérprete (p. ej. un entorno de prueba)

Sale con código 0 solo si hay 0 fallos y 0 errores. Requiere el clúster local
(.cache/windows/credentials.json). El registro completo queda en .cache/windows/<base>.log.
"""
import argparse
import configparser
import json
import re
import secrets
import subprocess
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
ADDONS = ','.join(str(p) for p in (ROOT / '.cache/odoo-community/addons', ROOT / '.cache/odoo-community/odoo/addons', ROOT / 'addons'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('modules', nargs='*', help='módulos a instalar y probar; por defecto todos los erpec_*')
    parser.add_argument('--python', default=str(ROOT / '.venv' / 'Scripts' / 'python.exe'))
    parser.add_argument('--name', default='ec_integrated_test_' + secrets.token_hex(3))
    parser.add_argument('--timeout', type=int, default=5400)
    args = parser.parse_args()

    modules = args.modules or sorted(p.name for p in (ROOT / 'addons').iterdir() if (p / '__manifest__.py').exists())
    name = args.name
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', name):
        sys.exit('Nombre de base no permitido')
    cluster = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))
    role_password = secrets.token_urlsafe(24)
    conf_path = STATE / (name + '.conf')

    def admin_connection():
        connection = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=cluster['postgres'], dbname='postgres')
        connection.autocommit = True
        return connection

    def cleanup():
        # Sin `with connection`: en autocommit no debe abrirse una transacción (DROP DATABASE la prohíbe).
        connection = admin_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
            cursor.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(name)))
        finally:
            connection.close()
        conf_path.unlink(missing_ok=True)

    connection = admin_connection()
    try:
        connection.cursor().execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER CREATEDB NOCREATEROLE').format(sql.Identifier(name)), [role_password])
    finally:
        connection.close()
    try:
        user_connection = psycopg2.connect(host='127.0.0.1', port=55487, user=name, password=role_password, dbname='postgres')
        user_connection.autocommit = True
        with user_connection.cursor() as cursor:
            cursor.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0 ENCODING %s OWNER {}').format(sql.Identifier(name), sql.Identifier(name)), ['UTF8'])
        user_connection.close()
        config = configparser.ConfigParser(interpolation=None)
        config['options'] = {
            'db_host': '127.0.0.1', 'db_port': '55487', 'db_user': name, 'db_password': role_password, 'db_name': name,
            'addons_path': ADDONS, 'list_db': 'False', 'without_demo': 'all', 'logfile': str(STATE / (name + '.log')),
        }
        with open(conf_path, 'w', encoding='utf-8') as handle:
            config.write(handle)
        tags = ','.join('/' + module for module in modules)
        result = subprocess.run([args.python, str(ODOO), '-c', str(conf_path), '-i', ','.join(modules), '--test-tags', tags, '--stop-after-init', '--no-http'],
                                cwd=str(ROOT), capture_output=True, text=True, timeout=args.timeout)
    finally:
        cleanup()

    log = (STATE / (name + '.log')).read_text(encoding='utf-8', errors='replace')
    summary = re.findall(r'odoo\.tests\.result: (\d+) failed, (\d+) error\(s\) of (\d+) tests', log)
    if not summary:
        print('Sin resumen de pruebas; código de salida', result.returncode, '\n', result.stderr[-1500:])
        return 2
    failed, errors, total = map(int, summary[-1])
    print('%d pruebas: %d fallos, %d errores (base %s, log %s.log)' % (total, failed, errors, name, name))
    for line in re.findall(r'(?:ERROR|FAIL): [\w.]+', log)[:20]:
        print('  ', line)
    return 0 if not failed and not errors and result.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
