"""Instala el módulo de contratos y ejecuta pruebas transaccionales en los pilotos."""
import pathlib
import subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv/Scripts/python.exe'
SOURCE = ROOT / '.cache/odoo-community'
subprocess.run([str(PYTHON), str(ROOT/'scripts/manage-odoo.py'), 'stop'], check=True)
for tenant in ['a', 'b']:
    subprocess.run([str(PYTHON), str(SOURCE/'odoo-bin'), '-c', str(ROOT/f'.cache/windows/{tenant}/odoo.conf'), '-i', 'erpec_suite', '-u', 'erpec_suite', '--test-enable', '--test-tags', '/erpec_suite', '--stop-after-init', '--no-http'], check=True)
subprocess.run([str(PYTHON), str(ROOT/'scripts/windows-local.py'), 'start'], check=True)
