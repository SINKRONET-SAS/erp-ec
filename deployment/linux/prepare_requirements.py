"""Combina los requisitos de Odoo con el lock de ERP EC.

Odoo fija versiones de su distribución de referencia (p. ej. Ubuntu Noble) que
ya no incluyen correcciones de seguridad. El lock de ERP EC manda: cada paquete
presente en ambos usa la versión del lock; el resto conserva lo que pide Odoo.
Solo se emiten los requisitos cuyo marcador aplica al Python en ejecución.

Uso: python prepare_requirements.py <requirements-odoo.txt> <lock> > combinado.txt
"""
import re
import sys

try:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
except ImportError:  # imagen mínima: pip trae su propia copia
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.utils import canonicalize_name


# Paquetes de Odoo sustituidos por su sucesor mantenido (sin correcciones en el original).
REPLACEMENTS = {'pypdf2': 'pypdf'}


def read_lock(path):
    pins = {}
    with open(path, encoding='utf-8') as stream:
        for line in stream:
            line = line.split('#', 1)[0].strip()
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)', line)
            if match:
                pins[canonicalize_name(match.group(1))] = match.group(2)
    return pins


def combine(odoo_path, lock_path):
    pins = read_lock(lock_path)
    emitted, output = set(), []
    with open(odoo_path, encoding='utf-8') as stream:
        for raw in stream:
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue
            requirement = Requirement(line)
            if requirement.marker is not None and not requirement.marker.evaluate():
                continue
            name = canonicalize_name(requirement.name)
            if name in REPLACEMENTS and REPLACEMENTS[name] in pins:
                output_name = REPLACEMENTS[name]
                if output_name not in emitted:
                    emitted.add(output_name)
                    output.append('%s==%s' % (output_name, pins[output_name]))
                continue
            if name in emitted:
                continue
            emitted.add(name)
            extras = '[' + ','.join(sorted(requirement.extras)) + ']' if requirement.extras else ''
            if name in pins:
                output.append('%s%s==%s' % (requirement.name, extras, pins[name]))
            else:
                output.append('%s%s%s' % (requirement.name, extras, requirement.specifier))
    return output


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print('\n'.join(combine(sys.argv[1], sys.argv[2])))
