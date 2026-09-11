"""Comprueba semillas, navegación autenticada y solicitudes concurrentes en copia."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from importlib.machinery import SourceFileLoader
import hashlib,json,subprocess,sys,threading,time,xmlrpc.client
ROOT=Path(__file__).resolve().parents[1]
verify=SourceFileLoader('operational_verify',str(ROOT/'scripts/verify-operational-plan.py')).load_module()
report=json.loads((verify.STATE/'operational-test-result.json').read_text(encoding='utf-8'))
if report['exitCode'] or report['fileHashes']!=verify.file_hashes():
    raise RuntimeError('Primero aprueba las pruebas con los archivos actuales')
directory=Path(report['directory']);conf=directory/'odoo.conf'
current=json.loads((verify.STATE/'operational-current.json').read_text());database=current['database']
seeds=['seed-manufacturing-demo.py','seed-operational-demo.py']
for seed in seeds:
    code="exec(compile(open("+repr(str(ROOT/'scripts'/seed))+",encoding='utf-8').read(),"+repr(seed)+",'exec'))"
    subprocess.run([sys.executable,str(verify.SOURCE/'odoo-bin'),'shell','-c',str(conf),'--no-http'],input=code,text=True,check=True)
password=json.loads((verify.DEMO/'credentials.json').read_text(encoding='utf-8'))['admin']
url='http://127.0.0.1:8469'
server=subprocess.Popen([sys.executable,str(verify.SOURCE/'odoo-bin'),'-c',str(conf)],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    for attempt in range(60):
        try:
            uid=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(database,'demo',password,{})
            if uid:break
        except (OSError,xmlrpc.client.Error):
            if attempt==59:raise RuntimeError('No respondió la copia') from None
        time.sleep(1)
    else:raise RuntimeError('No se autenticó la copia')
    def call(model,method,args,kwargs=None):
        return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object').execute_kw(database,uid,password,model,method,args,kwargs or {})
    def ref(module,name):
        return call('ir.model.data','search_read',[[('module','=',module),('name','=',name)]],{'fields':['res_id']})[0]['res_id']
    def concurrent(model,method,record):
        barrier=threading.Barrier(2)
        def request():
            barrier.wait(timeout=10)
            return call(model,method,[[record]])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(request) for _ in range(2)]
            return [future.result(timeout=45) for future in futures]
    mo=ref('erpec_manufacturing_demo','pending_order')
    wo=call('mrp.workorder','search_read',[[('production_id','=',mo)]],{'fields':['id'],'order':'id'})[0]['id']
    assert all(concurrent('mrp.workorder','button_start',wo))
    domain=[('workorder_id','=',wo),('date_end','=',False)]
    assert call('mrp.workcenter.productivity','search_count',[domain])==1
    call('mrp.workorder','write',[[wo],{'erpec_pause_reason':'Pausa del ensayo concurrente'}])
    assert all(concurrent('mrp.workorder','button_pending',wo))
    assert call('mrp.workcenter.productivity','search_count',[domain+[('erpec_pause','=',True)]])==1
    assert call('mrp.workcenter.productivity','search_count',[domain+[('erpec_pause','=',False)]])==0
    call('mrp.workorder','button_start',[[wo]])
    assert call('mrp.workcenter.productivity','search_count',[domain+[('erpec_pause','=',True)]])==0
    call('mrp.workorder','button_pending',[[wo]])
    period=ref('erpec_operational_demo','payroll_pending')
    state=call('erpec.payroll.period','read',[[period]],{'fields':['state']})[0]['state']
    if state=='draft':
        lines=call('erpec.payroll.line','search',[[('period_id','=',period)]])
        call('erpec.payroll.line','write',[lines,{'approved':True}])
        call('erpec.payroll.period','action_calculate',[[period]])
        call('erpec.payroll.period','action_close',[[period]])
    responses=concurrent('erpec.payroll.period','action_post',period)
    assert responses[0]['res_id']==responses[1]['res_id']
    assert call('account.move','search_count',[[('erpec_payroll_id','=',period)]])==1
    views={model:bool(call(model,'get_view',[],{'view_type':'form'})['arch']) for model in ['erpec.importation','erpec.payroll.period','erpec.payroll.policy','mrp.workorder']}
    assert all(views.values())
    report.update({'runtimePassed':True,'authenticatedViews':views,'concurrentRequestsPerAction':2,'activeWorkTimersAfterStart':1,'productiveTimersDuringPause':0,'pauseTimersDuringPause':1,'payrollMovesAfterConcurrentPost':1,'seedHashes':{seed:hashlib.sha256((ROOT/'scripts'/seed).read_bytes()).hexdigest() for seed in seeds}})
    verify.write(verify.STATE/'operational-test-result.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Semillas, vistas autenticadas, pausa y contabilización concurrente verificadas',flush=True)
finally:
    server.terminate();server.wait(30)
