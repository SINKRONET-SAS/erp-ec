"""Instala preparación fiscal local únicamente en la demo, con respaldo previo."""
from pathlib import Path
import configparser,hashlib,json,os,shutil,subprocess,sys,time,xmlrpc.client,socket,re
import psutil
os.environ.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
ROOT=Path(__file__).resolve().parents[1];STATE=ROOT/'.cache/windows';DEMO=STATE/'demo';ODOO=ROOT/'.cache/odoo-community/odoo-bin'
closeout_mode = '--closeout' in sys.argv
imports_ui_mode = '--imports-ui' in sys.argv
workspace_mode = '--workspace' in sys.argv or closeout_mode or imports_ui_mode
prefix = 'imports-ui' if imports_ui_mode else 'closeout' if closeout_mode else 'workspace' if workspace_mode else 'fiscal-native'
expected_tests = 63 if imports_ui_mode else 21 if closeout_mode else 9 if workspace_mode else 14
report=json.loads((STATE/(prefix+'-test-result.json')).read_text(encoding='utf-8'))
expected_modules = ['erpec_imports','erpec_workspace','erpec_fiscal_connector','erpec_fiscal_documents','erpec_withholding_accounting'] if imports_ui_mode else ['erpec_workspace','erpec_treasury'] if closeout_mode else ['erpec_workspace'] if workspace_mode else ['erpec_fiscal_native','erpec_fiscal_connector']
if report['modules'] != expected_modules: raise RuntimeError('El informe corresponde a otros módulos')
log=Path(report['log']).read_bytes()
if report['exitCode'] or hashlib.sha256(log).hexdigest()!=report['logSha256'] or not re.search(('0 failed, 0 error\\(s\\) of '+str(expected_tests)+' tests').encode(),log):raise RuntimeError('Faltan las pruebas aprobadas del incremento')
for name,expected in report['fileHashes'].items():
    path=ROOT/name
    if not path.resolve().is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Cambios posteriores a las pruebas')
if closeout_mode:
    seed_report=json.loads((STATE/'treasury-seed-result.json').read_text(encoding='utf-8'))
    if seed_report['exitCode'] or seed_report['seedSha256']!=hashlib.sha256((ROOT/'scripts/seed-treasury-demo.py').read_bytes()).hexdigest():
        raise RuntimeError('Falta ensayo de la semilla actual de tesorería')
    if seed_report['logSha256']!=hashlib.sha256(Path(seed_report['log']).read_bytes()).hexdigest():
        raise RuntimeError('El registro del ensayo de semilla cambió')
