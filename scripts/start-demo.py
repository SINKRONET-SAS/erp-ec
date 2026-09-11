"""Inicia o reinicia solo la demo con comprobación previa de sesiones."""
import argparse,configparser,importlib.util,subprocess
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1];DEMO=ROOT/'.cache/windows/demo';CONF=DEMO/'odoo.conf'
spec=importlib.util.spec_from_file_location('session_access',ROOT/'scripts/demo-session-access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
parser=argparse.ArgumentParser();parser.add_argument('--restart',action='store_true');args=parser.parse_args()
config=configparser.ConfigParser(interpolation=None);config.read(CONF,encoding='utf-8')
if config['options']['db_name']!='erpec_demo' or config['options']['http_port']!='8369' or Path(config['options']['data_dir']).resolve()!=(DEMO/'data').resolve():raise RuntimeError('Configuración distinta de la demo')
access.verify_session_access(DEMO)
pidfile=DEMO/'pid'
if pidfile.exists() and psutil.pid_exists(int(pidfile.read_text())):
    process=psutil.Process(int(pidfile.read_text()))
    if str(CONF) not in process.cmdline():raise RuntimeError('El proceso registrado no corresponde a la demo')
    if not args.restart:raise RuntimeError('Demo activa. Usar --restart para reiniciarla con el usuario actual')
    process.terminate();process.wait(30)
process=subprocess.Popen([str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'.cache/odoo-community/odoo-bin'),'-c',str(CONF)],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
pidfile.write_text(str(process.pid),encoding='utf-8')
print('Demo iniciada con acceso de escritura a sesiones: http://127.0.0.1:8369')
