"""Reproducciones aisladas del diagnóstico DI25; no conecta bases ni servicios."""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def method(relative, class_name, name, namespace):
    tree = ast.parse((ROOT / relative).read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), relative, 'exec'), namespace)
    return namespace[name]


engine = load('addons/erpec_payroll/engine.py')
params = load('addons/erpec_payroll/parameters_ec2026.py').PARAMS
results = [engine.calculate({'start_date': '2025-01-01', 'wage': wage}, params, 2026, month)
           for month, wage in enumerate([1000] * 11 + [3000], 1)]
annual_base = round(sum(row['base'] - row['personal_iess'] for row in results), 2)
bracket = next(b for b in params['tax_brackets'] if annual_base >= b['from'] and (b['to'] is None or annual_base <= b['to']))
annual_tax = round(bracket['base'] + (annual_base - bracket['from']) * bracket['rate'], 2)
assert annual_tax != results[-1]['annual_tax_caused']

class Queue:
    def search(self, domain, limit):
        self.domain, self.limit = domain, limit
        excluded = domain[0][2]
        eligible = [item for item in self.items if item.state not in excluded]
        return eligible[:limit]

queue = Queue()
processed = []
queue.items = [SimpleNamespace(state='blocked', action_process=lambda: processed.append('blocked')) for _ in range(10)]
queue.items.append(SimpleNamespace(state='signed', action_process=lambda: processed.append('signed')))
cron = method('addons/erpec_fiscal_sri/models.py', 'Emission', '_cron_process',
              {'fields': SimpleNamespace(Datetime=SimpleNamespace(now=lambda: '2026-09-21'))})
cron(queue)
assert processed == ['blocked'] * 10

report = {
    'scope': 'Funciones reales aisladas y motor puro; sin ORM, DB ni SRI. No prueba integración.',
    'rdep_variable_income': {'monthly_wages': [1000] * 11 + [3000], 'accumulated_tax_base': annual_base,
        'tax_on_accumulated_base_using_repository_table': annual_tax,
        'last_month_annual_projection_used_by_rdep': results[-1]['annual_tax_caused']},
    'fiscal_queue': {'actual_method_executed': 'Emission._cron_process', 'domain': queue.domain,
        'limit': queue.limit, 'selected_states': processed, 'older_signed_document_processed': False,
        'assumption': 'Diez bloqueados más recientes sin próxima fecha y una firmada anterior elegible; search simulado.'},
}
print(json.dumps(report, ensure_ascii=False, indent=2))
