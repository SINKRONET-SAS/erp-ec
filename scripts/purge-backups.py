"""Purga de respaldos anteriores al cifrado de secretos.

Uso (desde la raiz del repositorio):
    python scripts/purge-backups.py              # simulacion: solo lista
    python scripts/purge-backups.py --ejecutar   # borra respaldos
    python scripts/purge-backups.py --ejecutar --certificado-ajeno   # ademas borra .cache/private/fiscal-pruebas

Se conservan: claves-*, punto-restauracion-*, migracion-install-20260918-*,
cualquier elemento sin fecha en el nombre (p. ej. ERPEC-PRUEBA-*) y todo lo
posterior a 20260919-140000.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.cache' / 'windows' / 'backups'
PRIVATE = ROOT / '.cache' / 'private' / 'fiscal-pruebas'
CORTE = '20260919-140000'
EJECUTAR = '--ejecutar' in sys.argv
CERTIFICADO = '--certificado-ajeno' in sys.argv


def tamano(path):
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())


def se_conserva(path):
    if path.name.startswith(('claves-', 'punto-restauracion-')):
        return True
    if path.name.startswith('migracion-install-20260918-'):
        return True
    marca = re.search(r'(\d{8}-\d{6})', path.name)
    return marca is None or marca.group(1) >= CORTE


assert BASE.is_dir(), BASE
borrar = [p for p in sorted(BASE.iterdir()) if not se_conserva(p)]
total = 0
for p in borrar:
    peso = tamano(p)
    total += peso
    print('%-62s %8.1f MB' % (p.name, peso / 1e6))
print('%d elementos, %.2f GB' % (len(borrar), total / 1e9))

if not EJECUTAR:
    print('SIMULACION: no se borro nada. Agrega --ejecutar para borrar.')
    sys.exit(0)

fallos = []
for p in borrar:
    assert p.resolve().parent == BASE.resolve()
    try:
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    except OSError as error:
        fallos.append((p.name, str(error)))
print('borrados: %d, fallos: %s' % (len(borrar) - len(fallos), fallos or 'ninguno'))

if CERTIFICADO:
    assert PRIVATE.is_dir() and PRIVATE.name == 'fiscal-pruebas'
    shutil.rmtree(PRIVATE)
    print('borrado', PRIVATE)
