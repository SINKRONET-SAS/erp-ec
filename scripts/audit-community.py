"""Audita manifiestos oficiales sin ejecutar código de módulos."""
import ast
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.cache' / 'odoo-community'
EXPECTED = 'b1fd3a9eee5d575848ac649d2f5103537d8de7a4'
SELECTED = ['base', 'web', 'sale_management', 'purchase', 'stock', 'account', 'l10n_ec', 'l10n_ec_stock', 'l10n_ec_website_sale']

def audit():
    revision = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != EXPECTED:
        raise ValueError('La revisión Community no coincide con el pin aprobado')
    modules = {}
    for directory in [SOURCE / 'addons', SOURCE / 'odoo' / 'addons']:
        for manifest in directory.glob('*/__manifest__.py'):
            data = ast.literal_eval(manifest.read_text(encoding='utf-8-sig'))
            modules[manifest.parent.name] = {'license': data.get('license', 'LGPL-3'), 'depends': data.get('depends', []), 'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
    required = set()
    def visit(name):
        if name not in required:
            if name not in modules:
                raise ValueError('Dependencia no encontrada: ' + name)
            required.add(name)
            for dependency in modules[name]['depends']:
                visit(dependency)
    for name in SELECTED:
        visit(name)
    restricted = {name: modules[name]['license'] for name in required if modules[name]['license'] != 'LGPL-3'}
    if restricted:
        raise ValueError('Licencias requieren revisión: ' + str(restricted))
    report = {'source': 'https://github.com/odoo/odoo', 'revision': revision, 'selected': SELECTED, 'requiredModules': {name: modules[name] for name in sorted(required)}, 'scope': 'Manifiestos y dependencias de módulos; bibliotecas del entorno en informe separado', 'restricted': restricted}
    output = ROOT / 'docs/evidencias/community-audit.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Community verificado:', len(required), 'módulos de licencia LGPL-3')

if __name__ == '__main__':
    audit()
