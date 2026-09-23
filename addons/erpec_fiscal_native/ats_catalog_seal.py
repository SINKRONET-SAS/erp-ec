"""Sellado de los archivos oficiales del ATS bundleados en el repositorio (DI25-04.1).

Una huella SHA-256 escrita a mano detecta cualquier cambio silencioso a los archivos oficiales
bundleados (catálogo .xls y esquema at.xsd): para reemplazarlos por una versión más nueva del SRI
hay que descargarla, copiarla sobre el archivo bundleado y volver a sellar la huella aquí, lo que
deja el cambio visible en la revisión. Mismo patrón que erpec_payroll.parameters_seal, adaptado a
archivos binarios completos en vez de una tabla de parámetros en JSON.
"""
import hashlib
from pathlib import Path

try:
    from . import ats_catalog
except ImportError:  # ejecutado como script suelto (scripts/verify-ats-catalog.py), fuera del paquete Odoo
    import ats_catalog

MODULE_ROOT = Path(__file__).resolve().parent

# Huella de cada archivo bundleado. Cambiar el archivo sin resellar esta línea hace fallar
# verify_bundled_files_integrity y la prueba automática correspondiente.
SEAL_SHA256 = {
    'reference/Catalogo_ATS_2026.xls': 'bd3f7834f2cd31187af39cd2f4c685a646d7e49316e92ee493da5f2dd9776e3e',
    'xsd/at.xsd': '4756fe58c139aff5073137ca3b2e66f7a6a55b096861c682b007d5f99b276a9a',
}


def compute_seal(relative_path):
    return hashlib.sha256((MODULE_ROOT / relative_path).read_bytes()).hexdigest()


def verify_bundled_files_integrity():
    """Incidencias si algún archivo bundleado no coincide con su huella sellada."""
    issues = []
    for relative_path, expected in SEAL_SHA256.items():
        absolute = MODULE_ROOT / relative_path
        if not absolute.exists():
            issues.append('Falta el archivo oficial bundleado: %s' % relative_path)
            continue
        if compute_seal(relative_path) != expected:
            issues.append('El archivo oficial bundleado %s fue modificado sin volver a sellar su huella.' % relative_path)
    return issues


def verify_source_metadata():
    """La metadata declarada en ats_catalog.SOURCE debe apuntar a los archivos realmente sellados."""
    issues = []
    if ats_catalog.SOURCE.get('bundled') != 'addons/erpec_fiscal_native/reference/Catalogo_ATS_2026.xls':
        issues.append('ats_catalog.SOURCE["bundled"] no apunta al archivo sellado vigente.')
    if ats_catalog.SOURCE.get('schema') != 'addons/erpec_fiscal_native/xsd/at.xsd':
        issues.append('ats_catalog.SOURCE["schema"] no apunta al esquema sellado vigente.')
    return issues
