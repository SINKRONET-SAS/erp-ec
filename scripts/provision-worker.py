"""Trabajador Windows local. No acepta comandos, rutas ni destinos del navegador.

Cada cliente corre en el servidor compartido (scripts/shared-tenant-server.py), no en un
proceso ni puerto propio: ver docs/PLAN_HAIKY_MULTITENANT.md. Este trabajador crea la base de
PostgreSQL del cliente PROPIEDAD DEL ROL COMPARTIDO erp_tenants (Odoo abre cada base con un
único db_user/db_password de proceso; no hay credencial por base en su capa de conexión, así
que un rol nuevo por cliente no sería alcanzable por el servidor compartido). El aislamiento
real entre clientes es la separación física de bases de PostgreSQL (una conexión a una base no
puede leer otra) y la contraseña de aplicación Odoo (res.users) propia de cada base -- nunca
una credencial de PostgreSQL por cliente. Instala los módulos con una llamada de un solo uso
(sin proceso persistente) y activa/suspende el acceso con ALTER DATABASE ... ALLOW_CONNECTIONS.
SHARED_URL debe coincidir con ENDPOINT_SCHEME de addons/erpec_provision/models/provision.py."""
import argparse
import json
import msvcrt
import pathlib
import re
import secrets
import socket
import subprocess
import time
import xmlrpc.client
import psycopg2
from psycopg2 import sql

socket.setdefaulttimeout(20)

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
SOURCE = ROOT / '.cache/odoo-community'
PYTHON = ROOT / '.venv/Scripts/python.exe'
SHARED_URL = 'http://{}.localtest.me:8200'
TENANT_STATEMENT_TIMEOUT = '30s'  # Ver nota junto a su uso: único techo por inquilino posible en Windows hoy.

def write(path, text):
    if text.encode('utf-8').decode('utf-8') != text:
        raise ValueError('UTF-8 inválido')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text, encoding='utf-8', newline='\n')
    temporary.replace(path)

def rpc(url, database, password, login='admin'):
    common = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common')
    uid = common.authenticate(database, login, password, {})
    if not uid:
        raise ValueError('No se autenticó el operador o la instancia')
    models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
    return lambda model, method, args: models.execute_kw(database, uid, password, model, method, args)

def _cluster_connection(cluster):
    connection = psycopg2.connect(host='127.0.0.1', port=55487, dbname='postgres', user='postgres', password=cluster['postgres'])
    connection.autocommit = True
    return connection

def set_allow_connections(cluster, database, allowed):
    # ALTER DATABASE no admite %s para ALLOW_CONNECTIONS (no es un valor, es una palabra de la
    # DDL); allowed es un bool interno, no dato de usuario, por lo que interpolarlo es seguro.
    connection = _cluster_connection(cluster)
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL('ALTER DATABASE {} WITH ALLOW_CONNECTIONS {}').format(
                sql.Identifier(database), sql.SQL('true' if allowed else 'false')))
            if not allowed:
                cursor.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid <> pg_backend_pid()', [database])
    finally:
        connection.close()

