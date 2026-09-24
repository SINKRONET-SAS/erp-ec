"""Simulacro de respaldo y restauración aislada (DI25-07.4): respaldo de base + filestore, clave maestra guardada
APARTE, restauración en una base/rol/directorio propios (prefijo reservado ec_restore_drill_), arranque real de
Odoo sobre la copia, comprobaciones de integridad y de descifrado con la clave restaurada, y medición de RTO/RPO.

Nunca toca la instancia de origen salvo lecturas y pg_dump; la copia restaurada arranca sin cron ni correo
(max_cron_threads=0) para que no ejecute ninguna acción automática. Solo elimina los recursos que creó.

Uso: python scripts/backup-restore-drill.py [--instance demo] [--report ruta.json]
"""
import argparse
import configparser
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
PG_BIN = Path('C:/Program Files/PostgreSQL/17/bin')
KEY_FILE = 'erpec_secret.key'
SAMPLE_TABLES = ['res_partner', 'res_users', 'account_move', 'account_move_line', 'account_account', 'ir_attachment',
                 'ir_module_module', 'ir_model_data', 'erpec_fiscal_certificate', 'erpec_fiscal_tax_matrix']


def validate_name(name):
    if not re.fullmatch(r'ec_restore_drill_[a-z0-9]{1,30}', name):
        raise ValueError('Nombre fuera del prefijo reservado ec_restore_drill_.')
    return name


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def tree_summary(directory):
    digest, files, size = hashlib.sha256(), 0, 0
    for path in sorted(p for p in Path(directory).rglob('*') if p.is_file()):
        rel = path.relative_to(directory).as_posix()
        digest.update(('%s:%d;' % (rel, path.stat().st_size)).encode())
        files += 1
        size += path.stat().st_size
    return {'files': files, 'bytes': size, 'tree_sha256': digest.hexdigest()}


