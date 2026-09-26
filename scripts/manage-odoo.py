"""Actualiza o detiene únicamente los dos procesos del piloto ERP EC."""
import argparse
import json
import pathlib
import subprocess
import psutil

ROOT=pathlib.Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
PYTHON=ROOT/'.venv/Scripts/python.exe'
SOURCE=ROOT/'.cache/odoo-community'

def stop():
    for tenant in ['a','b']:
        pidfile=STATE/tenant/'pid'
        if not pidfile.exists():
            print('Sin PID registrado para',tenant)
            continue
        pid=int(pidfile.read_text())
        if not psutil.pid_exists(pid):
            print('El proceso registrado ya terminó:',tenant)
            continue
        process=psutil.Process(pid)
        arguments=process.cmdline()
        expected=str(STATE/tenant/'odoo.conf')
        if expected not in arguments or str(SOURCE/'odoo-bin') not in arguments:
            raise ValueError('El PID no corresponde al piloto; no se detiene')
        process.terminate()
        process.wait(timeout=30)
        print('Proceso del piloto detenido:',tenant)

def update():
    stop()
    # DI26-01: actualizar todos los módulos erpec_* instalados, con respaldo y comprobación de desfase.
    subprocess.run([str(PYTHON),str(ROOT/'scripts/update-instance.py'),'a','b'],check=True)
    for tenant in ['a','b']:
        code="lang=env['res.lang'].with_context(active_test=False).search([('code','=','es_EC')],limit=1)\nassert lang, 'No existe idioma es_EC'\nenv['base.language.install'].create({'lang_ids':[(6,0,lang.ids)],'overwrite':False}).lang_install()\nenv.ref('base.user_admin').write({'lang':'es_EC','tz':'America/Guayaquil'})\nhasattr(env['res.company'], '_ec_apply_locale_defaults') and env['res.company']._ec_apply_locale_defaults()\nenv.cr.commit()\n"
        subprocess.run([str(PYTHON),str(SOURCE/'odoo-bin'),'shell','-c',str(STATE/tenant/'odoo.conf'),'--no-http'],input=code,text=True,check=True)
    subprocess.run([str(PYTHON),str(ROOT/'scripts/windows-local.py'),'start'],check=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['stop','update'])
    action=parser.parse_args().action
    stop() if action=='stop' else update()
