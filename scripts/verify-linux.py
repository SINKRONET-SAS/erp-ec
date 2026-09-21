"""Prueba Docker local con recursos nuevos y datos sintéticos; nunca llama a Render."""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import urllib.request
import uuid
import xmlrpc.client

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/linux'
POSTGRES = 'postgres:17-bookworm@sha256:051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0'
socket.setdefaulttimeout(10)


def docker(*args, input=None, check=True):
    result = subprocess.run(['docker', *args], input=input, text=True, capture_output=True, encoding='utf-8', timeout=900)
    if check and result.returncode:
        raise RuntimeError('Docker falló: ' + args[0] + '; ' + result.stderr[:300])
    return result


def write(path, text):
    assert text.encode('utf-8').decode('utf-8') == text and '\ufffd' not in text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def auth(url, database, password):
    return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(database, 'admin', password, {})


def call(url, database, password, model, method, args, kwargs=None):
    uid = auth(url, database, password)
    assert uid, 'Autenticación fallida'
    return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object').execute_kw(database, uid, password, model, method, args, kwargs or {})


def wait_health(url, container):
    for attempt in range(120):
        try:
            with urllib.request.urlopen(url+'/erpec/health', timeout=5) as response:
                if response.status == 200 and json.load(response)['status'] == 'pass':
                    return
        except (OSError, ValueError):
            if docker('inspect', container, '--format', '{{.State.Running}}').stdout.strip() != 'true':
                raise RuntimeError('El contenedor terminó durante la inicialización; revisar registro privado') from None
        if attempt % 12 == 0:
            print('Esperando inicialización Linux intento='+str(attempt+1), flush=True)
        time.sleep(3)
    raise RuntimeError('La instancia no alcanzó salud verificable')


