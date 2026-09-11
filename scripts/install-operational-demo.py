"""Instala únicamente en la demo tras comprobar pruebas, respaldo y hashes."""
from pathlib import Path
import configparser, hashlib, json, os, shutil, subprocess, sys, time, xmlrpc.client
import psutil
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
DEMO=STATE/'demo'
ODOO=ROOT/'.cache/odoo-community/odoo-bin'
report=json.loads((STATE/'operational-test-result.json').read_text(encoding='utf-8'))
if report['exitCode'] or not report.get('runtimePassed') or report.get('payrollMovesAfterConcurrentPost')!=1:
    raise RuntimeError('Faltan pruebas operativas y de concurrencia')
for name, expected in report['fileHashes'].items():
    path=ROOT/name
    if not path.resolve().is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Los archivos cambiaron después de las pruebas')
for seed, expected in report['seedHashes'].items():
    if hashlib.sha256((ROOT/'scripts'/seed).read_bytes()).hexdigest()!=expected:
        raise RuntimeError('El escenario cambió después de probarse')
config=configparser.ConfigParser(interpolation=None)
config.read(DEMO/'odoo.conf',encoding='utf-8')
options=config['options']
if options['db_name']!='erpec_demo' or options['http_port']!='8369':
    raise RuntimeError('El destino no es la demo autorizada')
backup=STATE/'backups'/('operational-install-'+time.strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True)
process=psutil.Process(int((DEMO/'pid').read_text()))
if str(DEMO/'odoo.conf') not in process.cmdline():
    raise RuntimeError('El proceso no pertenece a la demo')
process.terminate()
process.wait(30)
try:
    subprocess.run(['C:/Program Files/PostgreSQL/17/bin/pg_dump.exe','-h',options['db_host'],'-p',options['db_port'],'-U',options['db_user'],'-d',options['db_name'],'-Fc','-f',str(backup/'database.dump')],env={**os.environ,'PGPASSWORD':options['db_password']},check=True)
    shutil.copytree(DEMO/'data/filestore'/options['db_name'],backup/'filestore')
    shutil.copytree(DEMO/'addons',backup/'addons',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for module in report['modules']:
        shutil.copytree(ROOT/'addons'/module,DEMO/'addons'/module,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    subprocess.run([sys.executable,str(ODOO),'-c',str(DEMO/'odoo.conf'),'-i',','.join(report['modules']),'-u',','.join(report['modules']),'--stop-after-init','--no-http','--logfile',str(backup/'install.log')],check=True)
    for name in report['seedHashes']:
        seed="exec(compile(open("+repr(str(ROOT/'scripts'/name))+",encoding='utf-8').read(),"+repr(name)+",'exec'))"
        subprocess.run([sys.executable,str(ODOO),'shell','-c',str(DEMO/'odoo.conf'),'--no-http'],input=seed,text=True,check=True)
finally:
    running=subprocess.Popen([sys.executable,str(ODOO),'-c',str(DEMO/'odoo.conf')],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
    (DEMO/'pid').write_text(str(running.pid),encoding='utf-8')
password=json.loads((DEMO/'credentials.json').read_text(encoding='utf-8'))['admin']
url='http://127.0.0.1:8369'
for attempt in range(60):
    try:
        uid=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate('erpec_demo','demo',password,{})
        if uid:
            break
    except (OSError,xmlrpc.client.Error):
        if attempt==59:
            raise RuntimeError('La demo no respondió tras instalar') from None
    time.sleep(1)
else:
    raise RuntimeError('No se autenticó la demo')
def call(model,method,args,kwargs=None):
    return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object').execute_kw('erpec_demo',uid,password,model,method,args,kwargs or {})
assert not call('res.company','search_count',[[('id','=',1),('vat','!=',False)]])
assert not call('ir.module.module','search_count',[[('state','=','installed'),('license','in',['OEEL-1','OPL-1'])]])
actions={}
for module,name in [('erpec_imports','import_action'),('erpec_payroll','period_action'),('erpec_payroll','policy_action')]:
    actions[name]=call('ir.model.data','search_read',[[('module','=',module),('name','=',name)]],{'fields':['res_id']})[0]['res_id']
views={model:bool(call(model,'get_view',[],{'view_type':'form'})['arch']) for model in ['erpec.importation','erpec.payroll.period','erpec.payroll.policy','mrp.workorder']}
assert all(views.values())
policy=call('erpec.payroll.policy','search_read',[[('name','=','Ecuador 2026 · privado general v1')]],{'fields':['parameters','state']})[0]
params=json.loads(policy['parameters'])
assert params['minimum_salary']==482 and params['personal_rate']==0.0945 and params['employer_rate']==0.1115 and params['reserve_rate']==0.0833 and policy['state']=='active'
result={'backup':str(backup),'database':'erpec_demo','urls':{name:url+'/odoo/action-'+str(action) for name,action in actions.items()},'authenticated':True,'viewsCompiled':views,'fictionalEmployees':True,'realParameters2026':True,'vatEmpty':True,'enterpriseInstalled':False,'payrollPeriods':call('erpec.payroll.period','search_read',[[]],{'fields':['name','state','move_id']})}
text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
assert text.encode('utf-8').decode('utf-8')==text
(STATE/'operational-install-result.json').write_text(text,encoding='utf-8',newline='\n')
print(json.dumps(result),flush=True)
