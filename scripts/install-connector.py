"""Instala el incremento validado exclusivamente en el cliente local 8186."""
from pathlib import Path
import configparser,hashlib,json,os,re,shutil,subprocess,sys,time,xmlrpc.client
import psutil
import requests
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
INSTANCE='b0bdbfd97ff34409b0fe0ea9eff6793f'
DIRECTORY=STATE/'instances'/INSTANCE
CONF=DIRECTORY/'odoo.conf'
ODOO=ROOT/'.cache/odoo-community/odoo-bin'
report=json.loads((STATE/'fiscal_connector-test-result.json').read_text(encoding='utf-8'))
if report['exitCode'] != 0:
 raise RuntimeError('Las pruebas del incremento no están aprobadas')
if not re.search(rb'0 failed, 0 error\(s\) of [1-9][0-9]* tests', Path(report['log']).read_bytes()):
 raise RuntimeError('Falta un resultado positivo con pruebas ejecutadas')
for name,expected in report['fileHashes'].items():
 path=ROOT/name
 if not path.resolve().is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
  raise RuntimeError('Los archivos cambiaron después de las pruebas')
config=configparser.ConfigParser(interpolation=None)
config.read(CONF,encoding='utf-8'); options=config['options']
if options['http_port']!='8186' or options['db_name']!='erp_'+INSTANCE:
 raise RuntimeError('La configuración no corresponde al cliente previsto')
pidfile=DIRECTORY/'pid'
process=psutil.Process(int(pidfile.read_text()))
if str(CONF) not in process.cmdline() or str(ODOO) not in process.cmdline():
 raise RuntimeError('El proceso no corresponde al cliente; no se detiene')
backup=STATE/'backups'/('fiscal_connector-install-'+time.strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True)
process.terminate(); process.wait(timeout=30)
try:
 subprocess.run(['C:/Program Files/PostgreSQL/17/bin/pg_dump.exe','-h',options['db_host'],'-p',options['db_port'],'-U',options['db_user'],'-d',options['db_name'],'-Fc','-f',str(backup/'database.dump')],env={**os.environ,'PGPASSWORD':options['db_password']},check=True)
 shutil.copytree(DIRECTORY/'data/filestore'/options['db_name'],backup/'filestore')
 shutil.copytree(ROOT/'addons/erpec_fiscal_connector',DIRECTORY/'addons/erpec_fiscal_connector',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 subprocess.run([sys.executable,str(ODOO),'-c',str(CONF),'-i','erpec_fiscal_connector','-u','erpec_fiscal_connector','--stop-after-init','--no-http','--max-cron-threads','0','--logfile',str(backup/'install.log')],check=True)
finally:
 process=subprocess.Popen([sys.executable,str(ODOO),'-c',str(CONF)],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
 pidfile.write_text(str(process.pid),encoding='utf-8')
for attempt in range(60):
 try:
  response=requests.get('http://127.0.0.1:8186/web/login',timeout=3)
  if response.status_code==200:
   break
 except requests.RequestException:
  if attempt==59:
   raise RuntimeError('El cliente no respondió tras la instalación') from None
 time.sleep(1)
else:
 raise RuntimeError('No se recuperó la pantalla de acceso')
private=json.loads((DIRECTORY/'credentials.json').read_text(encoding='utf-8'))
url='http://127.0.0.1:8186'
uid=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(options['db_name'],'admin',private['admin'],{})
if not uid:
 raise RuntimeError('No se pudo autenticar el cliente instalado')
models=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
def call(model,method,args,kwargs=None):
 return models.execute_kw(options['db_name'],uid,private['admin'],model,method,args,kwargs or {})
modules=call('ir.module.module','search_read',[[('name','in',['erpec_fiscal_connector','erpec_operations','sale_stock','purchase_stock'])]],{'fields':['name','state']})
assert len(modules)==4 and all(m['state']=='installed' for m in modules)
assert not call('ir.module.module','search_count',[[('state','=','installed'),('license','in',['OEEL-1','OPL-1'])]])
workspace=call('erpec.workspace','search_read',[[]],{'fields':['company_readiness','fiscal_scope']})
metadata=call('ir.model.data','search_read',[[('module','=','erpec_fiscal_connector'),('name','=','job_action')]],{'fields':['res_id']})
group=call('ir.model.data','search_read',[[('module','=','account'),('name','=','group_account_user')]],{'fields':['res_id']})
call('res.users','write',[[uid],{'groups_id':[(4,group[0]['res_id'])]}])
view=call('account.move','get_view',[],{'view_type':'form'})
assert 'ec_fiscal_job_ids' in view['arch']
counts={model:call(model,'search_count',[[]]) for model in ('erpec.fiscal.connection','erpec.fiscal.job')}
result={'documentCounts':counts,'invoiceViewVerified':True,'backup':str(backup),'modules':modules,'workspace':workspace,'url':url+'/odoo/action-'+str(metadata[0]['res_id']),'loginStatus':200,'enterpriseInstalled':False,'fiscalEmissionPerformed':False}
(STATE/'fiscal_connector-install-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result,ensure_ascii=True))
