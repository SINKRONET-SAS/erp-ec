"""Instala archivos revisados y valida en una copia aislada antes de tocar el piloto."""
import hashlib
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '.cache/windows'
PYTHON = ROOT / '.venv/Scripts/python.exe'
ODOO = ROOT / '.cache/odoo-community/odoo-bin'
STATE = ROOT / '.cache/windows'
PG = Path(r'C:\Program Files\PostgreSQL\17\bin')

private = json.loads((STATE / 'credentials.json').read_text())
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup = STATE / 'backups' / ('payphone-' + stamp)
backup.mkdir(parents=True)
env = {**os.environ, 'PGPASSWORD': private['a']}
subprocess.run([str(PG/'pg_dump.exe'), '-h', '127.0.0.1', '-p', '55487', '-U', 'erpec_a', '-d', 'erpec_a', '-Fc', '-f', str(backup/'database.dump')], env=env, check=True)
db = 'erpec_pp_test_' + uuid.uuid4().hex[:10]
connection = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=private['postgres'], dbname='postgres')
connection.autocommit = True
with connection.cursor() as cursor:
    cursor.execute(sql.SQL('CREATE DATABASE {} OWNER erpec_a TEMPLATE template0').format(sql.Identifier(db)))
    cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(db)))
connection.close()
subprocess.run([str(PG/'pg_restore.exe'), '-h', '127.0.0.1', '-p', '55487', '-U', 'erpec_a', '-d', db, '--exit-on-error', str(backup/'database.dump')], env=env, check=True)
filestore = STATE / 'a/data/filestore/erpec_a'
if filestore.exists():
    shutil.copytree(filestore, backup/'test-data/filestore'/db)
log = STATE / ('payphone-test-' + stamp + '.log')
args = [str(PYTHON), str(ODOO), '-c', str(STATE/'a/odoo.conf'), '-d', db, '--db-filter', '^' + db + '$',
        '--data-dir', str(backup/'test-data'), '-i', 'erpec_payphone', '-u', 'erpec_suite,erpec_provision,erpec_payphone', '--test-enable', '--test-tags',
        '/erpec_payphone,/erpec_provision,/erpec_suite', '--stop-after-init', '--no-http', '--max-cron-threads', '0', '--http-port', '8199', '--logfile', str(log)]
result = subprocess.run(args)
report = {'database': db, 'backup': str(backup), 'log': str(log), 'exitCode': result.returncode,
          'scope': 'Copia aislada; respuestas PayPhone simuladas; sin cargos externos',
          'moduleHashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'addons/erpec_payphone').rglob('*') if p.is_file() and p.suffix in ('.py','.xml','.csv')}}
(STAGE/'payphone-test-result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
sys.exit(result.returncode)
