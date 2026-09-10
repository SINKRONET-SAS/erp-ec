"""Instala el controlador solo en el piloto del operador y verifica regresiones."""
import pathlib
import subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
PYTHON = ROOT/'.venv/Scripts/python.exe'
subprocess.run([str(PYTHON),str(ROOT/'scripts/manage-odoo.py'),'stop'],check=True)
subprocess.run([str(PYTHON),str(ROOT/'.cache/odoo-community/odoo-bin'),'-c',str(ROOT/'.cache/windows/a/odoo.conf'),'-i','erpec_provision','-u','erpec_suite,erpec_provision','--test-enable','--test-tags','/erpec_suite,/erpec_provision','--stop-after-init','--no-http'],check=True)
subprocess.run([str(PYTHON),str(ROOT/'scripts/windows-local.py'),'start'],check=True)
