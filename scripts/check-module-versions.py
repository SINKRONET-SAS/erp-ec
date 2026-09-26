"""Evita el desfase de esquema de DI26-01: si cambia el esquema declarado de un módulo propio (modelos y campos),
su versión en __manifest__.py debe cambiar también, porque las instancias solo detectan actualizaciones pendientes
por la versión.

La huella se calcula leyendo el código (sin importar Odoo): por cada clase de modelo, su nombre o herencia y cada
campo declarado con su tipo y sus argumentos store/compute/related. El registro vive en
docs/evidencias/module-schema-fingerprints.json.

Uso:
    python scripts/check-module-versions.py --check   # sale con 1 si un esquema cambió sin subir versión
    python scripts/check-module-versions.py --write   # registra huellas y versiones actuales (tras subir versión)
"""
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'docs' / 'evidencias' / 'module-schema-fingerprints.json'
FIELD_TYPES = {'Char', 'Text', 'Html', 'Integer', 'Float', 'Monetary', 'Boolean', 'Date', 'Datetime', 'Binary', 'Image',
               'Selection', 'Many2one', 'One2many', 'Many2many', 'Json', 'Properties', 'Reference', 'Many2oneReference'}


def _literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return ast.dump(node)[:80]


def module_schema(module_dir):
    entries = []
    for path in sorted(module_dir.rglob('*.py')):
        relative = path.relative_to(module_dir).as_posix()
        if relative.startswith(('tests/', 'migrations/')):
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            model = None
            for stmt in cls.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) \
                        and stmt.targets[0].id in ('_name', '_inherit') and model is None:
                    model = str(_literal(stmt.value))
            if model is None:
                continue
            for stmt in cls.body:
                if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
                    continue
                call = stmt.value
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr in FIELD_TYPES:
                    options = {k.arg: _literal(k.value) for k in call.keywords if k.arg in ('store', 'compute', 'related', 'company_dependent')}
                    comodel = _literal(call.args[0]) if call.args and call.func.attr in ('Many2one', 'One2many', 'Many2many') else None
                    entries.append([model, stmt.targets[0].id, call.func.attr, comodel, sorted(options.items(), key=str)])
    entries.sort(key=str)
    return hashlib.sha256(json.dumps(entries, sort_keys=True, default=str).encode('utf-8')).hexdigest()


def current_state():
    state = {}
    for manifest in sorted((ROOT / 'addons').glob('erpec_*/__manifest__.py')):
        version = ast.literal_eval(manifest.read_text(encoding='utf-8')).get('version')
        state[manifest.parent.name] = {'version': version, 'schema': module_schema(manifest.parent)}
    return state


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else '--check'
    state = current_state()
    if mode == '--write':
        text = json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + '\n'
        REGISTRY.write_bytes(text.encode('utf-8'))
        print('Huellas registradas para %d módulos.' % len(state))
        return 0
    recorded = json.loads(REGISTRY.read_text(encoding='utf-8')) if REGISTRY.exists() else {}
    problems = []
    for module, info in state.items():
        before = recorded.get(module)
        if not before:
            problems.append('%s: módulo sin huella registrada; ejecutar --write tras revisar su versión.' % module)
        elif before['schema'] != info['schema'] and before['version'] == info['version']:
            problems.append('%s: cambió el esquema de modelos sin subir la versión (%s).' % (module, info['version']))
        elif before['schema'] != info['schema'] or before['version'] != info['version']:
            problems.append('%s: versión o esquema nuevos sin registrar; ejecutar --write.' % module)
    for problem in problems:
        print('ERROR', problem)
    if problems:
        return 1
    print('Versiones coherentes con el esquema declarado en %d módulos.' % len(state))
    return 0


if __name__ == '__main__':
    sys.exit(main())
