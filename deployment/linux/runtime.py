"""Arranque Linux aislado: base existente, identidad durable y filestore propio."""
import configparser
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit

import psycopg2

ROOT = Path('/opt/erpec')
DATA = Path('/var/data/odoo')
CONFIG = Path('/tmp/erpec.conf')


def setting(name, default=None):
    value = os.environ.get(name, default)
    if not value or any(char in value for char in '\r\n\x00'):
        raise ValueError('Configuración ausente o inválida: ' + name)
    return value


def configuration():
    url = urlsplit(setting('DATABASE_URL'))
    if url.scheme not in ('postgres', 'postgresql') or not url.hostname or not url.username or not url.password or url.query or url.fragment:
        raise ValueError('DATABASE_URL requiere una conexión PostgreSQL sin parámetros adicionales')
    database = unquote(url.path.lstrip('/'))
    if not re.fullmatch('[a-z][a-z0-9_]{0,62}', database):
        raise ValueError('Nombre de base no permitido')
    # Sin esta clave los secretos cifrados (certificado de firma, token PayPhone) quedarían atados a un
    # archivo en el mismo disco de datos; debe venir del entorno y respaldarse aparte.
    if len(setting('ERPEC_SECRET_KEY')) < 32:
        raise ValueError('ERPEC_SECRET_KEY debe tener al menos 32 caracteres')
    instance = setting('ERPEC_INSTANCE_ID')
    if not re.fullmatch('[a-f0-9]{32}', instance):
        raise ValueError('Identidad de instancia inválida')
    profile = (ROOT / 'profile').read_text().strip()
    if profile not in ('customer', 'controller'):
        raise ValueError('Perfil de imagen inválido')
    password = unquote(url.password)
    if any(char in password for char in '\r\n\x00'):
        raise ValueError('Contraseña PostgreSQL inválida')
    options = {
        'db_host': url.hostname, 'db_port': str(url.port or 5432),
        'db_user': unquote(url.username), 'db_password': password,
        'db_name': database, 'dbfilter': '^' + database + '$',
        'db_sslmode': setting('DB_SSLMODE', 'require'),
        'admin_passwd': setting('ODOO_MASTER_PASSWORD'),
        'list_db': 'False', 'proxy_mode': 'True', 'http_interface': '0.0.0.0',
        'http_port': setting('PORT', '10000'), 'workers': '0',
        'max_cron_threads': '1', 'without_demo': 'all',
        'data_dir': str(DATA), 'addons_path': '/opt/odoo/addons,/opt/odoo/odoo/addons,/opt/erpec/addons',
        'log_level': 'info', 'db_maxconn': '16',
    }
    if options['db_sslmode'] not in ('require', 'verify-full', 'disable') or not options['http_port'].isdigit() or not 1024 <= int(options['http_port']) <= 65535:
        raise ValueError('Puerto o modo TLS inválido')
    for value in options.values():
        if any(char in value for char in '\r\n\x00'):
            raise ValueError('Configuración contiene saltos de línea')
    return options, instance, profile


def connect(options):
    for attempt in range(30):
        try:
            return psycopg2.connect(host=options['db_host'], port=options['db_port'],
                user=options['db_user'], password=options['db_password'],
                dbname=options['db_name'], sslmode=options['db_sslmode'], connect_timeout=5)
        except psycopg2.OperationalError:
            if attempt == 29:
                raise RuntimeError('No se pudo conectar con la base asignada') from None
            print('Esperando PostgreSQL intento=' + str(attempt + 1), flush=True)
            time.sleep(2)


