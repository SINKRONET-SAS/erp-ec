"""Entorno Windows local aislado. Secretos y datos permanecen en .cache."""
import argparse
import json
import os
import pathlib
import secrets
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
PG = pathlib.Path(os.environ.get('ERPEC_PG_BIN', 'C:/Program Files/PostgreSQL/17/bin'))
PORT = 55487
PYTHON = ROOT / '.venv/Scripts/python.exe'
SOURCE = ROOT / '.cache/odoo-community'


def write(p, text):
    if text.encode('utf-8').decode('utf-8') != text:
        raise ValueError('UTF-8 inválido')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def credentials():
    return json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))


def bootstrap():
    if (STATE / 'credentials.json').exists():
        raise ValueError('El entorno ya existe; no se sobrescriben datos ni credenciales')
    STATE.mkdir(parents=True, exist_ok=True)
    private = {'postgres': secrets.token_urlsafe(32), 'a': secrets.token_urlsafe(32), 'b': secrets.token_urlsafe(32), 'admin_a': secrets.token_urlsafe(24), 'admin_b': secrets.token_urlsafe(24)}
    write(STATE / 'credentials.json', json.dumps(private))
    write(STATE / 'init-password.txt', private['postgres'])
    run([PG / 'initdb.exe', '-D', STATE / 'pgdata', '-U', 'postgres', '--pwfile', STATE / 'init-password.txt', '-A', 'scram-sha-256', '--encoding=UTF8', '--locale=C'])
    write(STATE / 'pgdata/postgresql.auto.conf', "listen_addresses = '127.0.0.1'\nport = 55487\n")
    (STATE / 'init-password.txt').unlink()
    start_database()
    import psycopg2
    from psycopg2 import sql
    connection = psycopg2.connect(host='127.0.0.1', port=PORT, user='postgres', password=private['postgres'], dbname='postgres')
    connection.autocommit = True
    with connection.cursor() as cursor:
        for tenant, webport in [('a', 8169), ('b', 8170)]:
            name = 'erpec_' + tenant
            cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)), [private[tenant]])
            cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {} ENCODING \'UTF8\' TEMPLATE template0').format(sql.Identifier(name), sql.Identifier(name)))
            cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
            config = f'[options]\nadmin_passwd = {secrets.token_urlsafe(32)}\ndb_host = 127.0.0.1\ndb_port = {PORT}\ndb_user = {name}\ndb_password = {private[tenant]}\ndb_name = {name}\ndbfilter = ^{name}$\nlist_db = False\nhttp_interface = 127.0.0.1\nhttp_port = {webport}\nworkers = 0\nmax_cron_threads = 1\nwithout_demo = all\ndata_dir = {STATE / tenant / "data"}\naddons_path = {SOURCE / "addons"},{SOURCE / "odoo/addons"},{ROOT / "addons"}\nlogfile = {STATE / tenant / "odoo.log"}\n'
            write(STATE / tenant / 'odoo.conf', config)
    connection.close()
    for tenant in ['a', 'b']:
        run([PYTHON, SOURCE / 'odoo-bin', '-c', STATE / tenant / 'odoo.conf', '-i', 'base,l10n_ec,erpec_base', '--stop-after-init', '--no-http'])
        code = "import json\nfrom pathlib import Path\np = json.loads(Path(" + repr(str(STATE / 'credentials.json')) + ").read_text())\nenv.ref('base.user_admin').write({'login': 'admin', 'password': p['admin_" + tenant + "']})\nc=env.company\nc.write({'name':'ERP EC piloto " + tenant.upper() + "','country_id':env.ref('base.ec').id})\nenv['account.chart.template'].try_loading('ec',c,install_demo=False)\nenv['erpec.workspace'].create({'company_id':c.id})\nenv.cr.commit()\n"
        run([PYTHON, SOURCE / 'odoo-bin', 'shell', '-c', STATE / tenant / 'odoo.conf', '--no-http'], input=code, text=True)
    print('Dos organizaciones inicializadas; credenciales locales en .cache/windows/credentials.json')


def start_database():
    status = subprocess.run([str(PG / 'pg_ctl.exe'), '-D', str(STATE / 'pgdata'), 'status'], capture_output=True)
    if status.returncode == 0:
        print('PostgreSQL del piloto ya está activo')
    else:
        run([PG / 'pg_ctl.exe', '-D', STATE / 'pgdata', '-l', STATE / 'postgres.log', '-w', 'start'])


def start():
    start_database()
    import socket
    for tenant, port in [('a', 8169), ('b', 8170)]:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise ValueError(f'Puerto {port} ocupado; comprobar el proceso antes de iniciar')
        process = subprocess.Popen([str(PYTHON), str(SOURCE / 'odoo-bin'), '-c', str(STATE / tenant / 'odoo.conf')], cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
        write(STATE / tenant / 'pid', str(process.pid))
    print('Inicio solicitado: http://127.0.0.1:8169 y http://127.0.0.1:8170; verificar salud antes de usar')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['bootstrap', 'start'])
    action = parser.parse_args().action
    try:
        bootstrap() if action == 'bootstrap' else start()
    except Exception as error:
        print('No se pudo preparar el piloto Windows:', str(error), file=sys.stderr)
        sys.exit(1)