def run(args, env=None, **kw):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding='utf-8', errors='replace',
                            env={**os.environ, **(env or {})}, **kw)
    if result.returncode != 0:
        raise RuntimeError('Falló %s: %s' % (Path(str(args[0])).name, (result.stderr or result.stdout)[-400:]))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', default='demo')
    parser.add_argument('--report', default=None)
    args = parser.parse_args()
    source_conf = configparser.ConfigParser(interpolation=None)
    source_conf.read(STATE / args.instance / 'odoo.conf', encoding='utf-8')
    options = source_conf['options']
    db, data_dir = options['db_name'], Path(options['data_dir'])
    cluster = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))
    pg_env = {'PGPASSWORD': cluster['postgres']}
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    backup_dir = STATE / 'backups' / ('drill-%s-%s' % (args.instance, stamp))
    key_dir = STATE / 'backups-keys' / ('drill-%s-%s' % (args.instance, stamp))
    backup_dir.mkdir(parents=True)
    key_dir.mkdir(parents=True)
    report = {'instance': args.instance, 'database': db, 'stamp': stamp}

    def admin():
        connection = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=cluster['postgres'], dbname='postgres')
        connection.autocommit = True
        return connection

    def counts(dbname, user='postgres', password=cluster['postgres']):
        connection = psycopg2.connect(host='127.0.0.1', port=55487, user=user, password=password, dbname=dbname)
        try:
            cursor = connection.cursor()
            result = {}
            for table in SAMPLE_TABLES:
                cursor.execute('SELECT to_regclass(%s)', ['public.' + table])
                if cursor.fetchone()[0]:
                    cursor.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
                    result[table] = cursor.fetchone()[0]
            return result
        finally:
            connection.close()

    # 1. Respaldo (base + filestore) y clave APARTE
    source = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=cluster['postgres'], dbname=db)
    cursor = source.cursor()
    cursor.execute('SELECT now()')
    snapshot_at = cursor.fetchone()[0]
    cursor.execute('SELECT max(write_date) FROM (SELECT max(write_date) write_date FROM account_move UNION ALL SELECT max(write_date) FROM res_partner '
                   'UNION ALL SELECT max(write_date) FROM ir_attachment) t')
    last_write = cursor.fetchone()[0]
    source.close()
    counts_source_before = counts(db)
    t0 = time.monotonic()
    run([PG_BIN / 'pg_dump.exe', '-h', '127.0.0.1', '-p', '55487', '-U', 'postgres', '-Fc', '-f', backup_dir / 'db.dump', db], env=pg_env)
    filestore = data_dir / 'filestore' / db
    shutil.copytree(filestore, backup_dir / 'filestore')
    shutil.copy2(data_dir / KEY_FILE, key_dir / KEY_FILE)
    backup_seconds = time.monotonic() - t0
    manifest = {'db_dump_sha256': sha256_file(backup_dir / 'db.dump'), 'db_dump_bytes': (backup_dir / 'db.dump').stat().st_size,
                'filestore': tree_summary(backup_dir / 'filestore'), 'snapshot_at_utc': str(snapshot_at)}
    (backup_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (key_dir / 'manifest.json').write_text(json.dumps({'key_file_sha256': sha256_file(key_dir / KEY_FILE)}, indent=2), encoding='utf-8')
    master = (key_dir / KEY_FILE).read_text(encoding='ascii').strip()
    plain = run([PG_BIN / 'pg_restore.exe', '-f', '-', backup_dir / 'db.dump']).stdout
    key_in_dump = master in plain
    key_in_filestore = any(master.encode() in p.read_bytes() for p in (backup_dir / 'filestore').rglob('*') if p.is_file() and p.stat().st_size < 5_000_000)
    report['backup'] = {'seconds': round(backup_seconds, 2), 'manifest': manifest, 'key_in_separate_dir': str(key_dir),
                        'key_found_in_dump': key_in_dump, 'key_found_in_filestore_copy': key_in_filestore}

    # 2. Restauración aislada
    name = validate_name('ec_restore_drill_' + secrets.token_hex(4))
    password = secrets.token_urlsafe(20)
    restore_dir = STATE / 'restore-drill' / name
    created_db = created_role = False
    process = None
    connection = admin()
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=%s) OR EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)', [name, name])
        if cursor.fetchone()[0] or restore_dir.exists():
            raise RuntimeError('Recursos del simulacro ya existen; no se reutilizan.')
        t_restore = time.monotonic()
        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(name)), [password])
        created_role = True
        cursor.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0 ENCODING %s OWNER {}').format(sql.Identifier(name), sql.Identifier(name)), ['UTF8'])
        created_db = True
        run([PG_BIN / 'pg_restore.exe', '-h', '127.0.0.1', '-p', '55487', '-U', 'postgres', '-d', name, '--no-owner', '--no-privileges',
             '--role=' + name, backup_dir / 'db.dump'], env=pg_env)
        (restore_dir / 'data' / 'filestore').mkdir(parents=True)
        shutil.copytree(backup_dir / 'filestore', restore_dir / 'data' / 'filestore' / name)
        shutil.copy2(key_dir / KEY_FILE, restore_dir / 'data' / KEY_FILE)
        restore_seconds = time.monotonic() - t_restore
        port = free_port()
        conf = configparser.ConfigParser(interpolation=None)
        conf['options'] = {
            'db_host': '127.0.0.1', 'db_port': '55487', 'db_user': name, 'db_password': password, 'db_name': name, 'dbfilter': '^' + name + '$',
            'addons_path': options['addons_path'], 'list_db': 'False', 'without_demo': 'all', 'workers': '0', 'max_cron_threads': '0',
            'data_dir': str(restore_dir / 'data'), 'http_interface': '127.0.0.1', 'http_port': str(port), 'logfile': str(restore_dir / 'odoo.log')}
        conf_path = restore_dir / 'odoo.conf'
        with open(conf_path, 'w', encoding='utf-8') as handle:
            conf.write(handle)
        t_start = time.monotonic()
        process = subprocess.Popen([str(PYTHON), str(ODOO), '-c', str(conf_path)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   env={**os.environ, 'PYTHONUTF8': '1'})
        ready = False
        while time.monotonic() - t_start < 300:
            try:
                with urllib.request.urlopen('http://127.0.0.1:%d/web/login' % port, timeout=5) as response:
                    ready = response.status == 200
            except Exception:  # noqa: BLE001 - aún arrancando
                ready = False
            if ready:
                break
            time.sleep(2)
        rto_seconds = time.monotonic() - t_restore
        report['restore'] = {'database': name, 'restore_seconds': round(restore_seconds, 2), 'odoo_start_seconds': round(time.monotonic() - t_start, 2),
                             'login_ready': ready, 'rto_seconds_backup_restored_and_serving': round(rto_seconds, 2)}
        if process:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
            process = None
        # 3. Integridad y descifrado con la clave restaurada (y control negativo con otra clave)
        counts_source_after = counts(db)
        counts_restored = counts(name, name, password)
        deltas = {t: counts_source_after[t] - counts_restored.get(t, 0) for t in counts_source_after}
        probe = r'''
import sys, os, json
sys.path.insert(0, r"%s")
import odoo
odoo.tools.config.parse_config(["-c", r"%s"])
registry = odoo.registry("%s")
from odoo.addons.erpec_secrets import secret_store
out = {}
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    cert = env["erpec.fiscal.certificate"].sudo().search([("p12_loaded", "=", True)], limit=1)
    out["cert_present"] = bool(cert)
    if cert:
        material = cert._signing_material()
        out["decrypt_with_restored_key"] = bool(material)
        os.environ["ERPEC_SECRET_KEY"] = "clave-incorrecta-" + "x" * 40
        try:
            cert._signing_material(); out["wrong_key_rejected"] = False
        except Exception as error:
            out["wrong_key_rejected"] = type(error).__name__
    attachments = env["ir.attachment"].sudo().search([("store_fname", "!=", False)], limit=300)
    missing = 0
    for att in attachments:
        if not os.path.exists(att._full_path(att.store_fname)):
            missing += 1
    out["attachments_checked"] = len(attachments); out["attachments_missing_file"] = missing
    cr.rollback()
print("PROBE_JSON=" + json.dumps(out))
''' % ((ROOT / '.cache' / 'odoo-community').as_posix(), conf_path.as_posix(), name)
        result = subprocess.run([str(PYTHON), '-c', probe], cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace',
                                env={**os.environ, 'PYTHONUTF8': '1'})
        line = next((l for l in result.stdout.splitlines() if l.startswith('PROBE_JSON=')), None)
        report['integrity'] = {'row_counts_source': counts_source_after, 'row_counts_restored': counts_restored, 'source_minus_restored': deltas,
                               'probe': json.loads(line[len('PROBE_JSON='):]) if line else {'error': (result.stderr or '')[-400:]}}
        report['rpo'] = {'snapshot_at_utc': str(snapshot_at), 'newest_data_write_before_snapshot_utc': str(last_write),
                         'exposure_if_failure_right_after_backup_seconds': round(backup_seconds, 2),
                         'nota': 'El RPO real depende de la frecuencia de respaldo que se programe; este simulacro mide la ventana propia del respaldo. '
                                 'La edad del último respaldo previo se informa en el cierre de la fase.'}
    finally:
        if process:
            process.kill()
        connection = admin()
        cursor = connection.cursor()
        if created_db:
            cursor.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', [name])
            row = cursor.fetchone()
            if row and row[0] == name:
                cursor.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
        if created_role:
            cursor.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(name)))
        connection.close()
        shutil.rmtree(restore_dir, ignore_errors=True)
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    if args.report:
        Path(args.report).write_text(text + '\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    sys.exit(main())
