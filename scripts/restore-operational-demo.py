"""Restaura el respaldo en otra base y carpeta; conserva intacta la demo actual."""
import argparse, configparser, hashlib, io, json, os, secrets, shutil, subprocess, sys, uuid
from pathlib import Path
import psycopg2
from psycopg2 import sql
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
parser=argparse.ArgumentParser()
parser.add_argument('--backup',required=True,help='Respaldo operational-install dentro de .cache/windows/backups')
parser.add_argument('--expect-workspace',action='store_true',help='Comprueba un respaldo con centro de trabajo instalado')
args=parser.parse_args()
backup=Path(args.backup).resolve()
if not backup.is_relative_to((STATE/'backups').resolve()) or not backup.name.startswith('workspace-install-' if args.expect_workspace else 'operational-install-'):
    raise ValueError('El respaldo no pertenece al incremento operativo')
for item in ['database.dump','filestore','addons']:
    if not (backup/item).exists():
        raise ValueError('Respaldo incompleto: '+item)
name='ec_recovery_'+uuid.uuid4().hex[:10]
directory=STATE/'recoveries'/name
directory.mkdir(parents=True)
private=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
password=secrets.token_urlsafe(32)
connection=psycopg2.connect(host='127.0.0.1',port=55487,user='postgres',password=private['postgres'],dbname='postgres')
connection.autocommit=True
try:
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)),[password])
        cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {} TEMPLATE template0').format(sql.Identifier(name),sql.Identifier(name)))
        cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
finally:
    connection.close()
subprocess.run(['C:/Program Files/PostgreSQL/17/bin/pg_restore.exe','-h','127.0.0.1','-p','55487','-U',name,'-d',name,'--no-owner','--no-privileges','--exit-on-error',str(backup/'database.dump')],env={**os.environ,'PGPASSWORD':password},check=True)
shutil.copytree(backup/'filestore',directory/'data/filestore'/name)
shutil.copytree(backup/'addons',directory/'addons')
config=configparser.ConfigParser(interpolation=None)
config.read(STATE/'demo/odoo.conf',encoding='utf-8')
config['options'].update({'db_name':name,'db_user':name,'db_password':password,'dbfilter':'^'+name+'$','data_dir':str(directory/'data'),'addons_path':','.join(map(str,[ROOT/'.cache/odoo-community/addons',ROOT/'.cache/odoo-community/odoo/addons',directory/'addons'])),'http_port':'8569','max_cron_threads':'0','logfile':str(directory/'recovery.log')})
stream=io.StringIO();config.write(stream)
text=stream.getvalue()
assert text.encode('utf-8').decode('utf-8')==text
(directory/'odoo.conf').write_text(text,encoding='utf-8',newline='\n')
if args.expect_workspace:
    code="assert env['ir.module.module'].search_count([('name','=','erpec_workspace'),('state','=','installed')]) == 1\nassert env['erpec.workspace'].action_home()['res_id']\nassert env['account.move'].search_count([]) > 0\nprint('Centro de trabajo y asientos recuperados en copia aislada')\n"
else:
    code="assert not env.company.vat\nassert not env['ir.module.module'].search_count([('name','=','erpec_payroll'),('state','=','installed')])\nprint('Recuperación previa a importaciones y nómina verificada; demo actual conservada')\n"

def hashes(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
assert hashes(backup/'filestore') == hashes(directory/'data/filestore'/name)
assert hashes(backup/'addons') == hashes(directory/'addons')
subprocess.run([sys.executable,str(ROOT/'.cache/odoo-community/odoo-bin'),'shell','-c',str(directory/'odoo.conf'),'--no-http'],input=code,text=True,check=True)
result={'restoredDatabase':name,'configuration':str(directory/'odoo.conf'),'sourceBackup':str(backup),'currentDemoUntouched':True,'previousPayrollAbsent':not args.expect_workspace,'workspaceExpected':args.expect_workspace,'filestoreAndAddonsMatch':True}
text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
assert text.encode('utf-8').decode('utf-8')==text
(STATE/('workspace-restore-result.json' if args.expect_workspace else 'operational-restore-result.json')).write_text(text,encoding='utf-8',newline='\n')
print(json.dumps(result),flush=True)
