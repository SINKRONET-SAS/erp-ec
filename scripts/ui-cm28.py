"""Recorrido visual reproducible sobre la copia CM28; no procesa pagos ni ejecuta cron."""
import json,hashlib,xmlrpc.client
from pathlib import Path
from ui_common import playwright,run_axe
ROOT=Path(__file__).resolve().parents[1]

def main():
    lab=json.loads((ROOT/'.cache/windows/cm28-lab.json').read_text(encoding='utf-8'))
    private=json.loads((Path(lab['work'])/'ui-credentials.json').read_text(encoding='utf-8'))
    url=lab['url'];password=private['password'];plan_id=private['plan_id']
    target=ROOT/'docs/evidencias/CM28/ui';target.mkdir(parents=True,exist_ok=True)
    report={'environment':'Copia aislada del fundador; tarifas y cuentas sintéticas','checks':[],'axe':{},'screenshots':[]}
    with playwright()() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='es-EC')
        page=context.new_page();page.set_default_timeout(60000)
        def shot(name):
            path=target/(name+'.png');page.screenshot(path=str(path),full_page=True)
            report['screenshots'].append({'file':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        def check_view(name):
            page.wait_for_load_state('networkidle')
            overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            assert not overflow,'Desbordamiento horizontal en '+name
            assert not page.get_by_text('Error de estilo',exact=True).is_visible(),'Error de compilación de estilos'
            report['axe'][name]=run_axe(page)
            shot(name)
        def login(user):
            page.goto(url+'/web/login')
            page.locator('input[name=login]').fill(user)
            page.locator('input[name=password]').fill(password)
            page.locator('form.oe_login_form button[type=submit]').click()
            page.wait_for_url(lambda u:'/web/login' not in str(u),timeout=90000)
        response=page.goto(url+'/autoservicio');assert response.status==200
        assert '+1 555-555-5556' not in page.locator('body').inner_text()
        assert page.locator('.cm28-hero h1').is_visible()
        check_view('landing-desktop')
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement.tagName')!='BODY'
        page.set_viewport_size({'width':390,'height':844});check_view('landing-mobile')
        login('cm28_cliente_a')
        page.goto(url+'/autoservicio/contratar?plan_id='+str(plan_id))
        page.locator('#period').select_option('annual')
        page.locator('#user_quantity').fill('5')
        page.locator('input[type=checkbox][name=option_ids]').check()
        page.get_by_role('button',name='Actualizar desglose').click()
        assert '760.00' in page.locator('.cm28-summary').inner_text()
        check_view('contratacion-mobile')
        page.set_viewport_size({'width':1440,'height':1000});check_view('contratacion-desktop')
        page.locator('#company_name').fill('Cliente visual CM28')
        page.locator('#company_vat').fill('1799999990001')
        page.locator('#street').fill('Dirección sintética de revisión')
        page.get_by_role('button',name='Solicitar pago por PayPhone').click()
        page.wait_for_url('**/mi-servicio/alta/**')
        progress_url=page.url
        assert 'Esperando pago' in page.locator('main').inner_text()
        check_view('seguimiento')
        context.close()
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='es-EC');page=context.new_page();page.set_default_timeout(60000)
        login('cm28_cliente_b')
        response=page.goto(progress_url);assert response.status==404
        report['checks'].append('Otro titular recibe 404 al abrir el alta ajena')
        context.close()
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='es-EC');page=context.new_page();page.set_default_timeout(60000)
        login('cm28_admin')
        uid=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(lab['name'],'cm28_admin',password,{})
        models=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
        def action(module,name):
            values=models.execute_kw(lab['name'],uid,password,'ir.model.data','search_read',[[('module','=',module),('name','=',name)]],{'fields':['res_id']})
            return values[0]['res_id']
        page.goto(url+'/odoo/action-%d/%d' % (action('erpec_suite','plans_action'),plan_id))
        page.wait_for_selector('.o_form_view');shot('fundador-oferta')
        assert page.get_by_text('Usuarios incluidos',exact=True).count()>0
        page.goto(url+'/odoo/action-%d' % action('erpec_assets','asset_action'))
        page.wait_for_selector('.o_list_view');shot('fundador-activos')
        report['checks']+=['Landing y contratación sin desbordamiento en 1440 y 390 píxeles','Foco de teclado disponible','Desglose anual de 5 usuarios y complemento calculado: USD 760 sintéticos','Alta en cola sin cobro real','Oferta editable por fundador y lista de activos accesibles']
        browser.close()
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n';assert text.encode().decode()==text
    (ROOT/'docs/evidencias/CM28/ui-results.json').write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps({'checks':report['checks'],'axe':report['axe'],'screenshots':len(report['screenshots'])},ensure_ascii=False))

if __name__=='__main__':main()
