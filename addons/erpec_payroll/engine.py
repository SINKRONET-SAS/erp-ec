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


def personal_expense_cap(expense_limit, dependents_count=0, galapagos='NO', *, special_expense=False):
    dependents_count = int(dependents_count or 0)
    if dependents_count < 0:
        raise ValueError('Las cargas familiares no pueden ser negativas.')
    if type(special_expense) is not bool:
        raise ValueError('El supuesto especial requiere un indicador booleano explícito.')
    # LRTI, segundo innumerado posterior al art. 10, literal c), sustituido por el art. 7 de la
    # Ley Orgánica de Eficiencia Económica y Generación de Empleo (Registro Oficial, 20-12-2023;
    # verificado en el texto oficial de la ley, aportado por el titular el 22-09-2026): "Para las
    # personas naturales con o a cargo de personas con discapacidad, enfermedades catastróficas,
    # raras y/o huérfanas, el monto de la rebaja por gastos personales será equivalente al 18% del
    # menor valor entre: los gastos personales declarados en el respectivo ejercicio fiscal y, el
    # valor de la canasta familiar básica multiplicado por cien (100)". No es una exención de la
    # base imponible: es el tope de la rebaja del 18 %, igual que el tope general por cargas.
    baskets = 100 if special_expense else DEPENDENTS_BASKETS.get(dependents_count, DEPENDENTS_BASKETS_MAX)
    cap = number(expense_limit)/BASELINE_BASKETS*baskets
    return cap*number(GALAPAGOS_IPCEG_FACTOR) if galapagos == 'SI' else cap


# LRTI art. 9 num. 12 (codificación SRI, última reforma 01-04-2026): mayores de 65 años,
# una fracción básica gravada con tarifa cero; personas con discapacidad calificada y su
# sustituto único, el doble de esa fracción; no son simultáneas y se aplica la más
# beneficiosa. Reglamento LRTI arts. 49 y 50: se deduce del total de ingresos y el
# documento se entrega al empleador hasta el 15 de enero. Reglamento LOD art. 6: solo
# desde 30 % de discapacidad y en proporción al grado. Única implementación: la reutilizan
# la nómina mensual, el anexo RDEP y los ensayos tributarios.
# Edad mínima confirmada además por la Ley Orgánica de las Personas Adultas Mayores, art. 5
# (Registro Oficial 484, 9-V-2019): "se considera persona adulta mayor aquella que ha
# cumplido los 65 años de edad" (documento aportado por el titular, 22-09-2026; DI25-03 D1).
ELDERLY_MIN_AGE = 65
DISABILITY_BENEFIT_SCALE = ((30, 49, 60), (50, 74, 70), (75, 84, 80), (85, 100, 100))
EXEMPTION_DEADLINE = (1, 15)  # mes y día del año fiscal para entregar el documento


def basic_fraction(parameters):
    """Fracción básica gravada con tarifa cero: primer tramo de la tabla vigente."""
    validate_parameters(parameters)
    first = parameters['tax_brackets'][0]
    if number(first['rate']) != 0 or number(first['base']) != 0 or first['to'] is None:
        raise ValueError('El primer tramo de la tabla debe ser la fracción básica con tarifa cero.')
    return number(first['to'])


def disability_benefit_percent(percentage):
    """Porcentaje de aplicación del beneficio según el grado (Reglamento LOD, art. 6)."""
    value = number(percentage)
    if value % 1:
        raise ValueError('El grado de discapacidad debe ser un entero.')
    for low, high, applied in DISABILITY_BENEFIT_SCALE:
        if low <= value <= high:
            return applied
    raise ValueError('El beneficio exige un grado de discapacidad entre 30 % y 100 %.')


def validate_exemption_claim(claim):
    kind = claim.get('kind')
    if kind == 'elderly':
        return
    if kind not in ('disability', 'substitute'):
        raise ValueError('Tipo de exención personal no reconocido.')
    disability_benefit_percent(claim.get('percentage', 0))
    months = number(claim.get('months', 12))
    if months % 1 or not 1 <= months <= 12:
        raise ValueError('Los meses de ejercicio del sustituto deben estar entre 1 y 12.')
    if kind == 'disability' and months != 12:
        raise ValueError('El titular con discapacidad no se prorratea por meses.')


def personal_exemption_amount(parameters, claim):
    """Monto máximo anual de una exención acreditada, antes del tope por base disponible."""
    validate_exemption_claim(claim)
    if claim['kind'] == 'elderly':
        return money(basic_fraction(parameters))
    percent = Decimal(disability_benefit_percent(claim['percentage']))
    return money(basic_fraction(parameters)*2*percent/100*number(claim.get('months', 12))/12)


