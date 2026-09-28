"""Actualización CM28 con ventana de mantenimiento, respaldo completo y recuperación identificada."""
import importlib.util,json,os,subprocess,time
from pathlib import Path
import psutil,requests
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'

def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def write(path,text):
    assert text.encode().decode()==text;path.write_text(text,encoding='utf-8',newline='\n')

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('instances',nargs='+',choices=['fundador','demo','a','b']);args=parser.parse_args()
    baseline=ROOT/'.cache/cm28-baseline/addons'
    if not baseline.is_dir():raise RuntimeError('Falta el código previo verificado para reversión.')
    for name in ['founder','demo']:
        report=json.loads((ROOT/('docs/evidencias/CM28/restore-'+name+'.json')).read_text(encoding='utf-8'))
        probe=report.get('integrity',{}).get('probe',{})
        if any(report['integrity']['source_minus_restored'].values()) or not report['restore']['login_ready'] or probe.get('attachments_missing_file')!=0 or (probe.get('cert_present') and not probe.get('decrypt_with_restored_key')):
            raise RuntimeError('La restauración previa no está aprobada: '+name)
    supervisor=load('cm28_supervisor','supervisor-windows.py');updater=load('cm28_updater','update-instance.py')
    for name in args.instances:write(STATE/name/'maintenance.json',json.dumps({'phase':'CM28-F','reason':'Actualización autorizada con respaldo'}))
    supervisor_path=(ROOT/'scripts/supervisor-windows.py').resolve()
    for process in psutil.process_iter(['cmdline']):
        if any(str(arg).replace('\\','/').lower()==supervisor_path.as_posix().lower() for arg in (process.info['cmdline'] or [])):
            process.terminate()
    password=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))['postgres']
    results=[]
    try:
        for name in args.instances:
            supervisor.stop(name)
            stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
            additions=['erpec_assets','erpec_website_entry','erpec_selfservice'] if name in ('demo','fundador') else []
            result=updater.update(name,False,password,stamp,install_modules=additions,baseline=baseline)
            if result['desfase']!='sin desfase':raise RuntimeError('Quedó desfase de esquema: '+name)
            (STATE/name/'maintenance.json').unlink()
            supervisor.start(name)
            healthy=False
            for attempt in range(30):
                if supervisor.healthy(supervisor.INSTANCES[name]):healthy=True;break
                time.sleep(2)
            if not healthy:raise RuntimeError('La instancia actualizada no responde: '+name)
            result['login_ready']=True;results.append(result)
            write(ROOT/('docs/evidencias/CM28/update-'+name+'.json'),json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            print('Actualización verificada: '+name,flush=True)
    finally:
        supervisor.spawn([str(supervisor.PYTHON),str(supervisor_path)],subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
