"""DI25-04.1: compara el catálogo ATS y el esquema at.xsd bundleados contra la descarga vigente del
portal del SRI, por contenido (SHA-256) y vigencia (fecha listada en la ficha). Herramienta manual
bajo demanda -- no se ejecuta en CI (evita depender de la red del SRI en cada corrida) ni sustituye
el sellado local (addons/erpec_fiscal_native/ats_catalog_seal.py), que sí se verifica siempre.

Uso: .venv/Scripts/python.exe -X utf8 scripts/verify-ats-catalog.py
Requiere red hacia sri.gob.ec / descargas.sri.gob.ec. Registra diferencias efectivas; no sobrescribe
el archivo bundleado ni resella nada automáticamente -- eso queda a criterio de quien lo ejecuta.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'addons' / 'erpec_fiscal_native'))
import ats_catalog  # noqa: E402
import ats_catalog_seal  # noqa: E402

CATALOG_URL = 'https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/e6a826af-b22c-40bb-8752-d711f293b8f9/Catalogo_ATS.xls'
SCHEMA_URL = 'https://descargas.sri.gob.ec/download/anexos/ats/ats.xsd'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main():
    issues = []
    for label, url, bundled_relative in (
        ('Catálogo ATS (.xls)', CATALOG_URL, ats_catalog.SOURCE['bundled']),
        ('Esquema (at.xsd)', SCHEMA_URL, ats_catalog.SOURCE['schema']),
    ):
        try:
            remote = fetch(url)
        except Exception as error:  # noqa: BLE001 -- se reporta cualquier fallo de red, no se oculta
            issues.append('%s: no se pudo descargar (%s). Revisa la conexión o si el portal cambió de URL.' % (label, error))
            continue
        remote_hash = hashlib.sha256(remote).hexdigest()
        bundled_path = ROOT / bundled_relative
        if not bundled_path.exists():
            issues.append('%s: falta el archivo bundleado %s.' % (label, bundled_relative))
            continue
        bundled_hash = hashlib.sha256(bundled_path.read_bytes()).hexdigest()
        if remote_hash == bundled_hash:
            print('%s: sin cambios (huella %s coincide con la bundleada).' % (label, remote_hash[:12]))
        else:
            issues.append(
                '%s: el archivo del portal cambió (huella remota %s, bundleada %s). '
                'Descarga, reemplaza %s y vuelve a sellar en ats_catalog_seal.py antes de confiar en el nuevo contenido.'
                % (label, remote_hash[:12], bundled_hash[:12], bundled_relative))
    seal_issues = ats_catalog_seal.verify_bundled_files_integrity() + ats_catalog_seal.verify_source_metadata()
    if seal_issues:
        issues.append('Sellado local inconsistente antes de comparar con el portal: %s' % '; '.join(seal_issues))
    if issues:
        print('\nDiferencias efectivas encontradas:')
        for issue in issues:
            print(' - %s' % issue)
        sys.exit(1)
    print('\nCatálogo y esquema ATS bundleados coinciden con la descarga vigente del portal del SRI.')


if __name__ == '__main__':
    main()
