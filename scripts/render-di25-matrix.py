"""Genera (o verifica) la matriz de pendientes DI25-03 del documento a partir de la fuente única del módulo.

Uso: python scripts/render-di25-matrix.py           # imprime la tabla
     python scripts/render-di25-matrix.py --write   # actualiza docs/DI25-03_MATRIZ_ACEPTACION.md
     python scripts/render-di25-matrix.py --check   # sale con 1 si el documento no coincide con el módulo
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'addons/erpec_payroll/acceptance_matrix_data.xml'
DOCUMENT = ROOT / 'docs/DI25-03_MATRIZ_ACEPTACION.md'
BEGIN, END = '<!-- MATRIZ-PENDIENTES:INICIO -->', '<!-- MATRIZ-PENDIENTES:FIN -->'
STATES = {'automated': 'Control automático', 'partial': 'Control parcial', 'blocked': 'Bloqueo automático', 'external': 'Depende de un tercero'}
DECISIONS = {'corregir': 'Corregir', 'aceptar': 'Aceptar', 'condicionar': 'Condicionar', 'rechazar': 'Rechazar', 'parcial': 'Parcial', 'bloquear': 'Bloquear', 'mixto': 'Mixto'}


def rows():
    result = []
    for record in ET.parse(SOURCE).getroot().iter('record'):
        values = {field.get('name'): (field.text or '').strip() for field in record.iter('field')}
        result.append(values)
    return sorted(result, key=lambda item: int(item['sequence']))


def cell(text):
    return text.replace('|', '/').replace('\n', ' ')


def render():
    data = rows()
    counts = {state: sum(1 for row in data if row['control_state'] == state) for state in STATES}
    lines = ['## Matriz de pendientes vigente (módulo 18.0.1.14.8)', '',
             'Fuente única: `addons/erpec_payroll/acceptance_matrix_data.xml`, visible en **Nómina → Matriz de aceptación DI25-03**. '
             'Este bloque se genera con `scripts/render-di25-matrix.py` y una verificación automática impide que se desactualice. '
             'Una prueba exige que cada fila con control cite pruebas que existan. **Nada aquí es una homologación**: la aceptación externa sigue pendiente.', '',
             'Resumen: ' + ', '.join('%s %d' % (STATES[state].lower(), counts[state]) for state in STATES) + '.', '',
             '| Código | Decisión o caso | Decisión del responsable | Estado | Control que existe hoy | Lo que sigue pendiente | Quién lo destraba |', '|---|---|---|---|---|---|---|']
    for row in data:
        lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (row['code'], cell(row['item']), DECISIONS[row['expert_decision']], STATES[row['control_state']],
                                                              cell(row['control']), cell(row['pending']), cell(row['owner'])))
    return '\n'.join(lines) + '\n'


def inject(document, block):
    if BEGIN in document and END in document:
        head, rest = document.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        return head + BEGIN + '\n' + block + END + tail
    return BEGIN + '\n' + block + END + '\n\n---\n\n' + document


def main():
    block = render()
    if '--write' in sys.argv or '--check' in sys.argv:
        current = DOCUMENT.read_text(encoding='utf-8')
        updated = inject(current, block)
        if '--check' in sys.argv:
            if updated != current:
                print('La matriz del documento no coincide con acceptance_matrix_data.xml; ejecuta --write.', file=sys.stderr)
                return 1
            print('Matriz del documento al día (%d filas).' % len(rows()))
            return 0
        DOCUMENT.write_text(updated, encoding='utf-8', newline='\n')
        print('Documento actualizado (%d filas).' % len(rows()))
        return 0
    sys.stdout.reconfigure(encoding='utf-8')
    print(block)
    return 0


if __name__ == '__main__':
    sys.exit(main())
