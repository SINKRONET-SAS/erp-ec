"""Recarga solamente la copia de revisión CM28, conservando datos sintéticos y credenciales privadas."""
import json,os,subprocess
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]
lab=json.loads((ROOT/'.cache/windows/cm28-lab.json').read_text(encoding='utf-8'))
work=Path(lab['work']).resolve();config=Path(lab['config']).resolve()
if not lab['name'].startswith('ec_restore_drill_cm28') or work.parent!=(ROOT/'.cache/windows/restore-drill').resolve() or config.parent!=work:
    raise ValueError('La configuración no corresponde a la copia aislada CM28.')
pidfile=work/'pid'
if pidfile.exists() and psutil.pid_exists(int(pidfile.read_text())):
    process=psutil.Process(int(pidfile.read_text()))
    if str(config) not in process.cmdline():raise ValueError('El proceso registrado no coincide con la copia.')
    for child in process.children(recursive=True):
        if str(config) in child.cmdline():child.terminate()
    process.terminate();process.wait(30)
command=[str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'.cache/odoo-community/odoo-bin'),'-c',str(config)]
result=subprocess.run(command+['-u','erpec_suite,erpec_selfservice,erpec_website_entry','--stop-after-init','--no-http'],capture_output=True,env={**os.environ,'PYTHONUTF8':'1'},timeout=900)
if result.returncode:raise RuntimeError('Falló la recarga; revisar el registro privado de la copia.')
process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={**os.environ,'PYTHONUTF8':'1'},creationflags=subprocess.CREATE_NO_WINDOW)
pidfile.write_text(str(process.pid),encoding='utf-8')
print('Copia aislada recargada en '+lab['url'])
