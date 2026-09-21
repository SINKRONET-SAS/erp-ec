"""Sellado de los parámetros tributarios oficiales por ejercicio (DI25-03, requisito 1 del pronunciamiento).

Los valores oficiales del impuesto a la renta (tabla progresiva, canasta familiar, topes por cargas,
rebaja, IPCEG y escala de discapacidad) viven aquí con su fuente y su fecha de vigencia. Una huella
SHA-256 escrita a mano detecta cualquier cambio silencioso: para modificar un valor hay que cambiarlo
y volver a sellar la huella, lo que deja el cambio visible en la revisión. Ningún cálculo de un
ejercicio sellado puede apoyarse en una tabla distinta (prohibido reutilizar valores de otro año).
"""
import hashlib
import json
from datetime import date

# Ejercicio -> valores oficiales. La canasta es la de enero del ejercicio.
SEALED_TAX_PARAMETERS = {
    2026: {
        'effective_from': '2026-01-01',
        'sources': [
            'SRI, tabla del Impuesto a la Renta de personas naturales 2026, Resolución NAC-DGERCGC25-00000043 (RO 194, 30-12-2025)',
            'SRI, Boletín NAC-COM-26-006 y comunicado de 08-09-2026 (CFB 2026 USD 821,80; IPCEG 1,803)',
            'LRTI art. 9 num. 12 y art. innumerado posterior al 10; RLRTI arts. 49-50 y 104',
        ],
        'tax_brackets': [
            {'from': 0, 'to': 12208, 'base': 0, 'rate': 0},
            {'from': 12208, 'to': 15549, 'base': 0, 'rate': 0.05},
            {'from': 15549, 'to': 20188, 'base': 167, 'rate': 0.1},
            {'from': 20188, 'to': 26700, 'base': 631, 'rate': 0.12},
            {'from': 26700, 'to': 35136, 'base': 1412, 'rate': 0.15},
            {'from': 35136, 'to': 46575, 'base': 2678, 'rate': 0.2},
            {'from': 46575, 'to': 62005, 'base': 4965, 'rate': 0.25},
            {'from': 62005, 'to': 82679, 'base': 8823, 'rate': 0.3},
            {'from': 82679, 'to': 109956, 'base': 15025, 'rate': 0.35},
            {'from': 109956, 'to': None, 'base': 24572, 'rate': 0.37},
        ],
        'basket': 821.8,
        'expense_limit': 5752.6,
        'rebate_rate': 0.18,
        'baskets_by_dependents': {'0': 7, '1': 9, '2': 11, '3': 14, '4': 17, '5': 20},
        'special_expense_baskets': 100,
        'ipceg_factor': 1.803,
        'disability_scale': [[30, 49, 60], [50, 74, 70], [75, 84, 80], [85, 100, 100]],
        'elderly_min_age': 65,
        'exemption_deadline': [1, 15],
    },
}

# Huella de cada ejercicio sellado. Cambiar un valor de SEALED_TAX_PARAMETERS sin resellar esta línea
# hace fallar verify_seal_integrity y la prueba automática correspondiente.
SEAL_SHA256 = {
    2026: 'c7322405a41ea40ab20a5f6ea522a85413574e604ee35ed11b2e729cf08815ef',
}

TOLERANCE_BRACKET_BASE = 1.0  # las bases publicadas por el SRI están redondeadas al dólar


def canonical(year):
    return json.dumps(SEALED_TAX_PARAMETERS[year], sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def compute_seal(year):
    return hashlib.sha256(canonical(year).encode('utf-8')).hexdigest()


def is_sealed(year):
    return year in SEALED_TAX_PARAMETERS


def verify_seal_integrity(year):
    """Incidencias si los valores sellados no coinciden con su huella."""
    if not is_sealed(year):
        return []
    if compute_seal(year) != SEAL_SHA256.get(year):
        return ['Los parámetros oficiales sellados de %s fueron modificados sin volver a sellar su huella.' % year]
    return []


def verify_bracket_coherence(brackets, tolerance=TOLERANCE_BRACKET_BASE):
    """La base de cada tramo debe ser la base anterior más el ancho del tramo por su tasa (±tolerancia)."""
    issues = []
    for previous, current in zip(brackets, brackets[1:]):
        expected = previous['base'] + (previous['to'] - previous['from']) * previous['rate']
        if abs(current['base'] - expected) > tolerance:
            issues.append('Tabla progresiva incoherente en el tramo desde %s: base %s, esperada %.2f.' % (current['from'], current['base'], expected))
    return issues


def _same_brackets(actual, expected):
    if len(actual) != len(expected):
        return False
    for left, right in zip(actual, expected):
        if (float(left['from']), None if left['to'] is None else float(left['to']), float(left['base']), float(left['rate'])) != (
                float(right['from']), None if right['to'] is None else float(right['to']), float(right['base']), float(right['rate'])):
            return False
    return True


def verify_policy_parameters(year, parameters):
    """Incidencias de una política frente a la referencia sellada del ejercicio. Sin sello, no valida nada."""
    if not is_sealed(year):
        return []
    sealed = SEALED_TAX_PARAMETERS[year]
    issues = verify_seal_integrity(year)
    if not _same_brackets(parameters.get('tax_brackets', []), sealed['tax_brackets']):
        issues.append('La tabla progresiva de la política no coincide con la oficial de %s.' % year)
    for key in ('expense_limit', 'rebate_rate'):
        if abs(float(parameters.get(key, -1)) - sealed[key]) > 1e-9:
            issues.append('%s de la política (%s) no coincide con el valor oficial de %s (%s).' % (key, parameters.get(key), year, sealed[key]))
    return issues


def verify_engine_constants(year, engine):
    """Contrasta las constantes del motor con la referencia sellada (cargas, canastas, IPCEG, escala, edad, plazo)."""
    if not is_sealed(year):
        return []
    sealed = SEALED_TAX_PARAMETERS[year]
    issues = []
    baskets = dict(engine.DEPENDENTS_BASKETS)
    baskets[5] = engine.DEPENDENTS_BASKETS_MAX
    if {str(key): value for key, value in baskets.items()} != sealed['baskets_by_dependents']:
        issues.append('Las canastas por cargas del motor no coinciden con las oficiales.')
    if abs(engine.GALAPAGOS_IPCEG_FACTOR - sealed['ipceg_factor']) > 1e-12:
        issues.append('El IPCEG del motor no coincide con el oficial.')
    if [list(item) for item in engine.DISABILITY_BENEFIT_SCALE] != sealed['disability_scale']:
        issues.append('La escala de discapacidad del motor no coincide con la oficial.')
    if engine.ELDERLY_MIN_AGE != sealed['elderly_min_age'] or list(engine.EXEMPTION_DEADLINE) != sealed['exemption_deadline']:
        issues.append('La edad o el plazo de entrega del motor no coinciden con los oficiales.')
    if abs(sealed['basket'] * sealed['baskets_by_dependents']['0'] - sealed['expense_limit']) > 0.01:
        issues.append('El límite sin cargas sellado no equivale a 7 canastas.')
    return issues


def year_notice(year):
    """Aviso, no bloqueo, para un ejercicio cercano sin referencia sellada (los ejercicios sintéticos lejanos no avisan)."""
    if is_sealed(year) or not min(SEALED_TAX_PARAMETERS) <= year <= date.today().year + 1:
        return []
    return ['No existe referencia oficial sellada para el ejercicio %s: no reutilices valores de otro año; carga y sella la referencia oficial.' % year]
