"""Comprobación de solo lectura tras CM28: acceso, datos preservados y pantallas reales."""
import configparser,hashlib,json,xmlrpc.client
from pathlib import Path
from ui_common import playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
    reports=[]
    with playwright()() as pw:
        browser=pw.chromium.launch(headless=True)
        for name,port in [('fundador',8199),('demo',8369)]:
            private=json.loads((ROOT/'.cache/windows'/name/'credentials.json').read_text(encoding='utf-8'))
            config=configparser.ConfigParser(interpolation=None);config.read(ROOT/'.cache/windows'/name/'odoo.conf',encoding='utf-8')
            database=config['options']['db_name'];password=private['admin'];url='http://127.0.0.1:'+str(port)
            uid=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(database,name,password,{})
            assert uid,'No se pudo autenticar '+name
            models=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
            def call(model,method,args,kwargs=None):return models.execute_kw(database,uid,password,model,method,args,kwargs or {})
            def action(module,item):return call('ir.model.data','search_read',[[('module','=',module),('name','=',item)]],{'fields':['res_id']})[0]['res_id']
            baseline=json.loads((ROOT/('docs/evidencias/CM28/restore-'+('founder' if name=='fundador' else name)+'.json')).read_text(encoding='utf-8'))
            counts={model:call(model,'search_count',[[]]) for model in ['account.move','account.move.line']}
            for model,count in counts.items():assert count==baseline['integrity']['row_counts_source'][model.replace('.','_')],model+' cambió'
            plans=call('erpec.plan','search_read',[[('code','=','SS-DEMO')]],{'fields':['published']})
            assert all(not plan['published'] for plan in plans)
            modules=call('ir.module.module','search_read',[[('name','in',['erpec_assets','erpec_entitlements','erpec_selfservice','erpec_website_entry'])]],{'fields':['name','state']})
            assert len(modules)==4 and all(module['state']=='installed' for module in modules)
            context=browser.new_context(viewport={'width':1440,'height':1000},locale='es-EC');page=context.new_page();page.set_default_timeout(90000)
            page.goto(url+'/autoservicio');page.wait_for_load_state('networkidle')
            assert page.locator('.cm28-hero h1').is_visible()
            assert page.locator('a[href^="/autoservicio/contratar"]').count()==0
            assert not page.get_by_text('Error de estilo',exact=True).is_visible()
            capture=ROOT/('docs/evidencias/CM28/ui/'+name+'-local.png');page.screenshot(path=str(capture),full_page=True)
            page.goto(url+'/web/login');page.locator('input[name=login]').fill(name);page.locator('input[name=password]').fill(password)
            page.locator('form.oe_login_form button[type=submit]').click();page.wait_for_selector('.o_main_navbar')
            page.goto(url+'/odoo/action-'+str(action('erpec_suite','plans_action')));page.wait_for_selector('.o_list_view')
            page.goto(url+'/odoo/action-'+str(action('erpec_assets','asset_action')));page.wait_for_selector('.o_list_view')
            assert not page.locator('.o_error_dialog').count()
            context.close()
            reports.append({'instance':name,'login':'validado con credencial existente, sin reset','counts':counts,'historical_accounting_preserved':True,
                'ss_demo_unpublished':True,'new_modules_installed':True,'landing_and_admin_views':True,'public_checkout_disabled_without_offers':True,
                'screenshot':capture.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(capture.read_bytes()).hexdigest()})
        browser.close()
    text=json.dumps(reports,ensure_ascii=False,indent=2)+'\n';assert text.encode().decode()==text
    (ROOT/'docs/evidencias/CM28/local-verification.json').write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps(reports,ensure_ascii=False))

if __name__=='__main__':main()