config=configparser.ConfigParser(interpolation=None);config.read(DEMO/'odoo.conf',encoding='utf-8');options=config['options']
if options['db_name']!='erpec_demo' or options['http_port']!='8369':raise RuntimeError('Destino diferente de la demo')
import importlib.util
access_spec=importlib.util.spec_from_file_location('session_access',ROOT/'scripts/demo-session-access.py')
access_check=importlib.util.module_from_spec(access_spec);access_spec.loader.exec_module(access_check)
access_check.verify_session_access(DEMO)
backup=STATE/'backups'/(prefix+'-install-'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
p=psutil.Process(int((DEMO/'pid').read_text()))
if str(DEMO/'odoo.conf') not in p.cmdline():raise RuntimeError('El proceso no pertenece a la demo')
p.terminate();p.wait(30)
try:
    subprocess.run(['C:/Program Files/PostgreSQL/17/bin/pg_dump.exe','-h',options['db_host'],'-p',options['db_port'],'-U',options['db_user'],'-d',options['db_name'],'-Fc','-f',str(backup/'database.dump')],env={**os.environ,'PGPASSWORD':options['db_password']},check=True)
    shutil.copytree(DEMO/'data/filestore'/options['db_name'],backup/'filestore')
    shutil.copytree(DEMO/'addons',backup/'addons',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for module in report['modules']:shutil.copytree(ROOT/'addons'/module,DEMO/'addons'/module,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    subprocess.run([sys.executable,str(ODOO),'-c',str(DEMO/'odoo.conf'),'-i',','.join(report['modules']),'-u',','.join(report['modules']),'--stop-after-init','--no-http','--logfile',str(backup/'install.log')],check=True)
    if closeout_mode:
        seed="exec(compile(open("+repr(str(ROOT/'scripts/seed-treasury-demo.py'))+",encoding='utf-8').read(),'seed-treasury-demo.py','exec'))"
        subprocess.run([sys.executable,str(ODOO),'shell','-c',str(DEMO/'odoo.conf'),'--no-http'],input=seed,text=True,encoding='utf-8',check=True)
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
if workspace_mode:
    home=call('erpec.workspace','action_home',[])
    views={'home':bool(call('erpec.workspace','get_view',[],{'view_id':home['views'][0][0],'view_type':'form'})['arch'])}
    action=call('ir.model.data','search_read',[[('module','=','erpec_workspace'),('name','=','home_action')]],{'fields':['res_id']})[0]['res_id']
    previous=call('res.users','read',[[uid]],{'fields':['action_id']})[0]['action_id']
    previous_text=json.dumps({'userId':uid,'actionId':previous})+'\n'
    assert previous_text.encode('utf-8').decode('utf-8')==previous_text
    (backup/'previous-home.json').write_bytes(previous_text.encode('utf-8'))
    call('res.users','write',[[uid],{'action_id':action}])
else:
    views={m:bool(call(m,'get_view',[],{'view_type':'form'})['arch']) for m in ['account.move','res.company','erpec.fiscal.preview']}
    assert 'ec_native_notice' in call('account.move','get_view',[],{'view_type':'form'})['arch']
    action=call('ir.model.data','search_read',[[('module','=','erpec_fiscal_native'),('name','=','native_action')]],{'fields':['res_id']})[0]['res_id']
if closeout_mode:
    views.update({m:bool(call(m,'get_view',[],{'view_type':'form'})['arch']) for m in ['erpec.payroll.disbursement','erpec.bank.match']})
    supplier_view=call('ir.model.data','search_read',[[('module','=','erpec_treasury'),('name','=','supplier_pending_list')]],{'fields':['res_id']})[0]['res_id']
    supplier_arch=call('account.move','get_view',[],{'view_id':supplier_view,'view_type':'list'})['arch']
    views['supplierBalances']='amount_residual' in supplier_arch and 'move_type' in supplier_arch
    payments_view=call('ir.model.data','search_read',[[('module','=','erpec_treasury'),('name','=','supplier_payments_list')]],{'fields':['res_id']})[0]['res_id']
    views['supplierPayments']='memo' in call('account.payment','get_view',[],{'view_id':payments_view,'view_type':'list'})['arch']
    sale_form=call('ir.model.data','search_read',[[('module','=','sale'),('name','=','view_order_form')]],{'fields':['res_id']})[0]['res_id']
    views['salesFlow']='erpec_sale_guide' in call('sale.order','get_view',[],{'view_id':sale_form,'view_type':'form'})['arch']
    production_form=call('ir.model.data','search_read',[[('module','=','mrp'),('name','=','mrp_production_form_view')]],{'fields':['res_id']})[0]['res_id']
    views['productionFlow']='Iniciar producción' in call('mrp.production','get_view',[],{'view_id':production_form,'view_type':'form'})['arch']
assert all(views.values());assert not call('res.company','read',[[1]],{'fields':['vat']})[0]['vat']
result={'backup':str(backup),'views':views,'url':url+'/odoo/action-'+str(action),'authenticated':True,'demoRucEmpty':True,'fiscalEmissionPerformed':False,'installedModules':report['modules']}
output=json.dumps(result,ensure_ascii=False,indent=2)+'\n';assert output.encode('utf-8').decode('utf-8')==output;(STATE/(prefix+'-install-result.json')).write_bytes(output.encode('utf-8'));print(json.dumps(result,ensure_ascii=True))