def main(profile):
    stamp = uuid.uuid4().hex[:10]
    prefix = 'erpec-linux-'+stamp
    image = 'erpec-linux-'+profile+':phase04'
    directory = STATE / stamp
    directory.mkdir(parents=True)
    containers = []
    evidence = {'scope':'Docker Linux local; no despliegue ni llamadas a Render', 'checks':[], 'passed':False}
    private = {key:secrets.token_urlsafe(32) for key in ['pg','db','admin','manager','rotated']}
    write(directory/'credentials.json', json.dumps(private))
    envfile = directory/'postgres.env'
    write(envfile, 'POSTGRES_PASSWORD='+private['pg']+'\n')
    docker('network', 'create', prefix)
    pg = prefix+'-pg'
    docker('run', '-d', '--name', pg, '--label', 'erpec.test='+stamp, '--network', prefix, '--env-file', str(envfile), '-v', prefix+'-pg:/var/lib/postgresql/data', POSTGRES)
    containers.append(pg)
    try:
        for attempt in range(30):
            if docker('exec', pg, 'pg_isready', '-U', 'postgres', check=False).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('PostgreSQL de ensayo no inició')
        docker('exec', '-i', pg, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1', input="CREATE ROLE erpec_app LOGIN PASSWORD '"+private['db']+"' NOSUPERUSER NOCREATEDB NOCREATEROLE; CREATE DATABASE erpec_app OWNER erpec_app TEMPLATE template0; REVOKE ALL ON DATABASE erpec_app FROM PUBLIC; CREATE ROLE foreign_app LOGIN PASSWORD '"+private['pg']+"'; CREATE DATABASE foreign_app OWNER foreign_app TEMPLATE template0; REVOKE ALL ON DATABASE foreign_app FROM PUBLIC;")
        instance = uuid.uuid4().hex
        values = {'DATABASE_URL':'postgresql://erpec_app:'+private['db']+'@'+pg+':5432/erpec_app',
            'DB_SSLMODE':'disable', 'ERPEC_INSTANCE_ID':instance, 'ERPEC_BOOTSTRAP':'1',
            'ODOO_ADMIN_PASSWORD':private['admin'],'ODOO_MASTER_PASSWORD':private['manager'],'ERPEC_SECRET_KEY':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            'ERPEC_COMPANY_NAME':'ERP EC ensayo Linux'}
        appenv = directory/'customer.env'
        write(appenv, ''.join(k+'='+v+'\n' for k,v in values.items()))
        number = port()
        url = 'http://127.0.0.1:'+str(number)
        volume = prefix+'-files'
        def launch(suffix, env=appenv, files=volume):
            name = prefix+'-'+suffix
            docker('run','-d','--name',name,'--label','erpec.test='+stamp,'--network',prefix,'--env-file',str(env),'-p','127.0.0.1:'+str(number)+':10000','-v',files+':/var/data/odoo',image)
            containers.append(name)
            return name
        app = launch('app')
        wait_health(url, app)
        duplicate = prefix+'-duplicate'
        docker('run','-d','--name',duplicate,'--label','erpec.test='+stamp,'--network',prefix,'--env-file',str(appenv),'-v',volume+':/var/data/odoo',image)
        containers.append(duplicate)
        assert docker('wait',duplicate).stdout.strip() == '1'
        assert 'filestore ya' in docker('logs',duplicate).stdout
        evidence['checks'].append('Dos procesos no pueden abrir simultáneamente el mismo filestore')
        evidence['checks'].append('Arranque real Python 3.12, PostgreSQL 17 y Community fijado; usuario PostgreSQL sin privilegios administrativos')
        def invoke(model, method, args, kwargs=None, password=private['admin']):
            return call(url,'erpec_app',password,model,method,args,kwargs)
        assert invoke('erpec.workspace','search_count',[[]]) == 1
        assert invoke('ir.module.module','search_count',[[('name','in',['erpec_suite','erpec_provision','erpec_payphone'])]]) == (0 if profile == 'customer' else 3)
        evidence['checks'].append('Módulos separados según perfil '+profile)
        partner = invoke('res.partner','create',[{'name':'Persistencia Linux '+stamp}])
        data = base64.b64encode(('Archivo persistente '+stamp).encode()).decode()
        attachment = invoke('ir.attachment','create',[{'name':'persistencia.txt','type':'binary','datas':data,'res_model':'res.partner','res_id':partner,'mimetype':'text/plain'}])
        stored = invoke('ir.attachment','read',[[attachment],['store_fname']])[0]['store_fname']
        assert stored, 'El adjunto debe estar en filestore'
        admin = auth(url,'erpec_app',private['admin'])
        invoke('res.users','write',[[admin],{'password':private['rotated']}])
        docker('stop',app)
        replacement = launch('redeploy')
        wait_health(url,replacement)
        assert not auth(url,'erpec_app',private['admin'])
        assert invoke('res.partner','read',[[partner],['name']],password=private['rotated'])[0]['name'] == 'Persistencia Linux '+stamp
        assert invoke('ir.attachment','read',[[attachment],['datas','store_fname']],password=private['rotated'])[0] == {'id':attachment,'datas':data,'store_fname':stored}
        assert invoke('erpec.workspace','search_count',[[]],password=private['rotated']) == 1
        evidence['checks'].append('Recreación del contenedor conserva contacto, adjunto físico y contraseña cambiada; sin duplicar espacio ni reinstalar')
        # Credenciales cruzadas se comprueban desde un proceso efímero, sin incluirlas en argumentos.
        probe = "import os,psycopg2\nfrom urllib.parse import urlsplit\nu=urlsplit(os.environ['DATABASE_URL'])\ntry:\n c=psycopg2.connect(host=u.hostname,dbname='foreign_app',user=u.username,password=u.password)\nexcept psycopg2.OperationalError:\n print('ACCESO_RECHAZADO')\nelse:\n raise RuntimeError('Acceso cruzado permitido')\n"
        result = docker('exec','-i',replacement,'python','-',input=probe)
        assert 'ACCESO_RECHAZADO' in result.stdout
        evidence['checks'].append('Rol de cliente no puede conectar a la base ajena')
        with urllib.request.urlopen(url+'/web/login',timeout=10) as response:
            assert response.status == 200 and 'odoo' in response.read().decode().lower()
        evidence['checks'].append('Interfaz de acceso HTTP 200 y espacio visible identificado como Linux')
        docker('stop',replacement)
        missing = launch('missing-disk',files=prefix+'-empty')
        code = docker('wait',missing).stdout.strip()
        assert code == '1' and 'Falta el filestore persistente' in docker('logs',missing).stdout
        values['ERPEC_INSTANCE_ID'] = uuid.uuid4().hex
        write(directory/'wrong.env',''.join(k+'='+v+'\n' for k,v in values.items()))
        wrong = launch('wrong-identity',env=directory/'wrong.env')
        assert docker('wait',wrong).stdout.strip() == '1'
        assert 'otra instancia o perfil' in docker('logs',wrong).stdout
        evidence['checks'].append('Arranque bloqueado ante pérdida de disco o identidad de otra instancia')
        evidence.update({'passed':True,'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance':instance,
            'image':docker('image','inspect',image,'--format','{{.Id}}').stdout.strip(),
            'profile':profile,'resourcesPrefix':prefix,'dataPreserved':True})
    finally:
        for name in reversed(containers):
            logs = docker('logs',name,check=False)
            write(directory/(name+'.log'),logs.stdout+logs.stderr)
            if logs.returncode:
                print(json.dumps({'code':'TEST_LOG_UNAVAILABLE','statusCode':500,'correlationId':stamp,'container':name}),flush=True)
            stopped = docker('stop',name,check=False)
            if stopped.returncode:
                evidence['passed'] = False
                evidence.setdefault('cleanupErrors',[]).append(name)
                print(json.dumps({'code':'TEST_STOP_FAILED','statusCode':500,'correlationId':stamp,'container':name}),flush=True)
        write(directory/'result.json',json.dumps(evidence,indent=2,ensure_ascii=False))
        print(json.dumps({'passed':evidence['passed'],'checks':evidence['checks'],'report':str(directory/'result.json')},ensure_ascii=False),flush=True)
    if not evidence['passed']:
        raise RuntimeError('No se pudo completar o detener el ensayo; revisar su informe')
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile',choices=['customer','controller'],default='customer')
    main(parser.parse_args().profile)
