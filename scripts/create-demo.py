"""Crea y arranca una demo con base y archivos propios; nunca clona datos del cliente."""
from pathlib import Path
import configparser,json,secrets,shutil,socket,subprocess,sys,time,xmlrpc.client
import psutil,psycopg2,requests
from psycopg2 import sql
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
DIRECTORY=STATE/'demo'
SOURCE=ROOT/'.cache/odoo-community'
DIRECTORY.mkdir(exist_ok=True)
NAME='erpec_demo'
PORT=8369
report=json.loads((STATE/'withholding_accounting-test-result.json').read_text(encoding='utf-8'))
if report['exitCode'] != 0:
    raise RuntimeError('Faltan pruebas aprobadas del módulo contable')
import hashlib
for name,digest in report['fileHashes'].items():
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('El módulo cambió después de las pruebas')
privatefile=DIRECTORY/'credentials.json'
if not privatefile.exists():
    privatefile.write_text(json.dumps({key:secrets.token_urlsafe(24) for key in ('database','admin','manager')}),encoding='utf-8')
private=json.loads(privatefile.read_text(encoding='utf-8'))
conf=DIRECTORY/'odoo.conf'
if not (DIRECTORY/'initialized.json').exists():
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',PORT))==0:
            raise RuntimeError('El puerto de la demo ya está ocupado')
    cluster=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
    connection=psycopg2.connect(host='127.0.0.1',port=55487,user='postgres',password=cluster['postgres'],dbname='postgres')
    connection.autocommit=True
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',[NAME])
        if not cursor.fetchone():
            cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(NAME)),[private['database']])
        cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s',[NAME])
        owner=cursor.fetchone()
        if owner and owner[0]!=NAME:
            raise RuntimeError('La base existente no pertenece a la demo')
        if not owner:
            cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(NAME),sql.Identifier(NAME)))
        cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(NAME)))
    connection.close()
    for module in ('erpec_base','erpec_operations','erpec_fiscal_documents','erpec_withholding_accounting'):
        shutil.copytree(ROOT/'addons'/module,DIRECTORY/'addons'/module,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    config=configparser.ConfigParser(interpolation=None)
    config['options']={'admin_passwd':private['manager'],'db_host':'127.0.0.1','db_port':'55487','db_user':NAME,'db_password':private['database'],'db_name':NAME,'dbfilter':'^'+NAME+'$','list_db':'False','http_interface':'127.0.0.1','http_port':str(PORT),'workers':'0','max_cron_threads':'0','without_demo':'all','data_dir':str(DIRECTORY/'data'),'addons_path':','.join(map(str,[SOURCE/'addons',SOURCE/'odoo/addons',DIRECTORY/'addons'])),'logfile':str(DIRECTORY/'odoo.log')}
    with conf.open('w',encoding='utf-8',newline='\n') as handle:
        config.write(handle)
    subprocess.run([sys.executable,str(SOURCE/'odoo-bin'),'-c',str(conf),'-i','erpec_withholding_accounting','--no-http','--stop-after-init'],check=True)
    seed="exec(compile(open("+repr(str(ROOT/'scripts/seed-demo.py'))+",encoding='utf-8').read(),'seed-demo.py','exec'))"
    subprocess.run([sys.executable,str(SOURCE/'odoo-bin'),'shell','-c',str(conf),'--no-http'],input=seed,text=True,check=True)
    (DIRECTORY/'initialized.json').write_text(json.dumps({'database':NAME,'purpose':'demo sintética comercial'}),encoding='utf-8')
    (DIRECTORY/'ACCESO_DEMO.txt').write_text('DEMO LOCAL — DATOS FICTICIOS\nURL: http://127.0.0.1:8369\nUsuario: demo\nContraseña: '+private['admin']+'\nNo publicar este archivo.\n',encoding='utf-8')
process=None
pidfile=DIRECTORY/'pid'
if pidfile.exists() and psutil.pid_exists(int(pidfile.read_text())):
    candidate=psutil.Process(int(pidfile.read_text()))
    if str(conf) not in candidate.cmdline():
        raise RuntimeError('El proceso registrado no pertenece a la demo')
    process=candidate
if process is None:
    process=subprocess.Popen([sys.executable,str(SOURCE/'odoo-bin'),'-c',str(conf)],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
    pidfile.write_text(str(process.pid),encoding='utf-8')
for attempt in range(60):
    try:
        uid=xmlrpc.client.ServerProxy('http://127.0.0.1:8369/xmlrpc/2/common').authenticate(NAME,'demo',private['admin'],{})
        if uid:
            break
    except (OSError,xmlrpc.client.Error):
        if attempt==59:
            raise RuntimeError('La demo no respondió tras iniciarse') from None
    time.sleep(1)
else:
    raise RuntimeError('No se autenticó la demo')
print((DIRECTORY/'demo-result.json').read_text(encoding='utf-8'))
