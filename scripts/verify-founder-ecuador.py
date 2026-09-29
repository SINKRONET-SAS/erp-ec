"""Verifica por RPC y navegador la localización Ecuador del fundador, sin operaciones contables."""
import hashlib
import json
import xmlrpc.client
from pathlib import Path
from ui_common import playwright

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/evidencias/CM28/fundador-ecuador.json'
MODULES = ['l10n_ec', 'l10n_ec_stock', 'erpec_fiscal_native', 'erpec_fiscal_sri',
           'erpec_fiscal_documents', 'erpec_fiscal_withholding_sri', 'erpec_fiscal_guide_sri',
           'erpec_fiscal_ats', 'erpec_withholding_accounting', 'erpec_payroll', 'erpec_assets']
ACTIONS = [('erpec_fiscal_native', 'native_action'), ('erpec_fiscal_sri', 'emission_action'),
           ('erpec_fiscal_sri', 'point_action'), ('erpec_fiscal_ats', 'report_action'),
           ('erpec_withholding_accounting', 'retention_action'), ('erpec_fiscal_guide_sri', 'guide_action'),
           ('erpec_payroll', 'period_action'), ('erpec_payroll', 'rdep_action'), ('erpec_assets', 'asset_action')]


def main():
    url, database = 'http://127.0.0.1:8199', 'erpec_fundador'
    password = json.loads((ROOT / '.cache/windows/fundador/credentials.json').read_text(encoding='utf-8'))['admin']
    uid = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common').authenticate(database, 'fundador', password, {})
    assert uid, 'No se pudo autenticar al fundador.'
    proxy = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')

    def call(model, method, args, kw=None):
        return proxy.execute_kw(database, uid, password, model, method, args, kw or {})

    modules = call('ir.module.module', 'search_read', [[('name', 'in', MODULES)]], {'fields': ['name', 'state']})
    assert len(modules) == len(MODULES) and all(m['state'] == 'installed' for m in modules)
    company = call('res.company', 'read', [[1]], {'fields': ['name', 'country_id', 'currency_id', 'chart_template']})[0]
    assert company['chart_template'] == 'ec' and company['currency_id'][1] == 'USD'
    user = call('res.users', 'read', [[uid]], {'fields': ['lang', 'tz']})[0]
    baseline = json.loads((ROOT / 'docs/evidencias/CM28/fundador-ecuador-restore.json').read_text(encoding='utf-8'))
    counts = {m: call(m, 'search_count', [[]]) for m in ['account.move', 'account.move.line', 'account.account']}
    assert all(n == baseline['integrity']['row_counts_source'][m.replace('.', '_')] for m, n in counts.items())
    views = []
    with playwright()() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='es-EC')
        page = context.new_page()
        page.set_default_timeout(90000)
        page.goto(url + '/web/login')
        page.locator('input[name=login]').fill('fundador')
        page.locator('input[name=password]').fill(password)
        page.locator('form.oe_login_form button[type=submit]').click()
        page.wait_for_selector('.o_main_navbar')
        response = context.request.post(url + '/web/dataset/call_kw/ir.ui.menu/load_menus',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {
                'model': 'ir.ui.menu', 'method': 'load_menus', 'args': [False], 'kwargs': {}}}),
            headers={'Content-Type': 'application/json'})
        payload = response.json()
        assert 'error' not in payload, 'No se pudo obtener la navegación del fundador.'
        visible_ids = {int(k) for k in payload['result'] if str(k).isdigit()}
        for module, name in ACTIONS:
            ref = call('ir.model.data', 'search_read', [[('module', '=', module), ('name', '=', name)]], {'fields': ['res_id']})
            action_id = ref[0]['res_id']
            action = call('ir.actions.act_window', 'read', [[action_id]], {'fields': ['name', 'res_model']})[0]
            menus = call('ir.ui.menu', 'search_read', [[('action', '=', 'ir.actions.act_window,' + str(action_id))]], {'fields': ['name', 'parent_id']})
            assert any(m['id'] in visible_ids for m in menus), 'Acción sin menú visible: ' + action['name']
            call(action['res_model'], 'search_read', [[]], {'fields': ['id'], 'limit': 1})
            page.goto(url + '/odoo/action-' + str(action_id))
            page.wait_for_selector('.o_list_view')
            page.wait_for_selector('.o_list_renderer, .o_view_nocontent')
            assert not page.locator('.o_error_dialog').count(), action['name']
            item = {'action': action['name'], 'model': action['res_model'], 'url': page.url, 'menus': menus, 'visible': True}
            if module == 'erpec_fiscal_ats':
                capture = ROOT / 'docs/evidencias/CM28/ui/fundador-ecuador-ats.png'
                page.screenshot(path=str(capture), full_page=True)
                item.update(screenshot=capture.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(capture.read_bytes()).hexdigest())
            views.append(item)
            print('Pantalla verificada: ' + action['name'], flush=True)
        context.close()
        browser.close()
    report = {'url': url, 'login': 'fundador; credencial existente conservada', 'company': company, 'user': user,
              'modules': modules, 'accounting_counts_preserved': counts, 'views': views,
              'limits': ['No se envían documentos al SRI ni correos.', 'ATS y RDEP son agregadores; disponibilidad no acredita homologación ni presentación tributaria.',
                         'No se modifican tasas, certificado, ambiente SRI ni movimientos contables.']}
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    assert text.encode().decode() == text
    REPORT.write_text(text, encoding='utf-8', newline='\n')
    print('Localización Ecuador: módulos instalados, nueve pantallas accesibles y contabilidad conservada.')


if __name__ == '__main__':
    main()
