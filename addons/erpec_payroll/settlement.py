"""Cálculo decimal del finiquito (liquidación de haberes) por terminación de la relación laboral.

Función pura, sin acceso a la base: la usa el modelo `erpec.payroll.exit` y las pruebas. Contrasta con la
referencia SKNOMINA (RSF26 y RCF26) y la corrige donde ésta pagaba conceptos sin descontar lo ya cubierto:
las vacaciones se calculan sobre los días devengados menos los gozados, y décimos y fondo de reserva se pagan
solo por la parte que el rol no cubrió. No incluye contabilización ni retención de impuesto a la renta.

Bases de tiempo: los décimos y el fondo de reserva usan año comercial de 360 días (meses de 30 días); las
vacaciones y las indemnizaciones usan años de 365 días de servicio.
"""
from calendar import monthrange
from datetime import date
from decimal import Decimal

from .engine import days_worked, money, number

# Causales que permiten calcular el finiquito automáticamente. Las que exigen resolución de autoridad
# (visto bueno), caso fortuito o fallecimiento requieren revisión manual y no se ofrecen aquí.
TERMINATION_CAUSES = {
    'renuncia_voluntaria': {'label': 'Renuncia voluntaria con desahucio', 'legal': 'Código del Trabajo, arts. 184 y 185', 'desahucio': True, 'dismissal': False, 'probation': False},
    'desahucio': {'label': 'Desahucio presentado por el trabajador', 'legal': 'Código del Trabajo, arts. 169.9, 184 y 185', 'desahucio': True, 'dismissal': False, 'probation': False},
    'mutuo_acuerdo': {'label': 'Acuerdo entre las partes', 'legal': 'Código del Trabajo, arts. 169.2, 184 y 185', 'desahucio': True, 'dismissal': False, 'probation': False},
    'despido_intempestivo': {'label': 'Despido intempestivo', 'legal': 'Código del Trabajo, art. 188, sin perjuicio del art. 185', 'desahucio': True, 'dismissal': True, 'probation': False},
    'prueba_empleador': {'label': 'Período de prueba: terminación unilateral del empleador', 'legal': 'Código del Trabajo, art. 15', 'desahucio': False, 'dismissal': False, 'probation': True},
    'prueba_trabajador': {'label': 'Período de prueba: terminación unilateral del trabajador', 'legal': 'Código del Trabajo, art. 15', 'desahucio': False, 'dismissal': False, 'probation': True},
    'conclusion_obra': {'label': 'Conclusión de obra, período o servicio', 'legal': 'Código del Trabajo, art. 169.3', 'desahucio': False, 'dismissal': False, 'probation': False},
}
CAUSE_CHOICES = [(code, item['label']) for code, item in TERMINATION_CAUSES.items()]
MODALITIES = [('rol_primero', 'Pagar primero el rol y luego liquidar'), ('con_finiquito', 'Pagar todo con el finiquito')]
PROBATION_MAX_DAYS = 90
VACATION_DAYS_PER_YEAR = 15
VACATION_EXTRA_AFTER_YEARS = 5
VACATION_EXTRA_MAX = 15
DISMISSAL_MAX_MONTHS = 25
DESAHUCIO_RATE = Decimal('0.25')
CONCEPTS = ('pending_salary', 'thirteenth', 'fourteenth', 'vacation', 'reserve', 'dismissal', 'desahucio')


def is_last_day(day):
    return day.day == monthrange(day.year, day.month)[1]


def days360(start, end):
    """Días comerciales (meses de 30 días) entre dos fechas, ambas incluidas; cero si `end` precede a `start`."""
    if end < start:
        return 0
    first = min(start.day, 30)
    last = 30 if is_last_day(end) else min(end.day, 30)
    return max(0, (end.year-start.year)*360+(end.month-start.month)*30+last-first+1)


def thirteenth_window(end):
    """Período del décimo tercero: del 1 de diciembre al 30 de noviembre."""
    return date(end.year if end.month == 12 else end.year-1, 12, 1)


def fourteenth_window(end, regime):
    """Período del décimo cuarto según el régimen regional del empleado (ver fourteenth_regime.py)."""
    if regime == 'sierra_amazonia':
        return date(end.year if end.month >= 8 else end.year-1, 8, 1)
    if regime == 'costa_insular':
        return date(end.year if end.month >= 3 else end.year-1, 3, 1)
    raise ValueError('Define el régimen del décimo cuarto del empleado antes de calcular el finiquito.')


def add_months(day, months):
    index = day.year*12+day.month-1+months
    year, month = divmod(index, 12)
    return date(year, month+1, min(day.day, monthrange(year, month+1)[1]))


