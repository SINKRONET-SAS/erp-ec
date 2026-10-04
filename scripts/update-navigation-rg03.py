"""Actualiza Fundador y demo con respaldo, mantenimiento y comparación contable."""
import argparse
import re
import hashlib
import importlib.util
import io
import json
import subprocess
import time
import zipfile
from pathlib import Path
import psycopg2
from psycopg2 import sql
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidencias/RG03'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(opts, password):
    result = {}
    with psycopg2.connect(host=opts['db_host'], port=opts['db_port'], user='postgres', password=password, dbname=opts['db_name']) as conn:
        with conn.cursor() as cursor:
            for table in ['account_move', 'account_move_line', 'erpec_tax_policy', 'erpec_tax_classification', 'erpec_fiscal_point', 'account_journal']:
                cursor.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY id').format(sql.Identifier(table)))
                rows = cursor.fetchall()
                result[table] = {'count': len(rows), 'sha256': hashlib.sha256('\n'.join(row[0] for row in rows).encode()).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='RG03')
    label = parser.parse_args().label
    if not re.fullmatch(r'[A-Z][A-Z0-9-]{1,30}', label):
        raise ValueError('Etiqueta de evidencia inválida.')
    OUT = ROOT / 'docs/evidencias' / label
    OUT.mkdir(parents=True, exist_ok=True)
    updater = load('rg03_updater', 'update-instance.py')
    supervisor = load('rg03_supervisor', 'supervisor-windows.py')
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    baseline = ROOT / '.cache' / (label.lower() + '-baseline-' + stamp)
    archive = subprocess.run(['git', 'archive', '--format=zip', 'HEAD', 'addons'], check=True, capture_output=True).stdout
    with zipfile.ZipFile(io.BytesIO(archive)) as content:
        for item in content.namelist():
            if not (baseline / item).resolve().is_relative_to(baseline.resolve()):
                raise ValueError('Ruta de archivo fuera del respaldo.')
        content.extractall(baseline)
    password = json.loads((updater.STATE / 'credentials.json').read_text())['postgres']
    for name in ['fundador', 'demo']:
        marker = updater.STATE / name / 'maintenance.json'
        if marker.exists():
            raise RuntimeError('Existe otro mantenimiento activo: ' + name)
        marker.write_text(json.dumps({'reason': label + ': navegación y marca'}), encoding='utf-8')
        supervisor.stop(name)
        conf, opts = updater.options(name)
        before = snapshot(opts, password)
        # Ante un fallo se conserva mantenimiento y respaldo para una recuperación explícita.
        result = updater.update(name, False, password, stamp, baseline=baseline / 'addons')
        after = snapshot(opts, password)
        result.update(before=before, after=after, business_data_preserved=before == after)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        assert text.encode().decode() == text
        report = OUT / ('update-' + name + '.json')
        report.write_text(text, encoding='utf-8', newline='\n')
        if before != after or result['desfase'] != 'sin desfase':
            raise RuntimeError('La actualización no superó integridad/esquema: ' + name)
        subprocess.run([str(updater.PYTHON), str(ROOT / 'scripts/restore-cm28-instance.py'), '--report', str(report)], check=True)
        supervisor.start(name)
        marker.unlink()
        print('Instancia actualizada con datos conservados: ' + name, flush=True)


if __name__ == '__main__':
    main()
