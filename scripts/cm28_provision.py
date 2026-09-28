"""Aprovisionamiento comercial local: lista autorizada y activación nativa, sin imprimir secretos."""
import configparser
import importlib.util
import json
import os
import re
import subprocess
import time
from urllib.parse import urlencode
import requests
import psycopg2
from psycopg2 import sql


def operate_commercial(job,runtime):
    instance=job['instance']
    if not re.fullmatch('[a-f0-9]{32}',instance) or type(job['id']) is not int or job['id']<1:
        raise ValueError('Identidad de instancia inválida.')
    directory=runtime.STATE/'instances'/instance
    directory.mkdir(parents=True,exist_ok=True)
    database='erp_'+instance
    cluster=json.loads((runtime.STATE/'credentials.json').read_text(encoding='utf-8'))
    if job['desired']=='stop':
        runtime.set_allow_connections(cluster,database,False)
        return {}
    if job['desired']!='start':
        raise ValueError('Operación no permitida.')
    spec=importlib.util.spec_from_file_location('cm28_capabilities',runtime.ROOT/'addons/erpec_entitlements/capabilities.py')
    catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)
    snapshot=job['snapshot']
    codes=snapshot.get('capabilities',[])
    if set(codes)-set(catalog.CAPABILITIES):
        raise ValueError('Capacidad desconocida.')
    if catalog.missing_requirements(codes):
        raise ValueError('La contratación omite una capacidad requerida.')
    modules=sorted({module for code in codes for module in catalog.CAPABILITIES[code][1]})
    if modules!=snapshot.get('modules'):
        raise ValueError('La lista de módulos no coincide con el catálogo autorizado.')
    modules=sorted(set(modules)|{'base','l10n_ec','erpec_base','erpec_entitlements','auth_signup'})
    tenants=json.loads((runtime.STATE/'shared/credentials.json').read_text(encoding='utf-8'))
    connection=runtime._cluster_connection(cluster)
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s',[database])
            owner=cursor.fetchone()
            if owner and owner[0]!=tenants['db_user']:
                raise ValueError('La base pertenece a otro propietario.')
            if not owner:
                cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(database),sql.Identifier(tenants['db_user'])))
                cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
            cursor.execute(sql.SQL('ALTER DATABASE {} SET statement_timeout TO %s').format(sql.Identifier(database)),[runtime.TENANT_STATEMENT_TIMEOUT])
    finally:
        connection.close()
    runtime.set_allow_connections(cluster,database,True)
    initialized=(directory/'initialized.json').exists()
    environment={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','ERPEC_CM28_INSTALLATION':'1'}
    if initialized:
        backup=directory/('before-'+job['revision']+'.dump')
        if not backup.exists():
            result=subprocess.run(['C:/Program Files/PostgreSQL/17/bin/pg_dump.exe','-h','127.0.0.1','-p','55487','-U','postgres','-Fc','-f',str(backup),database],env={**os.environ,'PGPASSWORD':cluster['postgres']},capture_output=True)
            if result.returncode:
                raise RuntimeError('No se obtuvo respaldo previo de la instancia.')
    config=configparser.ConfigParser(interpolation=None)
    config['options']={'db_host':'127.0.0.1','db_port':'55487','db_user':tenants['db_user'],'db_password':tenants['db_password'],
        'db_name':database,'addons_path':','.join(str(p) for p in [runtime.SOURCE/'addons',runtime.SOURCE/'odoo/addons',runtime.ROOT/'addons']),
        'data_dir':str(runtime.STATE/'shared/data'),'list_db':'False','max_cron_threads':'0','without_demo':'all','logfile':str(directory/'provision.log')}
    from io import StringIO
    output=StringIO();config.write(output);runtime.write(directory/'provision.conf',output.getvalue())
    command=[str(runtime.PYTHON),str(runtime.SOURCE/'odoo-bin'),'-c',str(directory/'provision.conf')]
    # No reinstalar base ni traducciones en cada renovación; solo instalar capacidades nuevas.
    tenant=psycopg2.connect(host='127.0.0.1',port=55487,user=tenants['db_user'],password=tenants['db_password'],dbname=database)
    try:
        with tenant.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.ir_module_module')")
            installed_names=set()
            if cursor.fetchone()[0]:
                cursor.execute("SELECT name FROM ir_module_module WHERE state='installed'")
                installed_names={row[0] for row in cursor.fetchall()}
    finally:
        tenant.close()
    pending=sorted(set(modules)-installed_names)
    if pending:
        installed=subprocess.run(command+['-i',','.join(pending),'--stop-after-init','--no-http'],capture_output=True,env=environment,timeout=1800)
        if installed.returncode:
            raise RuntimeError('Falló la instalación; revisar el registro privado de aprovisionamiento.')
    payload={'customer':job['customer'],'revision':job['revision'],'snapshot':snapshot,'ends_on':job['ends_on'],
             'name':job['company'],'email':job.get('contact_email'),'contact':job.get('contact_name'),'vat':job.get('vat'),
             'street':job.get('street'),'new':not initialized,'refresh':job.get('refresh_access'),
             'endpoint':runtime.SHARED_URL.format(instance)}
    code="payload="+repr(payload)+"\n"+r'''import json,secrets
from urllib.parse import urlencode
company=env.company
user=env.ref('base.user_admin')
if payload['new']:
    company.write({'name':payload['name'],'country_id':env.ref('base.ec').id,'street':payload['street']})
    env['account.chart.template'].try_loading('ec',company,install_demo=False)
    lang=env['res.lang'].with_context(active_test=False).search([('code','=','es_EC')],limit=1)
    env['base.language.install'].create({'lang_ids':[(6,0,lang.ids)],'overwrite':False}).lang_install()
    user.with_context(no_reset_password=True).write({'login':payload['email'] or 'admin','password':secrets.token_urlsafe(32),
        'name':payload['contact'] or payload['name'],'email':payload['email'],'lang':'es_EC','tz':'America/Guayaquil'})
    if not env['erpec.workspace'].search_count([('company_id','=',company.id)]):
        env['erpec.workspace'].create({'company_id':company.id})
groups=['account.group_account_user','account.group_account_manager']
for key,xmlid in [('sales','sales_team.group_sale_manager'),('purchases','purchase.group_purchase_manager'),('inventory','stock.group_stock_manager'),('manufacturing','mrp.group_mrp_manager'),('payroll','erpec_payroll.group_payroll_manager')]:
    if key in payload['snapshot']['capabilities']:
        groups.append(xmlid)
user.write({'groups_id':[(4,env.ref(x).id) for x in groups]})
rights=env['erpec.tenant.entitlement']._sync(payload['customer'],payload['revision'],payload['snapshot'],payload['ends_on'])
result={'revision':rights.revision,'active_users':rights.active_users}
if payload['new'] or payload['refresh']:
    user.partner_id.signup_prepare('reset')
    token=user.partner_id._generate_signup_token(expiration=4)
    result['activation_url']=payload['endpoint']+'/web/reset_password?'+urlencode({'token':token})
env.cr.commit()
print('CM28_RESULT='+json.dumps(result))
'''
    configured=subprocess.run(command[:2]+['shell']+command[2:]+['--no-http'],input=code,capture_output=True,text=True,encoding='utf-8',env=environment,timeout=900)
    if configured.returncode:
        raise RuntimeError('No se aplicaron los derechos; revisar usuarios activos y registro privado.')
    result_lines=[line for line in configured.stdout.splitlines() if line.startswith('CM28_RESULT=')]
    if len(result_lines)!=1:
        raise RuntimeError('El trabajador no recibió confirmación de la revisión.')
    details=json.loads(result_lines[0].split('=',1)[1])
    endpoint=payload['endpoint']
    for attempt in range(30):
        try:
            response=requests.get(endpoint+'/erpec/tenant-health',timeout=5)
            if response.status_code==200 and response.json().get('revision')==job['revision']:
                runtime.write(directory/'initialized.json',json.dumps({'instance':instance,'database':database,'customer':job['customer'],'revision':job['revision']}))
                print('Instancia comercial verificada correlationId='+instance)
                return details
        except (requests.RequestException,ValueError) as error:
            print('Esperando salud de instancia correlationId='+instance+' tipo='+type(error).__name__)
        time.sleep(2)
    raise RuntimeError('La revisión no está disponible en el servidor compartido.')
