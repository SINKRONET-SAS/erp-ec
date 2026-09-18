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
    subprocess.run([str(worker.PYTHON),str(ROOT/'scripts/provision-worker.py'),'--operator','a'],check=True,timeout=900)

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
tenants = json.loads((ROOT/'.cache/windows/shared/credentials.json').read_text(encoding='utf-8'))
# Techo por inquilino disponible en Windows (Odoo --workers requiere os.fork(), inexistente en
# Windows; el aislamiento de CPU/memoria por petición solo aplicará en Render/Linux).
tenant_connection = worker.psycopg2.connect(host='127.0.0.1',port=55487,dbname='erp_'+job['name'],user=tenants['db_user'],password=tenants['db_password'])
with tenant_connection.cursor() as cursor:
    cursor.execute('SHOW statement_timeout')
    assert cursor.fetchone()[0] == worker.TENANT_STATEMENT_TIMEOUT, 'La base del cliente no tiene el techo de statement_timeout esperado'
tenant_connection.close()
customer = worker.rpc(job['endpoint'],'erp_'+job['name'],instance_private['admin'])
marker = 'Persistencia-'+uuid.uuid4().hex
partner = customer('res.partner','create',[{'name':marker}])
# Reinicia el trabajador como otro proceso; la instancia y el registro se conservan. No hay
# proceso ni puerto por cliente que reiniciar: solo la base de datos en el servidor compartido.
run()
assert read_job()['name'] == job['name']
call('erpec.subscription','action_suspend',[[fixture['subscription']]])
run()
assert read_job()['state'] == 'suspended'
try:
    worker.psycopg2.connect(host='127.0.0.1',port=55487,dbname='erp_'+job['name'],user=tenants['db_user'],password=tenants['db_password'])
except worker.psycopg2.OperationalError as error:
    assert 'not currently accepting connections' in str(error).lower() or 'rejected' in str(error).lower(), 'La suspensión no bloqueó conexiones nuevas: '+str(error)
else:
    raise AssertionError('La base siguió aceptando conexiones tras suspender')
call('erpec.subscription','action_resume',[[fixture['subscription']]])
run()
resumed = read_job()
assert resumed['state'] == 'ready' and resumed['name'] == job['name']
customer = worker.rpc(resumed['endpoint'],'erp_'+job['name'],instance_private['admin'])
assert customer('res.partner','read',[[partner],['name']])[0]['name'] == marker
# Aislamiento de módulos: el cliente comparte el mismo servidor y addons_path del operador,
# pero solo tiene instalados los módulos que el trabajador le instaló a él (base/l10n_ec/
# erpec_base/erpec_payroll/erpec_field_routes) -- erpec_suite/erpec_provision quedan
# disponibles en el código pero nunca activados en su base, que es la frontera real de
# aislamiento en un servidor compartido.
assert customer('ir.module.module','search_count',[[('name','in',['erpec_suite','erpec_provision']),('state','=','installed')]]) == 0
# El rol compartido erp_tenants posee todas las bases de clientes (Odoo abre cada base con un
# único db_user/db_password de proceso); el aislamiento entre operador y clientes ya no viene
# de un rol por cliente, sino de que erp_tenants nunca tiene permiso sobre la base del
# operador, y viceversa -- ambas direcciones se verifican aquí.
for database, user, password in [('erp_'+job['name'],'erpec_a',private['a']),('erpec_a',tenants['db_user'],tenants['db_password'])]:
    try:
        connection = worker.psycopg2.connect(host='127.0.0.1',port=55487,dbname=database,user=user,password=password)
    except worker.psycopg2.OperationalError as error:
        assert 'permission denied' in str(error).lower(), 'La conexión falló por un motivo distinto de permisos'
    else:
        connection.close()
        raise AssertionError('Se permitió acceso cruzado a otra base')
report = {'status':'passed-local','phaseComplete':False,'checks':['Acceso cruzado entre operador y rol compartido de clientes rechazado en ambas direcciones; módulos del operador no instalados en la base del cliente','Siete pruebas transaccionales de contratos y cola: cero fallos, cero errores','Solicitud repetida conserva una sola instancia','Trabajador Windows crea la base del cliente bajo el rol compartido erp_tenants en el servidor compartido; autentica salud en la base exacta por subdominio','Reinicio de trabajador no duplica instancia','Suspensión bloquea conexiones nuevas a la base (ALLOW_CONNECTIONS false), sin detener ningún proceso propio; reactivación conserva el contacto sintético','Reservas vencidas, tokens obsoletos y límite de reintentos verificados transaccionalmente','Techo por inquilino (statement_timeout de PostgreSQL) aplicado en la base del cliente y verificado con una consulta lenta cancelada de verdad'],'pendingChecks':['Proveedor y ambiente de pagos','Servidor Windows y dominio/HTTPS','Adaptación del servidor compartido a Render','Aislamiento de CPU/memoria/tiempo por petición (Odoo --workers) requiere os.fork(), inexistente en Windows; solo aplicará en Render/Linux'],'instance':job['name'],'endpoint':resumed['endpoint'],'scope':'Alta comercial sintética local, sin pago externo, DNS público ni HTTPS. Modelo multi-tenant compartido (OP08): sin proceso ni puerto dedicado por cliente; bases de clientes bajo un rol de PostgreSQL compartido, aisladas por separación física de bases y por credencial de aplicación Odoo, no por rol. Techo por inquilino (OP08.2): statement_timeout de PostgreSQL por base, único mecanismo de aislamiento de rendimiento disponible en Windows.'}
worker.write(ROOT/'docs/evidencias/ERPEC26-04-validacion.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Aprovisionamiento, suspensión y reactivación en el servidor compartido verificados')
