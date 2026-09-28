"""Copia aislada para revisión CM28. Solo lee el origen; bloquea cron y correo en la copia."""
import configparser,json,os,secrets,shutil,socket,subprocess,time
from pathlib import Path
import psycopg2
from psycopg2 import sql
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
PYTHON=ROOT/'.venv/Scripts/python.exe'
ODOO=ROOT/'.cache/odoo-community/odoo-bin'
PG=Path('C:/Program Files/PostgreSQL/17/bin')

def write(path,text):
    assert text.encode().decode()==text
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')

def run(command,**kwargs):
    result=subprocess.run([str(x) for x in command],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONUTF8':'1',**kwargs.pop('env',{})},**kwargs)
    if result.returncode:raise RuntimeError('Falló '+Path(str(command[0])).name+'; revisar los registros privados de la copia.')
    return result

def main():
    source=configparser.ConfigParser(interpolation=None);source.read(STATE/'fundador/odoo.conf',encoding='utf-8');original=source['options']
    cluster=json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
    name='ec_restore_drill_cm28'+secrets.token_hex(4)
    work=STATE/'restore-drill'/name;work.mkdir(parents=True,exist_ok=False)
    dbpass=secrets.token_urlsafe(24)
    connection=psycopg2.connect(host='127.0.0.1',port=55487,user='postgres',password=cluster['postgres'],dbname='postgres');connection.autocommit=True
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[name]);assert not cursor.fetchone()
        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)),[dbpass])
        cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {} TEMPLATE template0').format(sql.Identifier(name),sql.Identifier(name)))
        cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
    connection.close()
    dump=work/'origin.dump'
    run([PG/'pg_dump.exe','-h','127.0.0.1','-p','55487','-U','postgres','-Fc','-f',dump,original['db_name']],env={'PGPASSWORD':cluster['postgres']})
    run([PG/'pg_restore.exe','-h','127.0.0.1','-p','55487','-U','postgres','-d',name,'--no-owner','--no-privileges','--role='+name,dump],env={'PGPASSWORD':cluster['postgres']})
    data=work/'data';data.mkdir()
    filestore=Path(original['data_dir'])/'filestore'/original['db_name']
    if filestore.exists():shutil.copytree(filestore,data/'filestore'/name)
    key=Path(original['data_dir'])/'erpec_secret.key'
    if key.exists():shutil.copy2(key,data/key.name)
    connection=psycopg2.connect(host='127.0.0.1',port=55487,user=name,password=dbpass,dbname=name)
    with connection.cursor() as cursor:
        cursor.execute('UPDATE ir_cron SET active=false');cursor.execute('UPDATE ir_mail_server SET active=false')
        cursor.execute("SELECT name FROM ir_module_module WHERE state='installed' AND name LIKE 'erpec\\_%%'")
        modules=[row[0] for row in cursor.fetchall()]
        before={}
        for table in ['account_move','account_move_line','res_partner','erpec_subscription']:
            cursor.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)));before[table]=cursor.fetchone()[0]
    connection.commit();connection.close()
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    conf=configparser.ConfigParser(interpolation=None)
    conf['options']={'db_host':'127.0.0.1','db_port':'55487','db_user':name,'db_password':dbpass,'db_name':name,'dbfilter':'^'+name+'$',
        'addons_path':','.join(str(p) for p in [ROOT/'.cache/odoo-community/addons',ROOT/'.cache/odoo-community/odoo/addons',ROOT/'addons']),
        'data_dir':str(data),'list_db':'False','without_demo':'all','max_cron_threads':'0','http_interface':'127.0.0.1','http_port':str(port),'logfile':str(work/'odoo.log')}
    from io import StringIO
    output=StringIO();conf.write(output);config=work/'odoo.conf';write(config,output.getvalue())
    command=[PYTHON,ODOO,'-c',config]
    write(STATE/'cm28-lab.json',json.dumps({'name':name,'work':str(work),'config':str(config),'url':'http://127.0.0.1:'+str(port)},indent=2))
    run(command+['-u',','.join(modules),'-i','erpec_assets,erpec_website_entry,erpec_selfservice','--stop-after-init','--no-http'],timeout=1800)
    password=secrets.token_urlsafe(24)
    seed="password="+repr(password)+"\n"+"""from odoo import Command
company=env.company
plan=env['erpec.plan'].create({'name':'Equipo · oferta de ensayo','code':'CM28-UI','erp':True,'terms':'Oferta sintética exclusivamente para revisión local. Sin cobros reales.',
    'price':40,'max_users':2,'user_limit':20,'additional_user_price':8,'annual_enabled':True,'annual_price':400,'additional_user_annual_price':80,
    'fiscal_reviewed':True,'published':True,'option_ids':[Command.create({'capability_id':env.ref('erpec_suite.capability_sales').id}),Command.create({'capability_id':env.ref('erpec_suite.capability_assets').id,'kind':'optional','monthly_price':12,'annual_price':120})]})
for login in ['cm28_cliente_a','cm28_cliente_b']:
    env['res.users'].with_context(no_reset_password=True).create({'name':'Cliente de ensayo '+login[-1].upper(),'login':login,'password':password,'email':login+'@example.invalid','groups_id':[Command.set(env.ref('base.group_portal').ids)],'lang':'es_EC','tz':'America/Guayaquil'})
env.ref('base.user_admin').with_context(no_reset_password=True).write({'login':'cm28_admin','password':password})
env['ir.config_parameter'].sudo().set_param('auth_signup.invitation_scope','b2c')
env['ir.config_parameter'].sudo().set_param('web.base.url',%s)
env['ir.config_parameter'].sudo().set_param('web.base.url.freeze','True')
env['ir.cron'].search([]).write({'active':False})
env.cr.commit()
print('CM28_SEEDED='+str(plan.id))
""" % repr('http://127.0.0.1:'+str(port))
    result=run([PYTHON,ODOO,'shell','-c',config,'--no-http'],input=seed,timeout=180)
    plan_id=int(next(line.split('=')[1] for line in result.stdout.splitlines() if line.startswith('CM28_SEEDED=')))
    write(work/'ui-credentials.json',json.dumps({'password':password,'plan_id':plan_id}))
    process=subprocess.Popen([str(x) for x in command],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={**os.environ,'PYTHONUTF8':'1'},creationflags=subprocess.CREATE_NO_WINDOW)
    write(work/'pid',str(process.pid))
    write(work/'restore-check.json',json.dumps({'source':'fundador','restored':name,'business_rows_before_upgrade':before,'cron':False,'mail':False},indent=2))
    print('Copia CM28 preparada: http://127.0.0.1:'+str(port)+'; base '+name)

if __name__=='__main__':main()
