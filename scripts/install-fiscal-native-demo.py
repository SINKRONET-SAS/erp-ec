"""Instala preparación fiscal local únicamente en la demo, con respaldo previo."""
from pathlib import Path
import configparser,hashlib,json,os,shutil,subprocess,sys,time,xmlrpc.client,socket,re
import psutil
ROOT=Path(__file__).resolve().parents[1];STATE=ROOT/'.cache/windows';DEMO=STATE/'demo';ODOO=ROOT/'.cache/odoo-community/odoo-bin'
report=json.loads((STATE/'fiscal-native-test-result.json').read_text(encoding='utf-8'))
log=Path(report['log']).read_bytes()
if report['exitCode'] or hashlib.sha256(log).hexdigest()!=report['logSha256'] or not re.search(rb'0 failed, 0 error\(s\) of 14 tests',log):raise RuntimeError('Faltan 14 pruebas fiscales aprobadas')
for name,expected in report['fileHashes'].items():
    path=ROOT/name
    if not path.resolve().is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Cambios posteriores a las pruebas')
config=configparser.ConfigParser(interpolation=None);config.read(DEMO/'odoo.conf',encoding='utf-8');options=config['options']
if options['db_name']!='erpec_demo' or options['http_port']!='8369':raise RuntimeError('Destino diferente de la demo')
import importlib.util
access_spec=importlib.util.spec_from_file_location('session_access',ROOT/'scripts/demo-session-access.py')
access_check=importlib.util.module_from_spec(access_spec);access_spec.loader.exec_module(access_check)
access_check.verify_session_access(DEMO)
backup=STATE/'backups'/('fiscal-native-install-'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
p=psutil.Process(int((DEMO/'pid').read_text()))
if str(DEMO/'odoo.conf') not in p.cmdline():raise RuntimeError('El proceso no pertenece a la demo')
p.terminate();p.wait(30)
try:
    subprocess.run(['C:/Program Files/PostgreSQL/17/bin/pg_dump.exe','-h',options['db_host'],'-p',options['db_port'],'-U',options['db_user'],'-d',options['db_name'],'-Fc','-f',str(backup/'database.dump')],env={**os.environ,'PGPASSWORD':options['db_password']},check=True)
    shutil.copytree(DEMO/'data/filestore'/options['db_name'],backup/'filestore')
    shutil.copytree(DEMO/'addons',backup/'addons',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for module in report['modules']:shutil.copytree(ROOT/'addons'/module,DEMO/'addons'/module,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    subprocess.run([sys.executable,str(ODOO),'-c',str(DEMO/'odoo.conf'),'-i',','.join(report['modules']),'-u',','.join(report['modules']),'--stop-after-init','--no-http','--logfile',str(backup/'install.log')],check=True)
finally:
    running=subprocess.Popen([sys.executable,str(ODOO),'-c',str(DEMO/'odoo.conf')],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW);(DEMO/'pid').write_text(str(running.pid),encoding='utf-8')
password=json.loads((DEMO/'credentials.json').read_text(encoding='utf-8'))['admin'];url='http://127.0.0.1:8369';socket.setdefaulttimeout(10)
for attempt in range(45):
    try:
        uid=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate('erpec_demo','demo',password,{})
        if uid:break
    except (OSError,xmlrpc.client.Error):
        if attempt==44:raise RuntimeError('No respondió la demo tras instalar') from None
    time.sleep(1)
else:raise RuntimeError('Autenticación fallida')
def call(model,method,args,kwargs=None):return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object').execute_kw('erpec_demo',uid,password,model,method,args,kwargs or {})
views={m:bool(call(m,'get_view',[],{'view_type':'form'})['arch']) for m in ['account.move','res.company','erpec.fiscal.preview']}
assert all(views.values());assert not call('res.company','read',[[1]],{'fields':['vat']})[0]['vat']
assert 'ec_native_notice' in call('account.move','get_view',[],{'view_type':'form'})['arch']
action=call('ir.model.data','search_read',[[('module','=','erpec_fiscal_native'),('name','=','native_action')]],{'fields':['res_id']})[0]['res_id']
result={'backup':str(backup),'views':views,'url':url+'/odoo/action-'+str(action),'authenticated':True,'demoRucEmpty':True,'fiscalEmissionPerformed':False,'installedModules':report['modules']}
output=json.dumps(result,ensure_ascii=False,indent=2)+'\n';assert output.encode('utf-8').decode('utf-8')==output;(STATE/'fiscal-native-install-result.json').write_bytes(output.encode('utf-8'));print(json.dumps(result,ensure_ascii=True))
