"""Copia de ensayo con rol propio para ejecutar los incrementos operativos."""
from pathlib import Path
import argparse, configparser, datetime, hashlib, io, json, os, secrets, shutil, subprocess, sys, time, uuid
import psutil, psycopg2
from psycopg2 import sql
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
DEMO=STATE/'demo'
SOURCE=ROOT/'.cache/odoo-community'
PG=Path('C:/Program Files/PostgreSQL/17/bin')
MODULES=['erpec_manufacturing','erpec_imports','erpec_payroll']

def write(path,text):
    assert text.encode('utf-8').decode('utf-8')==text
    path.write_text(text,encoding='utf-8',newline='\n')

def file_hashes():
    return {path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for module in MODULES for path in (ROOT/'addons'/module).rglob('*') if path.is_file() and path.suffix in ('.py','.xml','.csv')}

def prepare():
    import importlib.util
    spec=importlib.util.spec_from_file_location('session_access',ROOT/'scripts/demo-session-access.py')
    access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
    access.verify_session_access(DEMO)
    config=configparser.ConfigParser(interpolation=None);config.read(DEMO/'odoo.conf',encoding='utf-8');options=config['options']
    if options['db_name']!='erpec_demo' or options['http_port']!='8369':
        raise RuntimeError('La configuración no corresponde a la demo')
    name='ec_operational_'+uuid.uuid4().hex[:10]
    directory=STATE/'operational-tests'/name;directory.mkdir(parents=True)
    pid=int((DEMO/'pid').read_text())
    if psutil.pid_exists(pid):
        process=psutil.Process(pid)
        if str(DEMO/'odoo.conf') not in process.cmdline():
            raise RuntimeError('El proceso no pertenece a la demo')
        process.terminate();process.wait(30)
    else:
        print('La demo estaba detenida; se respalda antes de reiniciar',flush=True)
    try:
        subprocess.run([str(PG/'pg_dump.exe'),'-h',options['db_host'],'-p',options['db_port'],'-U',options['db_user'],'-d',options['db_name'],'-Fc','-f',str(directory/'database.dump')],env={**os.environ,'PGPASSWORD':options['db_password']},check=True)
        shutil.copytree(DEMO/'data/filestore'/options['db_name'],directory/'filestore')
        shutil.copytree(DEMO/'addons',directory/'addons-before',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    finally:
        process=subprocess.Popen([sys.executable,str(SOURCE/'odoo-bin'),'-c',str(DEMO/'odoo.conf')],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
        write(DEMO/'pid',str(process.pid))
    private=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
    password=secrets.token_urlsafe(32)
    conn=psycopg2.connect(host='127.0.0.1',port=55487,user='postgres',password=private['postgres'],dbname='postgres');conn.autocommit=True
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)),[password])
            cur.execute(sql.SQL('CREATE DATABASE {} OWNER {} TEMPLATE template0').format(sql.Identifier(name),sql.Identifier(name)))
            cur.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
    finally:
        conn.close()
    subprocess.run([str(PG/'pg_restore.exe'),'-h','127.0.0.1','-p','55487','-U',name,'-d',name,'--no-owner','--no-privileges','--exit-on-error',str(directory/'database.dump')],env={**os.environ,'PGPASSWORD':password},check=True)
    shutil.copytree(directory/'filestore',directory/'data/filestore'/name)
    options.update({'db_name':name,'db_user':name,'db_password':password,'dbfilter':'^'+name+'$','http_port':'8469','max_cron_threads':'0','data_dir':str(directory/'data'),'addons_path':','.join(map(str,[SOURCE/'addons',SOURCE/'odoo/addons',ROOT/'addons'])),'logfile':str(directory/'tests.log')})
    output=io.StringIO();config.write(output);write(directory/'odoo.conf',output.getvalue())
    write(STATE/'operational-current.json',json.dumps({'directory':str(directory),'database':name}))
    return directory

def test(directory):
    test_log=directory/('operational-tests-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.log')
    command=[sys.executable,str(SOURCE/'odoo-bin'),'-c',str(directory/'odoo.conf'),'-i',','.join(MODULES),'-u',','.join(MODULES),'--test-enable','--test-tags',','.join('/'+module for module in MODULES),'--stop-after-init','--no-http','--logfile',str(test_log)]
    before=file_hashes()
    result=subprocess.run(command,env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'})
    if before!=file_hashes():
        raise RuntimeError('Los archivos cambiaron mientras se ejecutaban las pruebas; repetir antes de instalar')
    shutil.copyfile(test_log,directory/'unit-tests.log')
    report={'logFile':str(directory/'unit-tests.log'),'exitCode':result.returncode,'directory':str(directory),'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'modules':MODULES,'fileHashes':file_hashes(),'logSha256':hashlib.sha256(test_log.read_bytes()).hexdigest()}
    write(STATE/'operational-test-result.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'exitCode':result.returncode,'directory':str(directory)}),flush=True)
    sys.exit(result.returncode)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    directory=prepare() if args.prepare else Path(json.loads((STATE/'operational-current.json').read_text())['directory'])
    test(directory)
