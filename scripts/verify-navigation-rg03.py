"""Recorrido de regresión RG03 por menús reales, sin guardar registros de negocio."""
import configparser
import hashlib
import json
from pathlib import Path
from ui_common import playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidencias/RG03'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    with playwright()() as pw:
        browser = pw.chromium.launch(headless=True)
        for name in ['fundador', 'demo']:
            config = configparser.ConfigParser(interpolation=None)
            config.read(ROOT / '.cache/windows' / name / 'odoo.conf', encoding='utf-8')
            opts = config['options']
            url = 'http://127.0.0.1:' + opts['http_port']
            password = json.loads((ROOT / '.cache/windows' / name / 'credentials.json').read_text())['admin']
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='es-EC')
            page = context.new_page()
            page.set_default_timeout(45000)
            page.goto(url + '/web/login')
            assert not page.locator('.o_brand_promotion img[alt="Odoo"]').count()
            page.locator('input[name=login]').fill(name)
            page.locator('input[name=password]').fill(password)
            page.locator('form.oe_login_form button[type=submit]').click()
            page.wait_for_selector('.o_main_navbar')
            def call(model, method, args, kwargs=None):
                data = {'jsonrpc': '2.0', 'params': {'model': model, 'method': method, 'args': args, 'kwargs': kwargs or {}}}
                result = context.request.post(url + '/web/dataset/call_kw/' + model + '/' + method, data=data).json()
                assert 'error' not in result, 'Falló la consulta: ' + model + '.' + method
                return result['result']
            menus = call('ir.ui.menu', 'load_menus', [False])
            by_xmlid = {v['xmlid']: v for v in menus.values() if isinstance(v, dict) and v.get('xmlid')}
            ids = ['tax_policy_menu', 'tax_detail_menu', 'tax_partner_class_menu', 'tax_item_class_menu']
            page.locator('.o_navbar_apps_menu button').click()
            page.get_by_role('menuitem', name='Impuestos', exact=True).click()
            page.wait_for_selector('.o_list_view')
            checked = []
            for item in ids:
                menu = by_xmlid['erpec_workspace.' + item]
                target = page.locator('[data-menu-xmlid="erpec_workspace.' + item + '"]:visible')
                assert target.count(), 'Acceso principal oculto en Más: ' + item
                page.locator('[data-menu-xmlid="erpec_workspace.' + item + '"]:visible').click()
                page.wait_for_selector('.o_list_view')
                page.locator('.o_list_button_add').click()
                page.wait_for_selector('.o_form_view')
                assert not page.locator('.o_error_dialog').count(), item
                shot = OUT / (name + '-' + item + '.png')
                page.screenshot(path=str(shot), full_page=True)
                checked.append({'menu': menu['name'], 'new_form': True, 'screenshot': shot.relative_to(ROOT).as_posix(),
                                'sha256': hashlib.sha256(shot.read_bytes()).hexdigest()})
            page.goto(url + '/odoo/settings')
            page.wait_for_selector('.erpec_product_about')
            assert page.locator('.erpec_product_about').inner_text().startswith('ERP EC')
            assert not page.locator('a[href*="com.odoo.mobile"], img[src*="logo_google_play"], img[src*="logo_apple_store"]').count()
            assert page.locator('link[rel="shortcut icon"]').get_attribute('href') == '/erpec_workspace/static/img/favicon.svg'
            page.locator('.erpec_product_about').scroll_into_view_if_needed()
            shot = OUT / (name + '-settings.png')
            page.screenshot(path=str(shot), full_page=True)
            reports.append({'instance': name, 'database': opts['db_name'], 'url': url, 'menus': checked,
                            'settings_brand': True, 'favicon': True, 'footer_without_provider_promotion': True,
                            'screenshot': shot.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(shot.read_bytes()).hexdigest(),
                            'modules': call('ir.module.module', 'search_read', [[('name', '=', 'erpec_workspace')]], {'fields': ['name', 'installed_version']})})
            assert reports[-1]['modules'][0]['installed_version'] == '18.0.1.3.2'
            context.close()
            print('Navegación y marca verificadas: ' + name, flush=True)
        browser.close()
    text = json.dumps(reports, ensure_ascii=False, indent=2) + '\n'
    assert text.encode().decode() == text
    (OUT / 'runtime.json').write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
