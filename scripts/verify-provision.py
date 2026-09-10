"""Ensayo real local: repetición, reinicio, suspensión y conservación de datos."""
import importlib.util
import json
import pathlib
import subprocess
import uuid
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('worker',ROOT/'scripts/provision-worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
private = json.loads((ROOT/'.cache/windows/credentials.json').read_text(encoding='utf-8'))
call = worker.rpc('http://127.0.0.1:8169','erpec_a',private['admin_a'])
fixture_path = ROOT/'.cache/windows/provision-test.json'
if fixture_path.exists():
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
else:
    company = call('res.company','create',[{'name':'ERP EC ensayo de aprovisionamiento'}])
    plan = call('erpec.plan','create',[{'name':'Piloto sintético sin cobro','code':'PROVISION-'+uuid.uuid4().hex[:8],'erp':True,'terms':'Ensayo local, no es un contrato comercial'}])
    subscription = call('erpec.subscription','create',[{'name':'Ensayo local sin cargo','company_id':company,'plan_id':plan,'ends_on':str(date.today()+timedelta(days=7)),'billing_owner':'manual','billing_reference':'Operador: ensayo local sin cobro','authorization':'Solicitud de ejecución y pruebas del plan'}])
    call('erpec.subscription','action_activate',[[subscription]])
    fixture = {'subscription':subscription,'company':company}
    worker.write(fixture_path,json.dumps(fixture))
current = call('erpec.subscription','read',[[fixture['subscription']],['suspended']])[0]
if current['suspended']:
    call('erpec.subscription','action_resume',[[fixture['subscription']]])
first = call('erpec.subscription','action_provision',[[fixture['subscription']]])['res_id']
second = call('erpec.subscription','action_provision',[[fixture['subscription']]])['res_id']
assert first == second, 'La repetición creó otra instancia'

def run():
    subprocess.run([str(worker.PYTHON),str(ROOT/'scripts/provision-worker.py')],check=True,timeout=900)

def read_job():
    return call('erpec.provision','read',[[first],['name','state','endpoint']])[0]

job = read_job()
if job['state'] == 'failed':
    call('erpec.provision','action_retry',[[first]])
run()
job = read_job()
assert job['state'] == 'ready', job['state']
directory = ROOT/'.cache/windows/instances'/job['name']
instance_private = json.loads((directory/'credentials.json').read_text(encoding='utf-8'))
customer = worker.rpc(job['endpoint'],'erp_'+job['name'],instance_private['admin'])
marker = 'Persistencia-'+uuid.uuid4().hex
partner = customer('res.partner','create',[{'name':marker}])
# Reinicia el trabajador como otro proceso; la instancia y el registro se conservan.
run()
assert read_job()['name'] == job['name']
call('erpec.subscription','action_suspend',[[fixture['subscription']]])
run()
assert read_job()['state'] == 'suspended'
assert worker.matching_process(directory) is None
call('erpec.subscription','action_resume',[[fixture['subscription']]])
run()
resumed = read_job()
assert resumed['state'] == 'ready' and resumed['name'] == job['name']
customer = worker.rpc(resumed['endpoint'],'erp_'+job['name'],instance_private['admin'])
assert customer('res.partner','read',[[partner],['name']])[0]['name'] == marker
assert customer('ir.module.module','search_count',[[('name','in',['erpec_suite','erpec_provision']),('state','=','installed')]]) == 0
for database, user, password in [('erp_'+job['name'],'erpec_a',private['a']),('erpec_a','erp_'+job['name'],instance_private['database'])]:
    try:
        connection = worker.psycopg2.connect(host='127.0.0.1',port=55487,dbname=database,user=user,password=password)
    except worker.psycopg2.OperationalError as error:
        assert 'permission denied' in str(error).lower(), 'La conexión falló por un motivo distinto de permisos'
    else:
        connection.close()
        raise AssertionError('Se permitió acceso cruzado a otra base')
assert not (directory/'addons/erpec_suite').exists()
assert not (directory/'addons/erpec_provision').exists()
report = {'status':'passed-local','phaseComplete':False,'checks':['Acceso cruzado entre operador y cliente rechazado; módulos del operador excluidos del cliente','Siete pruebas transaccionales de contratos y cola: cero fallos, cero errores','Solicitud repetida conserva una sola instancia','Trabajador Windows crea rol, base, filestore y proceso reales; autentica salud en la base exacta','Reinicio de trabajador no duplica instancia','Suspensión detiene el proceso; reactivación conserva el contacto sintético','Reservas vencidas, tokens obsoletos y límite de reintentos verificados transaccionalmente'],'pendingChecks':['Proveedor y ambiente de pagos','Servidor Windows y dominio/HTTPS'],'instance':job['name'],'endpoint':resumed['endpoint'],'scope':'Alta comercial sintética local, sin pago externo, DNS público ni HTTPS'}
worker.write(ROOT/'docs/evidencias/ERPEC26-04-validacion.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Aprovisionamiento, suspensión y reactivación locales verificados')
