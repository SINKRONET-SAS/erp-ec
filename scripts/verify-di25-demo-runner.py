"""Ejecuta la auditoría DI25 de solo lectura y devuelve un código de salida verificable."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=root / '.cache/di25-demo-audit.json')
    args = parser.parse_args()
    source = root / 'scripts/verify-di25-demo.py'
    code = 'exec(compile(open(%r, encoding="utf-8").read(), "verify-di25-demo.py", "exec"))' % str(source)
    command = [str(root / '.venv/Scripts/python.exe'), '-X', 'utf8',
               str(root / '.cache/odoo-community/odoo-bin'), 'shell',
               '-c', str(root / '.cache/windows/demo/odoo.conf'), '--no-http',
               '--logfile', str(root / '.cache/di25-demo-audit.log')]
    try:
        run = subprocess.run(command, input=code, capture_output=True, text=True,
                             encoding='utf-8', cwd=root, timeout=180,
                             env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})
    except subprocess.TimeoutExpired:
        raise RuntimeError('La auditoría excedió 180 segundos; no se considera aprobada.') from None
    if 'DI25_AUDIT_BEGIN' not in run.stdout or 'DI25_AUDIT_END' not in run.stdout:
        raise RuntimeError('No se recibió el informe completo. Revisar .cache/di25-demo-audit.log; no se considera aprobada.')
    payload = run.stdout.split('DI25_AUDIT_BEGIN', 1)[1].split('DI25_AUDIT_END', 1)[0]
    record = json.loads(payload)
    record['processExit'] = run.returncode
    record['passed'] = bool(record.get('passed') and run.returncode == 0 and record.get('database') == 'erpec_demo')
    text = json.dumps(record, ensure_ascii=False, indent=2) + '\n'
    if text.encode('utf-8').decode('utf-8') != text:
        raise RuntimeError('El informe no conserva UTF-8.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps({'passed': record['passed'], 'cases': len(record['cases']),
                      'moduleVersion': record['moduleVersion'], 'problems': record['problems'],
                      'report': str(args.output)}, ensure_ascii=True))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print('Auditoría DI25 no aprobada: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
