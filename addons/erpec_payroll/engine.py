"""Núcleo decimal local basado en las reglas inspeccionadas de SKNOMINA.
Los parámetros pertenecen a una versión revisada; no hay tasas legales implícitas.
"""
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def number(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('El cálculo requiere un número válido.') from None
    if not result.is_finite():
        raise ValueError('El cálculo requiere importes finitos.')
    return result


def money(value):
    return number(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def days_worked(start, year, month):
    begin = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    if start > end:
        return 0
    if start <= begin:
        return 30
    return 31-min(30, start.day)


# Boletín NAC-COM-26-006 (SRI, 06-02-2026): desde la reforma tributaria de 2023
# el tope de gastos personales es único y total (no por categoría), expresado en
# canastas básicas familiares (CBF) de enero según las cargas familiares del
# contribuyente, y se multiplica por el Índice de Precios al Consumidor Especial
# de Galápagos (IPCEG) para quienes tributan en ese régimen. `expense_limit` de
# la política ya representa el tope de 0 cargas (7 canastas: verificado
# 5752.60 = 7 x 821.80 para 2026); esta función lo escala sin pedir la CBF por
# separado. Única fuente de esta regla: la reutilizan tanto el cálculo mensual
# (calculate) como el agregador anual del anexo RDEP (erpec_payroll.annex_rdep).
DEPENDENTS_BASKETS = {0: 7, 1: 9, 2: 11, 3: 14, 4: 17}
DEPENDENTS_BASKETS_MAX = 20  # 5 o más cargas
BASELINE_BASKETS = 7  # cargas=0, la base sobre la que ya está expresado expense_limit
GALAPAGOS_IPCEG_FACTOR = 1.803


def personal_expense_cap(expense_limit, dependents_count=0, galapagos='NO'):
    dependents_count = int(dependents_count or 0)
    if dependents_count < 0:
        raise ValueError('Las cargas familiares no pueden ser negativas.')
    baskets = DEPENDENTS_BASKETS.get(dependents_count, DEPENDENTS_BASKETS_MAX)
    cap = number(expense_limit)/BASELINE_BASKETS*baskets
    return cap*number(GALAPAGOS_IPCEG_FACTOR) if galapagos == 'SI' else cap


def calculate(data, parameters, year, month):
    validate_parameters(parameters)
    start = date.fromisoformat(data['start_date'])
    days = days_worked(start, year, month)
    wage = number(data['wage'])
    if days <= 0 or wage < number(parameters['minimum_salary']) or number(parameters['monthly_hours']) <= 0:
        raise ValueError('Revisa vigencia laboral, salario mínimo y jornada mensual.')
    for key, value in data.items():
        if key in ('bonus', 'commission', 'non_taxable_income', 'advances', 'loans', 'other_deductions', 'personal_expenses', 'hours_50', 'hours_100', 'night_hours') and number(value) < 0:
            raise ValueError('Las novedades y descuentos deben ser no negativos.')
    salary = money(wage*days/30)
    hourly = wage/number(parameters['monthly_hours'])
    overtime = sum(money(hourly*number(data.get(key, 0))*number(parameters[factor])) for key, factor in [('hours_50','overtime_50'), ('hours_100','overtime_100'), ('night_hours','night_rate')])
    base = money(salary+overtime+number(data.get('bonus', 0))+number(data.get('commission', 0)))
    iess = money(base*number(parameters['personal_rate']))
    employer = money(base*number(parameters['employer_rate']))
    employer_other = money(base*number(parameters.get('employer_other_rate',0)))
    annual_base = max(Decimal(0), (base-iess)*12)
    annual_tax = None
    for bracket in parameters['tax_brackets']:
        if annual_base >= number(bracket['from']) and (bracket['to'] is None or annual_base <= number(bracket['to'])):
            annual_tax = number(bracket['base'])+(annual_base-number(bracket['from']))*number(bracket['rate'])
            break
    if annual_tax is None:
        raise ValueError('La tabla de renta no cubre la base anual.')
    # La rebaja reduce el impuesto; no resta gastos personales de la base imponible.
    # El tope escala por cargas familiares y Galápagos (personal_expense_cap);
    # sin cargas y fuera de Galápagos el resultado es expense_limit sin cambios.
    expense_cap = personal_expense_cap(parameters['expense_limit'], data.get('dependents_count', 0), data.get('galapagos', 'NO'))
    rebate = min(number(data.get('personal_expenses', 0)), expense_cap)*number(parameters['rebate_rate'])
    tax_after_rebate = max(Decimal(0), annual_tax-rebate)
    tax = money(tax_after_rebate/12)
    thirteenth = money(base*number(parameters['thirteenth_rate']))
    fourteenth = money(number(parameters['minimum_salary'])*number(parameters['fourteenth_rate'])*days/30)
    vacation = money(base*number(parameters['vacation_rate']))
    end = date(year, month, monthrange(year, month)[1])
    months = (end.year-start.year)*12+end.month-start.month-(end.day < start.day)
    reserve = money(base*number(parameters['reserve_rate'])) if months >= int(parameters['reserve_months']) else Decimal(0)
    monthly13 = thirteenth if data.get('monthly_thirteenth') else Decimal(0)
    monthly14 = fourteenth if data.get('monthly_fourteenth') else Decimal(0)
    reserve_paid = reserve if data.get('reserve_paid') else Decimal(0)
    gross = money(base+number(data.get('non_taxable_income', 0))+monthly13+monthly14+reserve_paid)
    advances, loans, other = [money(data.get(key, 0)) for key in ('advances','loans','other_deductions')]
    deductions = money(iess+tax+advances+loans+other)
    net = money(gross-deductions)
    if net < 0:
        raise ValueError('El neto a recibir no puede ser negativo.')
    accrued13, accrued14, reserve_iess = thirteenth-monthly13, fourteenth-monthly14, reserve-reserve_paid
    cost = money(gross+employer+employer_other+accrued13+accrued14+vacation+reserve_iess)
    # annual_tax y rebate ya estaban calculados; se exponen sin duplicar el cálculo
    # para que el agregador RDEP obtenga la base imponible anual y la rebaja de
    # gastos personales sin recalcularlas por su cuenta (docs/ALCANCE_ATS_RDEP.md).
    return {key: float(value) for key, value in {'days':days, 'salary':salary, 'overtime':overtime, 'base':base, 'gross':gross, 'personal_iess':iess, 'tax':tax, 'advances':advances, 'loans':loans, 'other_deductions':other, 'deductions':deductions, 'net':net, 'employer_iess':employer, 'employer_other':employer_other, 'thirteenth':accrued13, 'fourteenth':accrued14, 'vacation':vacation, 'reserve_iess':reserve_iess, 'cost':cost, 'annual_tax_caused':annual_tax, 'personal_expense_rebate':rebate, 'annual_tax_after_rebate':tax_after_rebate}.items()}


def validate_parameters(parameters):
    required = ['minimum_salary', 'monthly_hours', 'personal_rate', 'employer_rate', 'reserve_rate', 'reserve_months', 'thirteenth_rate', 'fourteenth_rate', 'vacation_rate', 'tax_brackets', 'expense_limit', 'rebate_rate', 'overtime_50', 'overtime_100', 'night_rate']
    if any(key not in parameters for key in required):
        raise ValueError('La versión de parámetros está incompleta.')
    for key, value in parameters.items():
        if key != 'tax_brackets' and number(value) < 0:
            raise ValueError('Los parámetros numéricos deben ser no negativos.')
    for key in ('personal_rate','employer_rate','reserve_rate','thirteenth_rate','fourteenth_rate','vacation_rate','rebate_rate'):
        if number(parameters[key]) > 1:
            raise ValueError('Las tasas proporcionales deben estar entre cero y uno.')
    brackets=parameters['tax_brackets']
    if not brackets or number(brackets[0]['from']) != 0 or brackets[-1]['to'] is not None:
        raise ValueError('La tabla debe cubrir desde cero hasta una última fracción abierta.')
    previous=Decimal(0)
    for index, bracket in enumerate(brackets):
        lower=number(bracket['from'])
        upper=None if bracket['to'] is None else number(bracket['to'])
        if lower != previous or (upper is None and index!=len(brackets)-1) or (upper is not None and upper<=lower) or not 0<=number(bracket['rate'])<=1 or number(bracket['base'])<0:
            raise ValueError('La tabla tiene huecos, solapamientos o valores inválidos.')
        previous=upper
