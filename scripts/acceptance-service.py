"""Inicia o detiene solo la copia operativa seleccionada para aceptación visual."""
import argparse
import configparser
import json
import os
from pathlib import Path
import subprocess
import sys
import psutil

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['start', 'stop'])
args = parser.parse_args()
current = json.loads((STATE / 'operational-current.json').read_text(encoding='utf-8'))
directory = Path(current['directory']).resolve()
if not directory.is_relative_to((STATE / 'operational-tests').resolve()):
    raise RuntimeError('La carpeta no pertenece a las copias de aceptación.')
config_path = directory / 'odoo.conf'
config = configparser.ConfigParser(interpolation=None)
config.read(config_path, encoding='utf-8')
options = config['options']
if options['db_name'] != current['database'] or not options['db_name'].startswith('ec_operational_') or options['http_port'] != '8469' or options['http_interface'] != '127.0.0.1':
    raise RuntimeError('La configuración no corresponde a la copia aislada esperada.')
pid_path = directory / 'ui.pid'
if pid_path.exists():
    pid = int(pid_path.read_text())
    if psutil.pid_exists(pid):
        process = psutil.Process(pid)
        if str(config_path) not in process.cmdline():
            raise RuntimeError('El proceso registrado pertenece a otro servicio.')
        if args.action == 'start':
            raise RuntimeError('La copia de aceptación ya está en ejecución.')
        process.terminate()
        process.wait(30)
        print('Copia de aceptación detenida; demo conservada.')
    elif args.action == 'stop':
        print('La copia de aceptación ya estaba detenida.')
    pid_path.unlink()
elif args.action == 'stop':
    raise RuntimeError('No existe un proceso registrado de aceptación.')
if args.action == 'start':
    session_dir = directory / 'data/sessions'
    session_dir.mkdir(parents=True, exist_ok=True)
    import tempfile
    with tempfile.TemporaryFile(dir=session_dir):
        pass
    process = subprocess.Popen([sys.executable, str(ROOT / '.cache/odoo-community/odoo-bin'), '-c', str(config_path)], cwd=ROOT, env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}, creationflags=subprocess.CREATE_NO_WINDOW)
    value = str(process.pid)
    assert value.encode('utf-8').decode('utf-8') == value
    pid_path.write_text(value, encoding='utf-8', newline='\n')
    print('Copia iniciada: http://localhost:8469/web/login; sesión independiente de la demo.')