def apply_personal_exemption(annual_base, parameters, claims=()):
    """Aplica la exención más beneficiosa, nunca la suma, limitada a la base disponible.

    Devuelve (tipo aplicado o 'none', monto aplicado, base imponible resultante)."""
    annual_base = max(Decimal(0), number(annual_base))
    best_kind, best_amount = 'none', Decimal(0)
    for claim in claims:
        amount = personal_exemption_amount(parameters, claim)
        if amount > best_amount:
            best_kind, best_amount = claim['kind'], amount
    applied = min(best_amount, annual_base)
    return (best_kind if applied > 0 else 'none'), money(applied), money(annual_base-applied)


def resolve_exemption_claims(year, birthday, disability_type, disability_percentage, disability_id_type,
                             disability_id, accreditation_year, accreditation_ref, accreditation_date, months=12, regularized=None):
    """Decide qué exenciones están acreditadas para el ejercicio. Función pura.

    Devuelve (reclamos aplicables, incidencias que bloquean el anexo, avisos). El adulto mayor se reconoce por la edad. Sin
    acreditación del mismo año no se aplica la exención por discapacidad: la condición detectada solo genera un
    aviso. Una acreditación incompleta o en un caso no cubierto queda como incidencia y no
    se aplica. La edad se evalúa al cierre del ejercicio; los soportes tardíos de discapacidad requieren regularización."""
    claims, issues, notes = [], [], []
    conditions = []
    # DI25-03 D1 (criterio del titular, 21-09-2026): el adulto mayor se reconoce por la edad que resulta de su fecha de
    # nacimiento, sin acreditación documental; se evalúa el ejercicio en que cumple 65 años.
    if birthday and year-birthday.year >= ELDERLY_MIN_AGE:
        claims.append({'kind': 'elderly'})
    # Códigos del catálogo RDEP vigente (docs/evidencias/Catálogo vigente para el ejercicio fiscal 2024.xlsx,
    # hoja TABLAS): 01 No aplica, 02 Trabajador con discapacidad, 03 Actúa como sustituto,
    # 04 Cónyuge/pareja/hijo con discapacidad bajo su cuidado (derogado a partir del período 2024); 00 solo
    # era válido para períodos anteriores a 2013. Difiere del orden que trae la anotación del XSD 2023.
    if disability_type in ('00', '02', '03', '04'):
        conditions.append(disability_type)
    accredited = bool(accreditation_ref) and accreditation_year == year and bool(accreditation_date)
    if not accredited:
        if conditions:
            notes.append('Discapacidad detectada sin acreditación vigente del año %s: no se aplica exención.' % year)
        return claims, issues, notes
    if accreditation_date > date(year, 12, 31):
        issues.append('La fecha de entrega del documento es posterior al ejercicio del cálculo.')
        return claims, issues, notes
    if not conditions and not claims:
        issues.append('Hay una acreditación de exención sin condición de edad o discapacidad registrada en el empleado.')
        return claims, issues, notes
    for condition in conditions:
        if condition == '00':
            issues.append('El código de discapacidad 00 (catálogo RDEP) solo era válido para períodos anteriores a 2013: no se aplica exención.')
        elif condition == '04' and year >= 2024:
            issues.append('El código de discapacidad 04 (cónyuge, pareja o hijo bajo cuidado) quedó derogado a partir del período 2024 según el catálogo RDEP: no se aplica exención.')
        elif condition == '04':
            issues.append('El código de discapacidad 04 (cónyuge, pareja o hijo bajo cuidado) no otorga la exención por discapacidad al propio trabajador según el catálogo RDEP.')
        elif regularized != 'effective' and (accreditation_date.year, accreditation_date.month, accreditation_date.day) > (year, *EXEMPTION_DEADLINE):
            if regularized == 'pending':
                notes.append('Documento tardío con regularización verificada que aún no surte efecto: la exención no se aplica antes de esa fecha.')
                continue
            issues.append('Documento tardío: requiere regularización documentada y ajuste de retenciones futuras; no se reabren nóminas contabilizadas.')
        else:
            claim = {'kind': 'disability' if condition == '02' else 'substitute', 'percentage': disability_percentage or 0}
            if condition == '03':
                if disability_id_type in (None, False, '', 'N') or not disability_id:
                    issues.append('El sustituto requiere identificar a la persona con discapacidad sustituida.')
                    continue
                claim['months'] = months
            try:
                validate_exemption_claim(claim)
            except ValueError as error:
                issues.append(str(error))
                continue
            claims.append(claim)
    return claims, issues, notes