def main():
    options, instance, profile = configuration()
    DATA.mkdir(parents=True, exist_ok=True)
    # El bloqueo vive hasta terminar Odoo; impide compartir un disco entre procesos.
    lock = os.open(DATA / '.runtime.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError('El filestore ya está en uso por otra instancia') from None
    os.set_inheritable(lock, True)
    parser = configparser.ConfigParser(interpolation=None)
    parser['options'] = options
    os.umask(0o077)
    with CONFIG.open('w', encoding='utf-8') as stream:
        parser.write(stream)
    CONFIG.chmod(0o600)
    command = [sys.executable, '/opt/odoo/odoo-bin', '-c', str(CONFIG)]
    connection = connect(options)
    connection.autocommit = True
    marker = DATA / '.erpec-instance'
    try:
        with connection.cursor() as cursor:
            # Reserva por base, compartida por cualquier identidad que intente inicializarla.
            cursor.execute("SELECT pg_try_advisory_lock(18426004)")
            if not cursor.fetchone()[0]:
                raise RuntimeError('Otro proceso está preparando esta base')
            cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
            if cursor.fetchone()[0]:
                raise RuntimeError('Odoo no debe ejecutarse con un usuario PostgreSQL superusuario')
            cursor.execute("SELECT pg_get_userbyid(datdba)=current_user FROM pg_database WHERE datname=current_database()")
            if not cursor.fetchone()[0]:
                raise RuntimeError('La base debe pertenecer al usuario asignado a esta instancia')
            cursor.execute("SELECT to_regclass('public.erpec_runtime_identity')")
            present = cursor.fetchone()[0]
            if not present:
                cursor.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
                if cursor.fetchone()[0] or os.environ.get('ERPEC_BOOTSTRAP') != '1':
                    raise RuntimeError('Inicialización requiere base vacía y autorización ERPEC_BOOTSTRAP=1')
                if not marker.exists() and any(p.name != '.runtime.lock' for p in DATA.iterdir()):
                    raise RuntimeError('El disco contiene archivos sin identidad; revisar antes de inicializar')
                if marker.exists() and marker.read_text() != instance:
                    raise RuntimeError('El disco pertenece a otra instancia')
                cursor.execute('CREATE TABLE erpec_runtime_identity (singleton boolean PRIMARY KEY CHECK(singleton), instance varchar(32) NOT NULL, profile varchar(16) NOT NULL, ready boolean NOT NULL DEFAULT false)')
                cursor.execute('INSERT INTO erpec_runtime_identity(singleton,instance,profile) VALUES(true,%s,%s)', [instance, profile])
            cursor.execute('SELECT instance,profile,ready FROM erpec_runtime_identity WHERE singleton')
            identity = cursor.fetchone()
            if not identity or identity[:2] != (instance, profile):
                raise RuntimeError('La base pertenece a otra instancia o perfil')
            if marker.exists() and marker.read_text() != instance:
                raise RuntimeError('El disco pertenece a otra instancia')
            if identity[2] and not marker.exists():
                raise RuntimeError('Falta el filestore persistente; restaurar base y archivos conjuntamente')
            if not identity[2]:
                if os.environ.get('ERPEC_BOOTSTRAP') != '1':
                    raise RuntimeError('Inicialización incompleta: habilitar la recuperación explícita')
                setting('ODOO_ADMIN_PASSWORD')
                setting('ERPEC_COMPANY_NAME')
                marker.write_text(instance, encoding='utf-8')
                modules = 'base,l10n_ec,erpec_base,erpec_runtime' + (',erpec_selfservice' if profile == 'controller' else ',erpec_workspace,erpec_treasury,erpec_fiscal_sri,erpec_fiscal_withholding_sri,erpec_fiscal_guide_sri,erpec_field_routes,erpec_data_protection')
                subprocess.run(command + ['-i', modules, '--stop-after-init', '--no-http'], check=True, timeout=900)
                # Datos privados por entorno; nunca interpolar credenciales dentro del programa.
                code = """import os
env.ref('base.user_admin').write({'login':'admin','password':os.environ['ODOO_ADMIN_PASSWORD'],'tz':'America/Guayaquil'})
c=env.company
c.write({'name':os.environ['ERPEC_COMPANY_NAME'],'country_id':env.ref('base.ec').id})
env['account.chart.template'].try_loading('ec',c,install_demo=False)
lang=env['res.lang'].with_context(active_test=False).search([('code','=','es_EC')],limit=1)
env['base.language.install'].create({'lang_ids':[(6,0,lang.ids)],'overwrite':False}).lang_install()
env.ref('base.user_admin').write({'lang':'es_EC'})
w=env['erpec.workspace'].search([('company_id','=',c.id)],limit=1)
values={'platform':'Linux / contenedor','next_action':'Piloto Linux. Pendiente validar Render, HTTPS y recuperación administrada antes de producción.'}
if w:
    w.write(values)
else:
    env['erpec.workspace'].create(dict(values,company_id=c.id))
env.cr.commit()
"""
                subprocess.run([sys.executable, '/opt/odoo/odoo-bin', 'shell', '-c', str(CONFIG), '--no-http'], input=code, text=True, check=True, timeout=600)
                cursor.execute('UPDATE erpec_runtime_identity SET ready=true WHERE singleton')
    finally:
        connection.close()
    # No repetir la instalación ni restablecer el administrador después de un reinicio.
    os.environ.pop('ODOO_ADMIN_PASSWORD', None)
    print('Instancia Linux preparada correlationId=' + instance, flush=True)
    os.execv(sys.executable, command)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'code': 'LINUX_START_FAILED', 'statusCode': 503,
            'correlationId': os.environ.get('ERPEC_INSTANCE_ID', 'sin-identidad'),
            'userId': None, 'errorType': type(error).__name__,
            'message': str(error) if isinstance(error, (ValueError, RuntimeError)) else 'Error de arranque; revisar configuración y registros privados'}), flush=True)
        sys.exit(1)
