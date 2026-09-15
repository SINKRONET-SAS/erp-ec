"""Servidor Odoo compartido para clientes aprovisionados: una base de datos por cliente,
ruteada por subdominio via db_filter (%d = primera etiqueta del host), sin proceso ni puerto
dedicado por cliente. Reemplaza el modelo de OP07 (un proceso por cliente), que no escala en
costo en Render. Ver docs/PLAN_HAIKY_MULTITENANT.md.

Crear una base nueva no requiere reiniciar este proceso: Odoo consulta PostgreSQL en vivo en
cada petición (odoo/service/db.py, list_dbs). Suspender/reactivar un cliente tampoco reinicia
este proceso: se hace con ALTER DATABASE ... WITH ALLOW_CONNECTIONS false/true, ejecutado por
scripts/provision-worker.py.

Rol de PostgreSQL: Odoo abre cada base con un único db_user/db_password de proceso (no hay
credencial por base de datos en su capa de conexión) -- por eso todas las bases de clientes
las posee UN rol compartido (erp_tenants), creado aquí, no un rol nuevo por cliente como en el
modelo anterior. El aislamiento real entre clientes no depende de permisos de rol: Postgres no
permite consultar una base desde una conexión abierta a otra (separación física de
almacenamiento), y cada cliente solo tiene acceso HTTP/XML-RPC con su propia contraseña de
aplicación Odoo (tabla res.users de su base), nunca una credencial de PostgreSQL."""
import argparse
import configparser
import json
import secrets
import socket
import subprocess
from pathlib import Path

import psutil
import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
DIRECTORY = STATE / 'shared'
SOURCE = ROOT / '.cache/odoo-community'
PYTHON = ROOT / '.venv/Scripts/python.exe'
PORT = 8200
DBFILTER = '^erp_%d$'
TENANTS_ROLE = 'erp_tenants'


def write(path, text):
    if text.encode('utf-8').decode('utf-8') != text:
        raise ValueError('UTF-8 inválido')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def bootstrap():
    conf_path = DIRECTORY / 'odoo.conf'
    if conf_path.exists():
        print('El servidor compartido ya está inicializado:', conf_path)
        return
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    cluster = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))
    tenants_password = secrets.token_urlsafe(32)
    connection = psycopg2.connect(host='127.0.0.1', port=55487, dbname='postgres', user='postgres', password=cluster['postgres'])
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', [TENANTS_ROLE])
            if not cursor.fetchone():
                cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(TENANTS_ROLE)), [tenants_password])
            else:
                cursor.execute(sql.SQL('ALTER ROLE {} LOGIN PASSWORD %s').format(sql.Identifier(TENANTS_ROLE)), [tenants_password])
    finally:
        connection.close()
    write(DIRECTORY / 'credentials.json', json.dumps({'db_user': TENANTS_ROLE, 'db_password': tenants_password}))
    addons_path = ','.join([str(SOURCE / 'addons'), str(SOURCE / 'odoo/addons'), str(ROOT / 'addons')])
    config = configparser.ConfigParser(interpolation=None)
    config['options'] = {
        'admin_passwd': secrets.token_urlsafe(32),
        'db_host': '127.0.0.1', 'db_port': '55487',
        'db_user': TENANTS_ROLE, 'db_password': tenants_password,
        'dbfilter': DBFILTER, 'list_db': 'False',
        'http_interface': '127.0.0.1', 'http_port': str(PORT),
        'workers': '0', 'max_cron_threads': '1',
        'without_demo': 'all',
        'data_dir': str(DIRECTORY / 'data'),
        'addons_path': addons_path,
        'logfile': str(DIRECTORY / 'odoo.log'),
    }
    with open(conf_path, 'w', encoding='utf-8') as handle:
        config.write(handle)
    print('Servidor compartido inicializado:', conf_path)


def matching_process():
    pidfile = DIRECTORY / 'pid'
    if not pidfile.exists():
        return None
    pid = int(pidfile.read_text())
    if not psutil.pid_exists(pid):
        return None
    process = psutil.Process(pid)
    arguments = process.cmdline()
    conf_path = DIRECTORY / 'odoo.conf'
    if str(conf_path) not in arguments or str(SOURCE / 'odoo-bin') not in arguments:
        raise ValueError('El proceso registrado no pertenece al servidor compartido')
    return process


def start():
    conf_path = DIRECTORY / 'odoo.conf'
    if not conf_path.exists():
        raise RuntimeError('Ejecuta primero: shared-tenant-server.py bootstrap')
    if matching_process():
        print('El servidor compartido ya está en ejecución')
        return
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', PORT)) == 0:
            raise RuntimeError('Puerto %d ocupado; comprobar el proceso antes de iniciar' % PORT)
    process = subprocess.Popen([str(PYTHON), str(SOURCE / 'odoo-bin'), '-c', str(conf_path)],
                                cwd=str(ROOT), creationflags=subprocess.CREATE_NO_WINDOW)
    write(DIRECTORY / 'pid', str(process.pid))
    print('Servidor compartido iniciado en http://127.0.0.1:%d (pid %d)' % (PORT, process.pid))


def restart():
    process = matching_process()
    if process:
        process.terminate()
        process.wait(30)
        (DIRECTORY / 'pid').unlink(missing_ok=True)
    start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['bootstrap', 'start', 'restart'])
    action = parser.parse_args().action
    {'bootstrap': bootstrap, 'start': start, 'restart': restart}[action]()
