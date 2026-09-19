"""Rota la clave maestra de secretos de una instancia y re-cifra todo.
Uso: python scripts/rotate-secret-key.py <carpeta de la instancia en .cache/windows> [--estado]
Sin --estado: genera una clave nueva (si la clave vigente vive en el archivo erpec_secret.key), la anterior queda en
erpec_secret.previous solo para descifrar, y re-cifra todos los secretos. Con --estado solo informa (no cambia nada).
Con la clave en variable de entorno u odoo.conf: define la nueva clave, pasa la actual a ERPEC_SECRET_KEY_PREVIOUS,
reinicia y ejecuta este script (re-cifra con la vigente)."""
import configparser
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / '.cache' / 'windows' / sys.argv[1]
status_only = '--estado' in sys.argv
config = configparser.ConfigParser(interpolation=None)
config.read(folder / 'odoo.conf', encoding='utf-8')
os.environ.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
code = """
wizard = env['erpec.secret.rotation'].create({})
print('ORIGEN:', wizard.key_source, '| clave vigente:', wizard.current_key_id, '| claves anteriores:', wizard.previous_keys)
print(wizard.inventory)
%s
env.cr.commit()
""" % ("pass" if status_only else """
import os
from odoo.tools import config
if os.environ.get('ERPEC_SECRET_KEY') or config.get('erpec_secret_key'):
    wizard.action_reencrypt()
else:
    wizard.action_generate_and_reencrypt()
print(wizard.result)
wizard = env['erpec.secret.rotation'].create({})
print('DESPUES ->', wizard.key_source, '| clave vigente:', wizard.current_key_id, '| pendientes con otra clave:', wizard.pending)
print(wizard.inventory)
""")
result = subprocess.run([sys.executable, str(ROOT / '.cache/odoo-community/odoo-bin'), 'shell', '-c', str(folder / 'odoo.conf'), '--no-http'],
                        input=code, text=True, capture_output=True)
print(result.stdout[-3000:])
if result.returncode:
    print(result.stderr[-1500:])
    sys.exit(result.returncode)
