"""Utilidades compartidas por los recorridos de UI sobre la demo (DI26-A.4).

Playwright y axe-core no forman parte del repositorio: se buscan en .cache/tools (pw/ y axe.min.js) o en las rutas de
las variables ERPEC_PLAYWRIGHT_PATH y ERPEC_AXE_PATH. Las contraseñas de los usuarios QA viven en
.cache/windows/demo/qa-credentials.json (fuera de git). Los usuarios QA se activan solo durante el recorrido.
"""
import contextlib
import json
import os
import sys
import xmlrpc.client
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.cache' / 'tools'
DEMO = ROOT / '.cache' / 'windows' / 'demo'
BASE_URL = os.environ.get('ERPEC_UI_BASE_URL', 'http://127.0.0.1:8369')
DATABASE = os.environ.get('ERPEC_UI_DATABASE', 'erpec_demo')
AXE = Path(os.environ.get('ERPEC_AXE_PATH', TOOLS / 'axe.min.js'))
QA_ROLES = ['qa_admin', 'qa_basic', 'qa_vendedor', 'qa_comprador', 'qa_bodega', 'qa_operario', 'qa_supervisor', 'qa_nomina', 'qa_contador']


def playwright():
    sys.path.insert(0, str(Path(os.environ.get('ERPEC_PLAYWRIGHT_PATH', TOOLS / 'pw'))))
    from playwright.sync_api import sync_playwright
    return sync_playwright


def qa_credentials():
    return json.loads((DEMO / 'qa-credentials.json').read_text(encoding='utf-8'))


@contextlib.contextmanager
def qa_users_active():
    """Activa los usuarios QA durante el bloque y los devuelve a su estado anterior al salir."""
    password = json.loads((DEMO / 'credentials.json').read_text(encoding='utf-8'))['admin']
    uid = xmlrpc.client.ServerProxy(BASE_URL + '/xmlrpc/2/common').authenticate(DATABASE, 'demo', password, {})
    if not uid:
        raise RuntimeError('No se pudo autenticar el administrador de la demo.')
    models = xmlrpc.client.ServerProxy(BASE_URL + '/xmlrpc/2/object')
    inactive = models.execute_kw(DATABASE, uid, password, 'res.users', 'search',
                                 [[('login', 'in', QA_ROLES), ('active', '=', False)]], {'context': {'active_test': False}})
    if inactive:
        models.execute_kw(DATABASE, uid, password, 'res.users', 'write', [inactive, {'active': True}])
    try:
        yield
    finally:
        if inactive:
            models.execute_kw(DATABASE, uid, password, 'res.users', 'write', [inactive, {'active': False}])


def login(page, user, password):
    page.goto(BASE_URL + '/web/login')
    page.fill('input[name=login]', user)
    page.fill('input[name=password]', password)
    page.press('input[name=password]', 'Enter')
    page.wait_for_selector('.o_main_navbar', timeout=120000)
    page.wait_for_timeout(1500)


def run_axe(page):
    page.add_script_tag(path=str(AXE))
    return page.evaluate("""async () => { const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}});
        return {violations: r.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.length})), passes: r.passes.length}; }""")
