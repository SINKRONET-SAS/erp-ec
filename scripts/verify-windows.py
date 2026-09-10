"""Verifica aislamiento y restauración del piloto con datos sintéticos."""
import base64
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import uuid
import xmlrpc.client
import psycopg2
from psycopg2 import sql

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
PG = pathlib.Path(os.environ.get('ERPEC_PG_BIN', 'C:/Program Files/PostgreSQL/17/bin'))

def main():
    secrets = json.loads((STATE / 'credentials.json').read_text())
    checks = []
    def rpc(tenant, model, method, args, kwargs=None):
        url = 'http://127.0.0.1:' + ('8169' if tenant == 'a' else '8170')
        common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common')
        uid = common.authenticate('erpec_' + tenant, 'admin', secrets['admin_' + tenant], {})
        assert uid, 'No se pudo autenticar al administrador del piloto'
        objects = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')
        return objects.execute_kw('erpec_' + tenant, uid, secrets['admin_' + tenant], model, method, args, kwargs or {})
    for tenant, other in [('a', 'b'), ('b', 'a')]:
        try:
            connection = psycopg2.connect(host='127.0.0.1', port=55487, user='erpec_' + tenant, password=secrets[tenant], dbname='erpec_' + other)
        except psycopg2.OperationalError as error:
            assert 'permission denied' in str(error).lower(), 'El fallo debe corresponder a permisos de base'
        else:
            connection.close()
            raise AssertionError('Una credencial pudo abrir la base ajena')
        assert rpc(tenant, 'erpec.workspace', 'search_count', [[]]) == 1
        modules = rpc(tenant, 'ir.module.module', 'search_read', [[['name', 'in', ['erpec_base','l10n_ec']]]], {'fields':['name','state']})
        assert len(modules) == 2 and all(module['state'] == 'installed' for module in modules)
        charts = rpc(tenant, 'res.company', 'search_read', [[]], {'fields':['chart_template']})
        assert charts and charts[0]['chart_template'] == 'ec'
    checks.append('Dos bases y roles: acceso ajeno rechazado; módulos y plan contable Ecuador instalados')
    marker = 'ERPEC-PRUEBA-' + uuid.uuid4().hex
    partner = rpc('a', 'res.partner', 'create', [{'name':marker}])
    assert rpc('b', 'res.partner', 'search_count', [[['name','=',marker]]]) == 0
    data = ('Documento sintético ' + marker).encode()
    attachment = rpc('a', 'ir.attachment', 'create', [{'name':marker+'.txt','datas':base64.b64encode(data).decode(),'res_model':'res.partner','res_id':partner}])
    stored = rpc('a','ir.attachment','read',[[attachment]],{'fields':['store_fname']})[0]['store_fname']
    assert stored
    checks.append('Registro y adjunto de A no visibles en B')
    backup = STATE / 'backups' / marker
    backup.mkdir(parents=True)
    env = {**os.environ, 'PGPASSWORD':secrets['a']}
    subprocess.run([str(PG/'pg_dump.exe'),'-h','127.0.0.1','-p','55487','-U','erpec_a','-d','erpec_a','-Fc','-f',str(backup/'database.dump')],env=env,check=True)
    shutil.copytree(STATE/'a/data/filestore/erpec_a', backup/'filestore')
    restored = 'restore_' + uuid.uuid4().hex[:12]
    admin = psycopg2.connect(host='127.0.0.1',port=55487,user='postgres',password=secrets['postgres'],dbname='postgres')
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL('CREATE DATABASE {} OWNER erpec_a TEMPLATE template0').format(sql.Identifier(restored)))
        cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(restored)))
    admin.close()
    subprocess.run([str(PG/'pg_restore.exe'),'-h','127.0.0.1','-p','55487','-U','erpec_a','-d',restored,'--exit-on-error',str(backup/'database.dump')],env=env,check=True)
    with psycopg2.connect(host='127.0.0.1',port=55487,user='erpec_a',password=secrets['a'],dbname=restored) as restored_db:
        with restored_db.cursor() as cursor:
            cursor.execute('SELECT name FROM res_partner WHERE id=%s',[partner])
            assert cursor.fetchone()[0] == marker
            cursor.execute('SELECT store_fname FROM ir_attachment WHERE id=%s',[attachment])
            restored_file = cursor.fetchone()[0]
    restored_files = STATE/'restore-filestore'/restored
    shutil.copytree(backup/'filestore',restored_files)
    assert hashlib.sha256((restored_files/restored_file).read_bytes()).digest() == hashlib.sha256(data).digest()
    checks.append('Respaldo pg_dump restaurado en base independiente y archivo recuperado con SHA256 coincidente')
    report={'status':'passed','checks':checks,'restoredDatabase':restored,'scope':'Piloto Windows local con datos sintéticos, sin servicios fiscales ni carga productiva'}
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    assert text.encode('utf-8').decode('utf-8') == text
    (ROOT/'docs/evidencias/ERPEC26-02-validacion.json').write_text(text,encoding='utf-8')
    print('Aislamiento y restauración verificados')

if __name__ == '__main__':
    main()
