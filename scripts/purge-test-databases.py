"""Elimina bases y roles de PostgreSQL residuales de pruebas y ensayos.

Uso (desde la raiz del repositorio):
    python scripts/purge-test-databases.py              # simulacion: solo lista
    python scripts/purge-test-databases.py --ejecutar   # borra bases, roles y carpetas de ensayo

Nunca toca: erpec_fundador, erpec_demo, erpec_a, erpec_b, postgres ni bases con conexiones activas.
Con --ejecutar tambien borra .cache/windows/instances/* y .cache/windows/recoveries/*
(datos de los ensayos multi-inquilino y de recuperacion, cuyas bases se eliminan).
"""
import json
import re
import shutil
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
EJECUTAR = '--ejecutar' in sys.argv
PROTEGIDAS = {'erpec_fundador', 'erpec_demo', 'erpec_a', 'erpec_b', 'postgres'}
BASES = re.compile(r'(ec_(fiscal_connector|fiscal_documents|manufacturing|operational|operations|recovery|withholding_accounting|deps_upgraded|diag_full|diag_fix|fiscal_sri_full)_?[0-9a-f_]*|ec_[a-z_]+_test|erp_[0-9a-f]{32}|restore_[0-9a-f]{12})$')
ROLES = re.compile(r'(ec_operational_[0-9a-f]{10}|ec_recovery_[0-9a-f]{10}|erp_[0-9a-f]{32}|erp_tenants|ec_[a-z_]+_test)$')

cluster = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))
conexion = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=cluster['postgres'], dbname='postgres')
conexion.autocommit = True
cursor = conexion.cursor()

cursor.execute('select datname, pg_database_size(datname) from pg_database where not datistemplate order by 1')
borrar, omitir = [], []
for nombre, peso in cursor.fetchall():
    if nombre in PROTEGIDAS or not BASES.fullmatch(nombre):
        omitir.append(nombre)
        continue
    cursor.execute('select count(*) from pg_stat_activity where datname=%s', [nombre])
    if cursor.fetchone()[0]:
        omitir.append(nombre + ' (con conexiones)')
        continue
    borrar.append((nombre, peso))
print('BASES A BORRAR (%d, %.2f GB):' % (len(borrar), sum(p for _, p in borrar) / 1e9))
for nombre, peso in borrar:
    print('  %-45s %7.1f MB' % (nombre, peso / 1e6))
print('SE CONSERVAN:', omitir)

cursor.execute("select rolname from pg_roles where rolname not like 'pg_%' order by 1")
roles = [r[0] for r in cursor.fetchall() if r[0] not in PROTEGIDAS and ROLES.fullmatch(r[0])]
print('ROLES A BORRAR (%d):' % len(roles), roles)

carpetas = [p for base in ('instances', 'recoveries') if (STATE / base).is_dir() for p in sorted((STATE / base).iterdir())]
print('CARPETAS DE ENSAYO A BORRAR (%d):' % len(carpetas), [str(p.relative_to(STATE)) for p in carpetas])

if not EJECUTAR:
    print('SIMULACION: no se borro nada. Agrega --ejecutar para borrar.')
    sys.exit(0)

for nombre, _ in borrar:
    cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(nombre)))
for rol in roles:
    try:
        cursor.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(rol)))
        cursor.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(rol)))
    except psycopg2.Error as error:
        print('rol no borrado', rol, str(error).strip()[:100])
for carpeta in carpetas:
    assert carpeta.resolve().parent.parent == STATE.resolve()
    shutil.rmtree(carpeta, ignore_errors=True)
cursor.execute('select datname from pg_database where not datistemplate order by 1')
print('BASES RESTANTES:', [r[0] for r in cursor.fetchall()])
