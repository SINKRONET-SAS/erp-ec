"""Activa el módulo validado solo en el piloto operador, con respaldo y reinicio controlado."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil
import requests

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
PYTHON=ROOT/'.venv/Scripts/python.exe'
ODOO=ROOT/'.cache/odoo-community/odoo-bin'
CONF=STATE/'a/odoo.conf'
report=json.loads((STATE/'payphone-test-result.json').read_text(encoding='utf-8'))
if report['exitCode'] != 0:
    raise RuntimeError('Las pruebas todavía no están aprobadas.')
for relative, expected in report['moduleHashes'].items():
    path=ROOT/relative
    if not path.resolve().is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Cambió un archivo después de las pruebas: '+relative)
private=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
backup=STATE/'backups'/('payphone-install-'+time.strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True)
subprocess.run([r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe','-h','127.0.0.1','-p','55487','-U','erpec_a','-d','erpec_a','-Fc','-f',str(backup/'database.dump')],env={**os.environ,'PGPASSWORD':private['a']},check=True)
pidfile=STATE/'a/pid'
if pidfile.exists() and psutil.pid_exists(int(pidfile.read_text())):
    process=psutil.Process(int(pidfile.read_text()))
    args=process.cmdline()
    if str(CONF) not in args or str(ODOO) not in args:
        raise RuntimeError('El PID no corresponde al piloto operador; no se detiene.')
    process.terminate()
    process.wait(timeout=30)
try:
    result=subprocess.run([str(PYTHON),str(ODOO),'-c',str(CONF),'-i','erpec_payphone','--stop-after-init','--no-http','--max-cron-threads','0','--logfile',str(STATE/'payphone-install.log')])
    if result.returncode:
        raise RuntimeError('Odoo rechazó la instalación. Revisar payphone-install.log.')
    seed="""
provider=env['erpec.payphone.provider'].search([('company_id','=',env.company.id)],limit=1)
if not provider:
    provider=env['erpec.payphone.provider'].create({'company_id':env.company.id,'public_url':'https://pruebas.sinkronet.com.ec'})
plan=env['erpec.plan'].search([('code','=','PAYPHONE-LOCAL-TEST')],limit=1)
if not plan:
    plan=env['erpec.plan'].create({'name':'Ensayo local PayPhone','code':'PAYPHONE-LOCAL-TEST','erp':True,'terms':'Exclusivamente validación técnica local. No es una tarifa comercial ni habilita producción.'})
contract=env['erpec.subscription'].search([('name','=','PAYPHONE-ENSAYO-LOCAL'),('company_id','=',env.company.id)],limit=1)
if not contract:
    from datetime import timedelta
    contract=env['erpec.subscription'].create({'name':'PAYPHONE-ENSAYO-LOCAL','plan_id':plan.id,'starts_on':fields.Date.today(),'ends_on':fields.Date.today()+timedelta(days=7),'billing_owner':'payphone_test','billing_reference':'SK_ERP PayPhone en ambiente Prueba','authorization':'Ensayo de integración local solicitado por el usuario; requiere confirmar el pago antes de activar.'})
payment=env['erpec.payphone.payment'].search([('subscription_id','=',contract.id)],limit=1)
if not payment:
    payment=env['erpec.payphone.payment'].create({'subscription_id':contract.id,'provider_id':provider.id,'amount_without_tax':1.0})
env.cr.commit()
print('PAYPHONE_SETUP',provider.id,payment.id)
"""
    seed='from odoo import fields\n'+seed
    subprocess.run([str(PYTHON),str(ODOO),'shell','-c',str(CONF),'--no-http','--logfile',str(STATE/'payphone-install.log')],input=seed,text=True,check=True)
finally:
    process=subprocess.Popen([str(PYTHON),str(ODOO),'-c',str(CONF)],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
    pidfile.write_text(str(process.pid),encoding='utf-8')
for attempt in range(30):
    try:
        response=requests.get('http://127.0.0.1:8169/web/login',timeout=3)
        if response.status_code==200:
            print('Odoo operador activo; respaldo conservado. No se ha contactado PayPhone.')
            break
    except requests.RequestException:
        if attempt==29:
            raise RuntimeError('Odoo no respondió tras el arranque; revisar registro local.')
    time.sleep(1)
else:
    raise RuntimeError('Odoo no devolvió una pantalla de acceso correcta.')