def vacation_entitlement_days(service_days):
    """Días de vacaciones devengados en el servicio: 15 por año y un día adicional por año después del
    quinto, hasta 15 adicionales (Código del Trabajo, art. 69); el último año se prorratea."""
    service_days = int(service_days)
    total = Decimal(0)
    index = 1
    remaining = Decimal(service_days)/Decimal(365)
    while remaining > 0:
        fraction = min(Decimal(1), remaining)
        extra = min(VACATION_EXTRA_MAX, max(0, index-VACATION_EXTRA_AFTER_YEARS))
        total += (VACATION_DAYS_PER_YEAR+extra)*fraction
        remaining -= 1
        index += 1
    return total


def validate_inputs(data):
    cause = TERMINATION_CAUSES.get(data.get('cause'))
    if not cause:
        raise ValueError('La causal de terminación no admite cálculo automático; requiere revisión manual.')
    if data.get('modality') not in dict(MODALITIES):
        raise ValueError('Selecciona si el último mes se paga con el rol o con el finiquito.')
    start, end = data['start_date'], data['end_date']
    if end < start:
        raise ValueError('La fecha de salida no puede ser anterior al ingreso.')
    if number(data['wage']) <= 0:
        raise ValueError('El sueldo mensual debe ser mayor que cero.')
    for key in ('vacation_days_taken', 'other_deductions', 'thirteenth_paid', 'fourteenth_paid', 'reserve_paid', 'reserve_covered'):
        if number(data.get(key, 0)) < 0:
            raise ValueError('Los importes y días informados deben ser no negativos.')
    service_days = (end-start).days+1
    if cause['probation'] and service_days > PROBATION_MAX_DAYS:
        raise ValueError('La causal de período de prueba solo aplica dentro de los primeros %s días de servicio.' % PROBATION_MAX_DAYS)
    return cause, service_days


def settle(data, parameters):
    """Calcula los conceptos del finiquito. `data` trae fechas `date`, `wage`, `cause`, `modality`,
    `fourteenth_regime`, `vacation_days_taken`, `other_deductions` y lo ya pagado por el rol
    (`thirteenth_paid`, `fourteenth_paid`, `reserve_paid`, `reserve_covered`)."""
    cause, service_days = validate_inputs(data)
    wage, start, end = number(data['wage']), data['start_date'], data['end_date']
    daily = wage/30
    # Último mes: con rol primero ya está pagado por el rol proporcional; con finiquito se paga aquí.
    pending_days = days_worked(start, end.year, end.month, end)
    pending_salary = money(daily*pending_days) if data['modality'] == 'con_finiquito' else Decimal(0)
    thirteenth_days = days360(max(start, thirteenth_window(end)), end)
    thirteenth = max(Decimal(0), money(wage*number(parameters['thirteenth_rate'])*thirteenth_days/30)-money(data.get('thirteenth_paid', 0)))
    fourteenth_days = days360(max(start, fourteenth_window(end, data['fourteenth_regime'])), end)
    fourteenth = max(Decimal(0), money(number(parameters['minimum_salary'])*number(parameters['fourteenth_rate'])*fourteenth_days/30)-money(data.get('fourteenth_paid', 0)))
    vacation_entitled = vacation_entitlement_days(service_days)
    vacation_pending = max(Decimal(0), vacation_entitled-number(data.get('vacation_days_taken', 0)))
    vacation = money(daily*vacation_pending)
    first_reserve_day = add_months(start, int(parameters['reserve_months']))
    reserve_days = days360(max(first_reserve_day, date(end.year, 1, 1)), end) if end >= first_reserve_day else 0
    reserve = max(Decimal(0), money(wage*number(parameters['reserve_rate'])*reserve_days/30)-money(data.get('reserve_paid', 0))-money(data.get('reserve_covered', 0)))
    years = -(-service_days//365)
    dismissal = money(wage*(3 if years <= 3 else min(DISMISSAL_MAX_MONTHS, years))) if cause['dismissal'] else Decimal(0)
    desahucio = money(wage*DESAHUCIO_RATE*(service_days//365)) if cause['desahucio'] else Decimal(0)
    amounts = {'pending_salary': pending_salary, 'thirteenth': thirteenth, 'fourteenth': fourteenth, 'vacation': vacation, 'reserve': reserve, 'dismissal': dismissal, 'desahucio': desahucio}
    gross = money(sum(amounts.values()))
    iess = money(pending_salary*number(parameters['personal_rate']))
    other = money(data.get('other_deductions', 0))
    net = money(gross-iess-other)
    if net < 0:
        raise ValueError('Los descuentos superan el total a liquidar; revisa el importe de otros descuentos.')
    detail = {'service_days': service_days, 'pending_days': pending_days, 'thirteenth_days': thirteenth_days, 'fourteenth_days': fourteenth_days,
              'vacation_entitled_days': float(vacation_entitled), 'vacation_pending_days': float(vacation_pending), 'reserve_days': reserve_days,
              'legal_basis': cause['legal'], 'cause_label': cause['label']}
    return {**{key: float(value) for key, value in amounts.items()}, 'gross': float(gross), 'personal_iess': float(iess), 'other_deductions': float(other), 'net': float(net), 'detail': detail}