def resolve_special_expense(year, mode, accreditation_year, accreditation_ref, dependents_count):
    """Decide si el tope de 100 canastas está acreditado para el ejercicio. Función pura.

    Devuelve (aplica, incidencias). Sin marca del empleado rige el tope general. Una marca
    sin documento del mismo año o sin cargas, cuando corresponde a una carga, no se aplica
    y bloquea el anexo. No valida el certificado sanitario ni el parentesco."""
    if mode in (None, False, '', 'none'):
        return False, []
    if mode not in ('holder', 'dependent'):
        return False, ['El supuesto de 100 canastas no es reconocido.']
    issues = []
    if not accreditation_ref or accreditation_year != year:
        issues.append('El supuesto de 100 canastas requiere referencia del documento entregado en el año %s.' % year)
    if mode == 'dependent' and int(dependents_count or 0) < 1:
        issues.append('El supuesto de una carga con condición especial requiere al menos una carga declarada.')
    return not issues, issues


def annual_income_tax(annual_base, personal_expenses, parameters, dependents_count=0, galapagos='NO', *, special_expense=False):
    """Una sola tarifa para proyección mensual y consolidación anual efectiva."""
    validate_parameters(parameters)
    annual_base = max(Decimal(0), number(annual_base))
    expenses = number(personal_expenses)
    if expenses < 0:
        raise ValueError('Los gastos personales no pueden ser negativos.')
    annual_tax = None
    for bracket in parameters['tax_brackets']:
        if annual_base >= number(bracket['from']) and (bracket['to'] is None or annual_base <= number(bracket['to'])):
            annual_tax = number(bracket['base'])+(annual_base-number(bracket['from']))*number(bracket['rate'])
            break
    if annual_tax is None:
        raise ValueError('La tabla de renta no cubre la base anual.')
    cap = personal_expense_cap(parameters['expense_limit'], dependents_count, galapagos, special_expense=special_expense)
    rebate = min(expenses, cap)*number(parameters['rebate_rate'])
    return annual_tax, rebate, max(Decimal(0), annual_tax-rebate)


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
    # D6 (DI25-03): con meses contabilizados del mismo ejercicio se proyecta sobre lo acumulado, se recalcula el
    # impuesto causado y la rebaja, se restan las retenciones ya efectuadas y el saldo se reparte entre los meses
    # que faltan. Sin historial rige la proyección anual de siempre (12 meses, sin retenciones previas).
    prior_months = int(data.get('prior_months', 0) or 0)
    remaining_months = max(1, 12-prior_months) if prior_months else 12
    other_income = number(data.get('other_income', 0))-number(data.get('other_iess', 0))
    annual_base = max(Decimal(0), number(data.get('prior_base', 0))+(base-iess)*remaining_months+other_income)
    _, exemption, annual_base = apply_personal_exemption(annual_base, parameters, data.get('exemptions', ()))
    annual_tax, rebate, tax_after_rebate = annual_income_tax(
        annual_base, data.get('personal_expenses', 0), parameters,
        data.get('dependents_count', 0), data.get('galapagos', 'NO'),
        special_expense=data.get('special_expense', False))
    already_withheld = number(data.get('prior_tax', 0))+number(data.get('other_withheld', 0))
    tax = money(max(Decimal(0), tax_after_rebate-already_withheld)/remaining_months)
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
    # Estas magnitudes son proyecciones mensuales; el RDEP aplica la misma tarifa
    # a los acumulados efectivos, sin copiar una proyección de un mes aislado.
    return {key: float(value) for key, value in {'days':days, 'salary':salary, 'overtime':overtime, 'base':base, 'gross':gross, 'personal_iess':iess, 'tax':tax, 'advances':advances, 'loans':loans, 'other_deductions':other, 'deductions':deductions, 'net':net, 'employer_iess':employer, 'employer_other':employer_other, 'thirteenth':accrued13, 'fourteenth':accrued14, 'vacation':vacation, 'reserve_iess':reserve_iess, 'cost':cost, 'annual_tax_caused':annual_tax, 'personal_expense_rebate':rebate, 'personal_expense_rebate_applied':min(annual_tax,rebate), 'annual_tax_after_rebate':tax_after_rebate, 'personal_exemption':exemption}.items()}


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
