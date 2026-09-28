"""Ensayo real del trabajador en bases nuevas; sin pagos, correos ni datos de instancias existentes."""
import configparser
import importlib.util
import json
import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from psycopg2 import sql

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cm28_worker',ROOT/'scripts/provision-worker.py')
runtime=importlib.util.module_from_spec(spec);sys.modules[spec.name]=runtime;spec.loader.exec_module(runtime)
from cm28_provision import operate_commercial


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--two-tenants',action='store_true');args=parser.parse_args()
    instance=uuid.uuid4().hex
    database='erp_'+instance
    databases=[database]
    cluster=json.loads((runtime.STATE/'credentials.json').read_text(encoding='utf-8'))
    connection=runtime._cluster_connection(cluster)
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[database])
        if cursor.fetchone():raise RuntimeError('El ensayo exige base nueva.')
    directory=runtime.STATE/'instances'/instance
    snapshot={'schema':1,'users':2,'max_companies':1,'capabilities':['assets'],'modules':['erpec_assets']}
    job={'id':280028,'instance':instance,'desired':'start','customer':'ENSAYO-'+instance,'company':'Ensayo CM28 no comercial',
         'contact_email':'cm28@example.invalid','contact_name':'Persona sintética','street':'Dirección sintética',
         'snapshot':snapshot,'revision':'revision-inicial','ends_on':'2099-01-01'}
    checks=[]
    try:
        details=operate_commercial(job,runtime)
        assert details['revision']==job['revision'] and details['active_users']==1
        assert 'activation_url' in details
        checks.append('Instancia real con activos y un usuario humano; sin contraseña expuesta')
        token=parse_qs(urlsplit(details['activation_url']).query)['token'][0]
        def shell(code):
            command=[str(runtime.PYTHON),str(runtime.SOURCE/'odoo-bin'),'shell','-c',str(directory/'provision.conf'),'--no-http']
            result=subprocess.run(command,input=code,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'},timeout=180)
            if result.returncode or 'CM28_OK' not in result.stdout:
                # Solo errores sin valores secretos; registro privado queda en la carpeta del ensayo.
                diagnostic=directory/'test-diagnostic.txt'
                runtime.write(diagnostic,result.stderr.replace(token,'[REDACTADO]'))
                raise RuntimeError('Falló la comprobación ORM del ensayo; diagnóstico privado '+str(diagnostic))
        password=secrets.token_urlsafe(32)
        shell('token='+repr(token)+'\npassword='+repr(password)+'\n'+"""from odoo.exceptions import AccessError
rights=env['erpec.tenant.entitlement'].search([])
assert rights.snapshot['users']==2
partner=env['res.partner']._get_partner_from_token(token)
assert partner and partner==env.ref('base.user_admin').partner_id
env['res.users'].signup({'password':password},token=token)
assert not env['res.partner']._get_partner_from_token(token)
try:
    rights.write({'revision':'falsa'})
except AccessError:
    pass
else:
    raise AssertionError('Derechos editables')
env.cr.commit()
print('CM28_OK')
""")
        checks.append('Activación nativa consumida y derechos no editables por ORM')
        endpoint=runtime.SHARED_URL.format(instance)
        call=runtime.rpc(endpoint,database,password,login=job['contact_email'])
        assert call('erpec.tenant.entitlement','search_count',[[]])==1
        call('erpec.asset','search_count',[[]])
        checks.append('Autenticación y lectura de activos mediante RPC real')
        # Renovación sin activos: los datos históricos conservan lectura, las altas se bloquean.
        job.update(snapshot=dict(snapshot,capabilities=[],modules=[]),revision='revision-renovada')
        renewed=operate_commercial(job,runtime)
        assert renewed['revision']==job['revision']
        call('erpec.asset','search_count',[[]])
        import xmlrpc.client
        try:call('erpec.asset','create',[{'name':'Alta bloqueada'}])
        except xmlrpc.client.Fault as error:
            assert 'no está contratado' in error.faultString
        else:raise AssertionError('RPC permitió alta sin derechos')
        checks.append('Retirada de módulo aplicada; historial consultable y alta RPC bloqueada')
        if args.two_tenants:
            second=uuid.uuid4().hex
            databases.append('erp_'+second)
            second_job=dict(job,instance=second,customer='ENSAYO-'+second,company='Segundo cliente sintético',revision='segunda-instancia')
            second_result=operate_commercial(second_job,runtime)
            assert second_result['revision']=='segunda-instancia'
            common=xmlrpc.client.ServerProxy(runtime.SHARED_URL.format(second)+'/xmlrpc/2/common')
            assert not common.authenticate('erp_'+second,job['contact_email'],password,{})
            with connection.cursor() as cursor:
                cursor.execute('SELECT count(*) FROM pg_database WHERE datname=ANY(%s)',[databases])
                assert cursor.fetchone()[0]==2
            checks.append('Dos bases simultáneas; la contraseña del primer cliente no autentica en la segunda')
        evidence={'phase':'CM28-F' if args.two_tenants else 'CM28-D','environment':'base desechable local','checks':checks,'payments':'ninguno','emails':'ninguno'}
        runtime.write(ROOT/('docs/evidencias/CM28/worker-isolation.json' if args.two_tenants else 'docs/evidencias/CM28/worker-functional.json'),json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(evidence,ensure_ascii=False))
    finally:
        with connection.cursor() as cursor:
            tenants=json.loads((runtime.STATE/'shared/credentials.json').read_text(encoding='utf-8'))
            for database in databases:
                cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s',[database])
                row=cursor.fetchone()
                if row:
                    if row[0]!=tenants['db_user']:raise RuntimeError('Propietario cambió; limpieza bloqueada.')
                    cursor.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(database)))
        connection.close()

if __name__=='__main__':main()
