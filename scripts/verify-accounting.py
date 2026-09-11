"""Verifica la operación Community en una copia aislada del cliente local."""
from pathlib import Path
import configparser,datetime,hashlib,json,os,shutil,subprocess,sys,uuid
import psycopg2
from psycopg2 import sql
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
INSTANCE='b0bdbfd97ff34409b0fe0ea9eff6793f'
DIRECTORY=STATE/'instances'/INSTANCE
config=configparser.ConfigParser(interpolation=None)
config.read(DIRECTORY/'odoo.conf',encoding='utf-8')
options=config['options']
PG=Path('C:/Program Files/PostgreSQL/17/bin')
name='ec_withholding_accounting_'+uuid.uuid4().hex[:10]
backup=STATE/'withholding_accounting-tests'/name
backup.mkdir(parents=True)
environment={**os.environ,'PGPASSWORD':options['db_password']}
subprocess.run([str(PG/'pg_dump.exe'),'-h',options['db_host'],'-p',options['db_port'],'-U',options['db_user'],'-d',options['db_name'],'-Fc','-f',str(backup/'database.dump')],env=environment,check=True)
private=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
connection=psycopg2.connect(host='127.0.0.1',port=55487,user='postgres',password=private['postgres'],dbname='postgres')
connection.autocommit=True
with connection.cursor() as cursor:
 cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {} TEMPLATE template0').format(sql.Identifier(name),sql.Identifier(options['db_user'])))
 cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
connection.close()
subprocess.run([str(PG/'pg_restore.exe'),'-h',options['db_host'],'-p',options['db_port'],'-U',options['db_user'],'-d',name,'--exit-on-error',str(backup/'database.dump')],env=environment,check=True)
shutil.copytree(DIRECTORY/'data/filestore'/options['db_name'],backup/'data/filestore'/name)
source=ROOT/'.cache/odoo-community'
log=backup/'tests.log'
result=subprocess.run([sys.executable,str(source/'odoo-bin'),'-c',str(DIRECTORY/'odoo.conf'),'-d',name,'--db-filter','^'+name+'$','--addons-path',','.join(map(str,[source/'addons',source/'odoo/addons',ROOT/'addons'])),'--data-dir',str(backup/'data'),'-i','erpec_withholding_accounting','-u','erpec_withholding_accounting','--test-enable','--test-tags','/erpec_withholding_accounting','--stop-after-init','--no-http','--http-interface','127.0.0.1','--http-port','0','--max-cron-threads','0','--logfile',str(log)])
report={'database':name,'exitCode':result.returncode,'log':str(log),'backup':str(backup),'scope':'Copia del cliente; datos sinteticos y sin emision fiscal','fileHashes':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'addons/erpec_withholding_accounting').rglob('*') if p.is_file() and p.suffix in ('.py','.xml','.csv')}}
(STATE/'withholding_accounting-test-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(report),flush=True)
sys.exit(result.returncode)
