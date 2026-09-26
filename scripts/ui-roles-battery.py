"""Batería de UI por rol en la demo (DI26-A.4, origen DI25-06): 9 roles, anchos 360/768/1280 y 640 px a DPR 2
(zoom 200 %), desborde, errores de JavaScript, axe-core WCAG 2.x A/AA, foco visible con teclado y áreas por rol.

Uso: python scripts/ui-roles-battery.py [--report ruta.json] [--baseline docs/evidencias/DI25/DI25-06/recorrido-roles-9.json]
Sale con 1 si hay desbordes, errores de JavaScript, violaciones axe, foco sin indicador o áreas distintas a la línea base.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_common import BASE_URL, QA_ROLES, login, playwright, qa_credentials, qa_users_active, run_axe  # noqa: E402

VIEWS = [('360', 360, 740, 1), ('768', 768, 900, 1), ('1280', 1280, 800, 1), ('zoom200', 640, 400, 2)]


def keyboard(page, stops=25):
    page.evaluate('() => document.activeElement && document.activeElement.blur()')
    found, missing = 0, []
    for _ in range(stops):
        page.keyboard.press('Tab')
        info = page.evaluate("""() => { const e = document.activeElement; if (!e || e === document.body) return null; const c = getComputedStyle(e);
            return {label: (e.getAttribute('aria-label') || e.innerText || '').trim().slice(0, 30),
                    focus: (c.outlineStyle !== 'none' && parseFloat(c.outlineWidth) > 0) || c.boxShadow !== 'none'}; }""")
        if info:
            found += 1
            if not info['focus']:
                missing.append(info)
    return {'paradas': found, 'sin_indicador': missing[:4]}


def battery():
    creds = qa_credentials()
    report = {'entorno': 'Chrome (Playwright), %s' % BASE_URL, 'roles': {}}
    with playwright()() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        for role in QA_ROLES:
            report['roles'][role] = {}
            for name, width, height, dpr in VIEWS:
                context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=dpr, locale='es-EC')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)[:100]))
                login(page, role, creds[role])
                page.goto(BASE_URL + '/odoo')
                page.wait_for_timeout(2500)
                result = {'overflow': page.evaluate('() => document.documentElement.scrollWidth > window.innerWidth + 1'), 'errores_js': errors[:2]}
                if name in ('1280', 'zoom200'):
                    axe = run_axe(page)
                    result['axe'] = {'reglas_ok': axe['passes'], 'violaciones': [(v['id'], v['impact'], v['nodes']) for v in axe['violations']]}
                if name == '1280':
                    result['teclado'] = keyboard(page)
                    page.click('.o_main_navbar button:has-text("Áreas")')
                    page.wait_for_timeout(600)
                    result['areas'] = [t.strip() for t in page.eval_on_selector_all('.dropdown-menu .dropdown-item', 'els => els.map(e => e.innerText)') if t.strip()]
                    page.keyboard.press('Escape')
                report['roles'][role][name] = result
                context.close()
        browser.close()
    return report


def problems(report, baseline):
    found = []
    for role, views in report['roles'].items():
        for name, result in views.items():
            if result['overflow'] or result['errores_js'] or (result.get('axe') or {}).get('violaciones') \
                    or (result.get('teclado') or {}).get('sin_indicador'):
                found.append('%s %s: %s' % (role, name, json.dumps(result, ensure_ascii=False)[:200]))
            if baseline and name == '1280':
                before = baseline.get('roles', {}).get(role, {}).get('1280', {}).get('areas')
                if before is not None and sorted(before) != sorted(result.get('areas', [])):
                    found.append('%s: áreas distintas a la línea base (%s -> %s)' % (role, before, result.get('areas')))
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report')
    parser.add_argument('--baseline')
    args = parser.parse_args()
    with qa_users_active():
        report = battery()
    baseline = json.loads(Path(args.baseline).read_text(encoding='utf-8')) if args.baseline else None
    found = problems(report, baseline)
    report['problemas'] = found
    if args.report:
        Path(args.report).write_bytes((json.dumps(report, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    for item in found:
        print('PROBLEMA', item)
    print('Roles: %d; problemas: %d' % (len(report['roles']), len(found)))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
