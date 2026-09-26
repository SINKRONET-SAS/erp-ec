"""Recorre cada menú con acción de la demo con un usuario QA y registra errores de JavaScript, diálogos de error,
mojibake en pantalla y encabezados visibles en inglés (DI26-A.4). Solo navega; no guarda formularios.

Uso: python scripts/ui-menu-crawl.py [--user qa_admin] [--report ruta.json]
Sale con 1 si hay errores de JavaScript, diálogos de error, mojibake o textos en inglés.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_common import BASE_URL, login, playwright, qa_credentials, qa_users_active  # noqa: E402

MOJIBAKE = re.compile(r'Ã[\x80-\xbf¡-¿]|Â[\xa0-\xbf]|â€|�')
ENGLISH = re.compile(r'\b(the|and|with|without|your|please|invoice|invoices|payment|payments|settings|warning|click|select|create|save|discard|'
                     r'cancel|delete|name|date|amount|status|draft|done|customer|customers|vendor|vendors|supplier|employee|employees|company|'
                     r'account|report|reports|download|upload|file|record|records|missing|required|invalid|unknown|confirm|approve|reject|'
                     r'submit|update|user|users|new|search|reference|description|quantity|price|total amount|due|bank|batch|sequence)\b', re.I)
SPANISH = re.compile(r'[áéíóúñ¿¡]|\b(de|la|el|los|las|del|para|con|sin|por|una|un|es|no|se|que|en|al|y|o|nuevo|buscar|total)\b', re.I)
MENU_JS = """async () => { const r = await fetch('/web/dataset/call_kw/ir.ui.menu/load_menus', {method: 'POST', credentials: 'include',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({jsonrpc: '2.0', method: 'call',
    params: {model: 'ir.ui.menu', method: 'load_menus', args: [false], kwargs: {context: {lang: 'es_EC'}}}})});
    return (await r.json()).result; }"""


def leaves(menus):
    out, stack = [], [('root', [])]
    while stack:
        menu_id, path = stack.pop()
        menu = menus[str(menu_id)]
        new_path = path + ([menu.get('name')] if menu_id != 'root' else [])
        action = menu.get('action') or ''
        if action and not menu.get('children'):
            out.append({'id': menu['id'], 'ruta': ' / '.join(new_path), 'accion': int(action.partition(',')[2])})
        for child in reversed(menu.get('children', [])):
            stack.append((child, new_path))
    return out


def crawl(user):
    password = qa_credentials()[user]
    report = {'usuario': user, 'paginas': []}
    with playwright()() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_context(viewport={'width': 1366, 'height': 850}, locale='es-EC').new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)[:200]))
        page.on('console', lambda m: errors.append('console.error: ' + m.text[:200]) if m.type == 'error' else None)
        login(page, user, password)
        for item in leaves(page.evaluate(MENU_JS)):
            errors.clear()
            page.goto(BASE_URL + '/odoo/action-%s' % item['accion'], wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(2200)
            if page.query_selector('input[name=login]'):
                login(page, user, password)
                page.goto(BASE_URL + '/odoo/action-%s' % item['accion'], wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(2200)
            body = page.inner_text('body')
            dialog = page.query_selector('.o_error_dialog, .o_dialog .modal-header:has-text("Error")')
            visible = page.eval_on_selector_all('th, label, .o_form_label, .breadcrumb-item, .o_last_breadcrumb_item, h1, h2',
                                                'els => els.map(e => (e.innerText || "").trim()).filter(t => t && t.length < 90)')
            item.update({'errores': list(dict.fromkeys(errors))[:4], 'dialogoError': dialog.inner_text()[:200] if dialog else None,
                         'mojibake': sorted({m.group(0) for m in MOJIBAKE.finditer(body)}),
                         'ingles': sorted({t for t in visible if ENGLISH.search(t) and not SPANISH.search(t)})[:12]})
            if dialog:
                page.keyboard.press('Escape')
            report['paginas'].append(item)
        browser.close()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default='qa_admin')
    parser.add_argument('--report')
    args = parser.parse_args()
    with qa_users_active():
        report = crawl(args.user)
    problems = [p for p in report['paginas'] if p['errores'] or p['dialogoError'] or p['mojibake'] or p['ingles']]
    report['resumen'] = {'menus': len(report['paginas']), 'conProblemas': len(problems)}
    text = json.dumps(report, ensure_ascii=False, indent=1) + '\n'
    if args.report:
        Path(args.report).write_bytes(text.encode('utf-8'))
    for p in problems:
        print('PROBLEMA', p['ruta'], p['errores'], p['dialogoError'], p['mojibake'], p['ingles'])
    print('Menús recorridos: %(menus)d; con problemas: %(conProblemas)d' % report['resumen'])
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
