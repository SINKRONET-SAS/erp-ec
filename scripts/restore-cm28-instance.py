"""Reversión explícita desde un respaldo CM28. Sin --apply valida y describe, sin modificar la instancia."""
import argparse,configparser,importlib.util,json,os,shutil,subprocess,time
from pathlib import Path
import psycopg2,psutil
from psycopg2 import sql
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
PG=Path('C:/Program Files/PostgreSQL/17/bin')

def write(path,text):
    assert text.encode().decode()==text;path.write_text(text,encoding='utf-8',newline='\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    report=json.loads(Path(args.report).read_text(encoding='utf-8'));backup=(ROOT/report['respaldo']).resolve()
    if not backup.is_relative_to((STATE/'backups').resolve()):raise ValueError('Respaldo fuera del directorio autorizado.')
    meta=json.loads((backup/'restore.json').read_text(encoding='utf-8'));name=meta['instance']
    if name not in ('fundador','demo','a','b'):raise ValueError('Instancia desconocida.')
    config=STATE/name/'odoo.conf';current=configparser.ConfigParser(interpolation=None);current.read(config,encoding='utf-8')
    if current['options']['db_name']!=meta['database']:raise ValueError('El destino no coincide con el respaldo.')
    data=Path(meta['data_dir']).resolve()
    if not data.is_relative_to(STATE.resolve()):raise ValueError('Directorio de datos fuera del espacio local.')
    dump=backup/(meta['database']+'.dump')
    if not dump.is_file() or not (backup/'addons').is_dir():raise ValueError('Falta base o código del respaldo.')
    subprocess.run([str(PG/'pg_restore.exe'),'--list',str(dump)],stdout=subprocess.DEVNULL,check=True)
    if not args.apply:
        print('Respaldo válido para '+name+'. La aplicación requiere --apply; se preservará además una copia de la base actual.')
        return
    spec=importlib.util.spec_from_file_location('recovery_supervisor',ROOT/'scripts/supervisor-windows.py')
    supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
    marker=STATE/name/'maintenance.json';write(marker,json.dumps({'phase':'CM28-reversion','backup':backup.name}))
    for process in psutil.process_iter(['cmdline']):
        if str(ROOT/'scripts/supervisor-windows.py') in (process.info['cmdline'] or []):process.terminate()
    supervisor.stop(name)
    password=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))['postgres']
    environment={**os.environ,'PGPASSWORD':password}
    rescue=STATE/'backups'/('before-restore-'+name+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));rescue.mkdir()
    try:
        subprocess.run([str(PG/'pg_dump.exe'),'-h','127.0.0.1','-p','55487','-U','postgres','-Fc','-f',str(rescue/'current.dump'),meta['database']],env=environment,check=True)
        connection=psycopg2.connect(host='127.0.0.1',port=55487,user='postgres',password=password,dbname='postgres');connection.autocommit=True
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s',[meta['database']])
                if cursor.fetchone()[0]!=meta['db_user']:raise ValueError('Propietario inesperado; reversión detenida.')
                cursor.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(meta['database'])))
                cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {} TEMPLATE template0').format(sql.Identifier(meta['database']),sql.Identifier(meta['db_user'])))
                cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(meta['database'])))
        finally:connection.close()
        subprocess.run([str(PG/'pg_restore.exe'),'-h','127.0.0.1','-p','55487','-U','postgres','-d',meta['database'],'--no-owner','--no-privileges','--role='+meta['db_user'],str(dump)],env=environment,check=True)
        if (backup/'filestore').exists():shutil.copytree(backup/'filestore',data/'filestore'/meta['database'],dirs_exist_ok=True)
        key=Path(meta['key_backup']).resolve()/'erpec_secret.key'
        if not key.is_relative_to((STATE/'backups-keys').resolve()):raise ValueError('Clave fuera del directorio esperado.')
        if key.exists():shutil.copy2(key,data/'erpec_secret.key')
        saved=configparser.ConfigParser(interpolation=None);saved.read(backup/'odoo.conf',encoding='utf-8')
        saved['options']['addons_path']=','.join(str(p) for p in [ROOT/'.cache/odoo-community/addons',ROOT/'.cache/odoo-community/odoo/addons',backup/'addons'])
        from io import StringIO
        output=StringIO();saved.write(output);write(config,output.getvalue())
        marker.unlink();supervisor.start(name)
        print('Base, archivos, clave y código previo restaurados para '+name+'. Verificar el acceso y las operaciones antes de salir de mantenimiento.')
    finally:
        supervisor.spawn([str(supervisor.PYTHON),str(ROOT/'scripts/supervisor-windows.py')],subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__':main()
