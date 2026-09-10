"""Trabajador Windows local. No acepta comandos, rutas ni destinos del navegador."""
import argparse
import configparser
import io
import shutil
import json
import msvcrt
import os
import pathlib
import re
import secrets
import socket
import subprocess
import time
import xmlrpc.client
import psutil
import psycopg2
from psycopg2 import sql

socket.setdefaulttimeout(20)

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
SOURCE = ROOT / '.cache/odoo-community'
PYTHON = ROOT / '.venv/Scripts/python.exe'

def write(path, text):
    if text.encode('utf-8').decode('utf-8') != text:
        raise ValueError('UTF-8 inválido')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text, encoding='utf-8', newline='\n')
    temporary.replace(path)

def rpc(url, database, password):
    common = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common')
    uid = common.authenticate(database, 'admin', password, {})
    if not uid:
        raise ValueError('No se autenticó el operador o la instancia')
    models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
    return lambda model, method, args: models.execute_kw(database, uid, password, model, method, args)

def matching_process(directory):
    pidfile = directory/'pid'
    if not pidfile.exists():
        return None
    pid = int(pidfile.read_text())
    if not psutil.pid_exists(pid):
        return None
    process = psutil.Process(pid)
    arguments = process.cmdline()
    if str(directory/'odoo.conf') not in arguments or str(SOURCE/'odoo-bin') not in arguments:
        raise ValueError('El proceso registrado no pertenece a esta instancia')
    return process

def operate(job):
    instance = job['instance']
    if not re.fullmatch('[a-f0-9]{32}', instance) or not isinstance(job['id'], int) or not 1 <= job['id'] <= 119:
        raise ValueError('Identificador fuera del rango del piloto')
    directory = STATE/'instances'/instance
    directory.mkdir(parents=True, exist_ok=True)
    process = matching_process(directory)
    if job['desired'] == 'stop':
        if process:
            process.terminate()
            process.wait(30)
        print('Instancia suspendida; datos conservados correlationId='+instance)
        return
    if job['desired'] != 'start':
        raise ValueError('Operación no permitida')
    secretfile = directory/'credentials.json'
    if secretfile.exists():
        private = json.loads(secretfile.read_text(encoding='utf-8'))
    else:
        private = {'database':secrets.token_urlsafe(32), 'admin':secrets.token_urlsafe(24), 'manager':secrets.token_urlsafe(32)}
        write(secretfile, json.dumps(private))
    name = 'erp_'+instance
    port = 8180+job['id']
    url = f'http://127.0.0.1:{port}'
    customer_addons = directory/'addons'
    shutil.copytree(ROOT/'addons/erpec_base', customer_addons/'erpec_base', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    expected_addons = f'{SOURCE/"addons"},{SOURCE/"odoo/addons"},{customer_addons}'
    if (directory/'odoo.conf').exists():
        config = configparser.ConfigParser(interpolation=None)
        config.read(directory/'odoo.conf', encoding='utf-8')
        if config['options']['addons_path'] != expected_addons:
            config['options']['addons_path'] = expected_addons
            content = io.StringIO()
            config.write(content)
            write(directory/'odoo.conf', content.getvalue())
            if process:
                process.terminate()
                process.wait(30)
                process = None
    if not (directory/'initialized.json').exists():
        cluster = json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
        connection = psycopg2.connect(host='127.0.0.1',port=55487,dbname='postgres',user='postgres',password=cluster['postgres'])
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', [name])
                if not cursor.fetchone():
                    cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)), [private['database']])
                cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', [name])
                owner = cursor.fetchone()
                if owner and owner[0] != name:
                    raise ValueError('La base existente no pertenece a la instancia')
                if not owner:
                    cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(name),sql.Identifier(name)))
                cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
        finally:
            connection.close()
        config = f'[options]\nadmin_passwd = {private["manager"]}\ndb_host = 127.0.0.1\ndb_port = 55487\ndb_user = {name}\ndb_password = {private["database"]}\ndb_name = {name}\ndbfilter = ^{name}$\nlist_db = False\nhttp_interface = 127.0.0.1\nhttp_port = {port}\nworkers = 0\nmax_cron_threads = 1\nwithout_demo = all\ndata_dir = {directory/"data"}\naddons_path = {SOURCE/"addons"},{SOURCE/"odoo/addons"},{customer_addons}\nlogfile = {directory/"odoo.log"}\n'
        write(directory/'odoo.conf', config)
        subprocess.run([str(PYTHON),str(SOURCE/'odoo-bin'),'-c',str(directory/'odoo.conf'),'-i','base,l10n_ec,erpec_base','--stop-after-init','--no-http'],check=True,timeout=600)
        code = "import json\nfrom pathlib import Path\np=json.loads(Path("+repr(str(secretfile))+").read_text())\nenv.ref('base.user_admin').write({'login':'admin','password':p['admin']})\nc=env.company\nc.write({'name':"+repr(job['company'])+",'country_id':env.ref('base.ec').id})\nenv['account.chart.template'].try_loading('ec',c,install_demo=False)\nlang=env['res.lang'].with_context(active_test=False).search([('code','=','es_EC')],limit=1)\nenv['base.language.install'].create({'lang_ids':[(6,0,lang.ids)],'overwrite':False}).lang_install()\nenv.ref('base.user_admin').write({'lang':'es_EC','tz':'America/Guayaquil'})\nif not env['erpec.workspace'].search_count([('company_id','=',c.id)]):\n    env['erpec.workspace'].create({'company_id':c.id})\nenv.cr.commit()\n"
        subprocess.run([str(PYTHON),str(SOURCE/'odoo-bin'),'shell','-c',str(directory/'odoo.conf'),'--no-http'],input=code,text=True,check=True,timeout=300)
        write(directory/'initialized.json', json.dumps({'instance':instance,'database':name}))
    if not process:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',port)) == 0:
                raise ValueError('El puerto está ocupado por un proceso no registrado')
        process = subprocess.Popen([str(PYTHON),str(SOURCE/'odoo-bin'),'-c',str(directory/'odoo.conf')],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
        write(directory/'pid', str(process.pid))
    for attempt in range(60):
        try:
            call = rpc(url,name,private['admin'])
            if call('erpec.workspace','search_count',[[]]) != 1:
                raise ValueError('La instancia no tiene la configuración esperada')
            print('Instancia autenticada y disponible correlationId='+instance)
            return
        except (OSError, xmlrpc.client.Error) as error:
            if attempt == 59:
                raise
            print('Esperando salud de instancia correlationId='+instance+' intento='+str(attempt+1))
            time.sleep(1)

def main():
    # Un único trabajador por host evita ejecutar dos operaciones físicas simultáneas.
    with (STATE/'worker.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        private = json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
        call = rpc('http://127.0.0.1:8169','erpec_a',private['admin_a'])
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
    watch = parser.parse_args().watch
    while True:
        try:
            main()
        except Exception as error:
            if not watch:
                raise
            print(json.dumps({'code':'WORKER_UNAVAILABLE','statusCode':503,'correlationId':'operador-local','errorType':type(error).__name__}), flush=True)
        if not watch:
            break
        time.sleep(10)