def operate(job):
    instance = job['instance']
    if not re.fullmatch('[a-f0-9]{32}', instance) or not isinstance(job['id'], int) or not 1 <= job['id'] <= 119:
        raise ValueError('Identificador fuera del rango del piloto')
    directory = STATE/'instances'/instance
    directory.mkdir(parents=True, exist_ok=True)
    name = 'erp_'+instance
    cluster = json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
    if job['desired'] == 'stop':
        set_allow_connections(cluster, name, False)
        print('Instancia suspendida; datos conservados correlationId='+instance)
        return
    if job['desired'] != 'start':
        raise ValueError('Operación no permitida')
    secretfile = directory/'credentials.json'
    if secretfile.exists():
        private = json.loads(secretfile.read_text(encoding='utf-8'))
    else:
        private = {'admin': secrets.token_urlsafe(24)}
        write(secretfile, json.dumps(private))
    tenants = json.loads((STATE/'shared/credentials.json').read_text(encoding='utf-8'))
    addons_path = f'{SOURCE/"addons"},{SOURCE/"odoo/addons"},{ROOT/"addons"}'
    if not (directory/'initialized.json').exists():
        connection = _cluster_connection(cluster)
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', [name])
                owner = cursor.fetchone()
                if owner and owner[0] != tenants['db_user']:
                    raise ValueError('La base existente no pertenece al rol compartido de clientes')
                if not owner:
                    cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(name), sql.Identifier(tenants['db_user'])))
                    # Techo por inquilino disponible en Windows: Odoo --workers (CPU/memoria/
                    # tiempo por petición) requiere os.fork(), inexistente en Windows -- solo
                    # aplicará al desplegar en Render (Linux). Mientras tanto, statement_timeout
                    # evita que una consulta de un cliente cuelgue indefinidamente al servidor
                    # compartido y afecte a los demás.
                    cursor.execute(sql.SQL('ALTER DATABASE {} SET statement_timeout = %s').format(sql.Identifier(name)), [TENANT_STATEMENT_TIMEOUT])
                cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
        finally:
            connection.close()
        # Instalación de un solo uso contra el clúster compartido: sin -c/odoo.conf propio,
        # sin proceso persistente ni puerto dedicado a este cliente. Usa el rol compartido
        # erp_tenants (ver shared-tenant-server.py) porque el servidor compartido solo puede
        # abrir bases con ESE db_user/db_password de proceso.
        db_args = ['--db_host', '127.0.0.1', '--db_port', '55487', '--db_user', tenants['db_user'],
                    '--db_password', tenants['db_password'], '--addons-path', addons_path]
        # erpec_payroll siembra sola la versión NACIONAL-2026 al instalarse (post_init_hook,
        # ver hooks.py) sin depender de ningún diario ni del plan de cuentas -- seguro instalarlo
        # aquí, antes de que el bloque de abajo cargue el plan EC y renombre la empresa.
        subprocess.run([str(PYTHON), str(SOURCE/'odoo-bin'), '-d', name, *db_args,
                         '-i', 'base,l10n_ec,erpec_base,erpec_payroll,erpec_field_routes',
                         '--stop-after-init', '--no-http'],
                        check=True, timeout=600)
        code = ("import json\nfrom pathlib import Path\n"
                "p=json.loads(Path(" + repr(str(secretfile)) + ").read_text())\n"
                "env.ref('base.user_admin').write({'login':'admin','password':p['admin']})\n"
                "c=env.company\n"
                "c.write({'name':" + repr(job['company']) + ",'country_id':env.ref('base.ec').id})\n"
                "env['account.chart.template'].try_loading('ec',c,install_demo=False)\n"
                "lang=env['res.lang'].with_context(active_test=False).search([('code','=','es_EC')],limit=1)\n"
                "env['base.language.install'].create({'lang_ids':[(6,0,lang.ids)],'overwrite':False}).lang_install()\n"
                "env.ref('base.user_admin').write({'lang':'es_EC','tz':'America/Guayaquil'})\n"
                "env.ref('base.user_admin').write({'groups_id':[(4,env.ref('account.group_account_user').id),(4,env.ref('account.group_account_manager').id)]})\n"
                "if not env['erpec.workspace'].search_count([('company_id','=',c.id)]):\n"
                "    env['erpec.workspace'].create({'company_id':c.id})\n"
                "env.cr.commit()\n")
        subprocess.run([str(PYTHON), str(SOURCE/'odoo-bin'), 'shell', '-d', name, *db_args, '--no-http'],
                        input=code, text=True, check=True, timeout=300)
        write(directory/'initialized.json', json.dumps({'instance': instance, 'database': name}))
    else:
        set_allow_connections(cluster, name, True)
    url = SHARED_URL.format(instance)
    for attempt in range(60):
        try:
            call = rpc(url, name, private['admin'])
            if call('erpec.workspace', 'search_count', [[]]) != 1:
                raise ValueError('La instancia no tiene la configuración esperada')
            print('Instancia autenticada y disponible correlationId='+instance)
            return
        except (OSError, xmlrpc.client.Error) as error:
            if attempt == 59:
                raise
            print('Esperando salud de instancia correlationId='+instance+' intento='+str(attempt+1))
            time.sleep(1)

# Dos operadores válidos: la instancia operadora real (empresa del Fundador, OP07) y el
# piloto sintético erpec_a, usado solo por scripts/verify-provision.py para ensayos
# repetibles sin tocar datos reales. Ambos comparten el mismo servidor compartido de
# clientes (scripts/shared-tenant-server.py); solo cambia dónde vive la cola de contratos.
OPERATORS = {
    'fundador': {'url': 'http://127.0.0.1:8199', 'database': 'erpec_fundador', 'login': 'fundador',
                 'credentials': STATE / 'fundador/credentials.json', 'password_key': 'admin'},
    'a': {'url': 'http://127.0.0.1:8169', 'database': 'erpec_a', 'login': 'admin',
          'credentials': STATE / 'credentials.json', 'password_key': 'admin_a'},
}


def main(operator='fundador'):
    config = OPERATORS[operator]
    # Un único trabajador por host evita ejecutar dos operaciones físicas simultáneas.
    with (STATE/'worker.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        private = json.loads(config['credentials'].read_text(encoding='utf-8'))
        call = rpc(config['url'], config['database'], private[config['password_key']], config['login'])
        job = call('erpec.provision','claim_next',[])
        if not job:
            print('No hay trabajos pendientes')
            return
        try:
            operate(job)
        except Exception as error:
            # No devolver contraseñas, comandos ni respuestas de proveedores al frontend.
            print(json.dumps({'code':'PROVISION_FAILED','statusCode':500,'correlationId':job['instance'],'userId':'operador-local','errorType':type(error).__name__}))
            call('erpec.provision','finish',[[job['id']],job['token'],False])
            raise RuntimeError('Falló el aprovisionamiento; revisar los logs locales de la instancia') from None
        call('erpec.provision','finish',[[job['id']],job['token'],True])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', action='store_true', help='Procesar la cola cada diez segundos')
    parser.add_argument('--operator', choices=list(OPERATORS), default='fundador',
                         help='fundador = instancia operadora real; a = piloto sintético de scripts/verify-provision.py')
    args = parser.parse_args()
    watch = args.watch
    while True:
        try:
            main(args.operator)
        except Exception as error:
            if not watch:
                raise
            print(json.dumps({'code':'WORKER_UNAVAILABLE','statusCode':503,'correlationId':'operador-local','errorType':type(error).__name__}), flush=True)
        if not watch:
            break
        time.sleep(10)
