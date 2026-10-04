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


def days_worked(start, year, month, end=None):
    """Días del período sobre base 30. Con `end` (fecha de salida) el rol se prorratea hasta ese día;
    una salida en el último día del mes paga el mes completo (también en febrero)."""
    begin = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    if start > last or (end is not None and end < begin):
        return 0
    first_day = 1 if start <= begin else min(30, start.day)
    last_day = 30 if end is None or end >= last else min(30, end.day)
    return max(0, last_day-first_day+1)


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


def gross_up_assumed_tax(net_target, base_annual_base, personal_expenses, parameters, dependents_count=0, galapagos='NO', *, special_expense=False):
    """Caso 11 (DI25-03): impuesto asumido por el empleador en un "contrato de ingreso neto en
    nómina" (casillero 381 F107). La LRTI no fija una tarifa única de "gross-up"; se resuelve por
    bisección contra la misma tabla progresiva (annual_income_tax) ya aplicada al resto de la
    nómina, tratándola como caja negra: dado el neto adicional garantizado (net_target) y la base
    anual gravable del resto de la nómina (base_annual_base, ya después de la rebaja de gastos
    personales), busca el impuesto que el empleador debe asumir para que ese neto llegue íntegro
    al trabajador, sea cual sea el tramo de la tabla en el que caiga."""
    net_target = number(net_target)
    if net_target < 0:
        raise ValueError('El ingreso neto garantizado no puede ser negativo.')
    if net_target == 0:
        return Decimal(0)
    base_annual_base = max(Decimal(0), number(base_annual_base))
    _, _, base_tax = annual_income_tax(base_annual_base, personal_expenses, parameters, dependents_count, galapagos, special_expense=special_expense)
    lo, hi = net_target, net_target*Decimal(3)
    for _ in range(50):
        mid = (lo+hi)/2
        _, _, mid_tax = annual_income_tax(base_annual_base+mid, personal_expenses, parameters, dependents_count, galapagos, special_expense=special_expense)
        net = mid-(mid_tax-base_tax)
        if net < net_target:
            lo = mid
        else:
            hi = mid
    return money(hi-net_target)


# Licencia por enfermedad (LE26 de la referencia SKNOMINA; Oficio PGE 10097 de 2025, Ley de Seguridad Social
# arts. 106 y 107, Código del Trabajo arts. 42.19 y 54). La antigüedad no acredita el derecho al subsidio del
# IESS: la calificación la registra RR. HH. con su respaldo y, sin ella, el cálculo se rechaza (nunca se
# descuenta el 100 % por falta de evidencia). Con derecho: días 1 a 3 del episodio al 100 % a cargo del empleador
# (la numeración continúa entre meses con los días previos certificados) y desde el día 4 el subsidio lo paga
# el IESS, con complemento patronal opcional documentado. Sin derecho: el empleador paga el 50 % hasta 60 días
# por año; el subsidio estimado del IESS es informativo y nunca se suma al neto del empleador.
SICK_EMPLOYER_DAYS = 3
SICK_ANNUAL_EMPLOYER_DAYS = 60


def sick_leave_pay(data, wage, sick_days):
    """Devuelve (pago patronal, días pagados al 50 %, subsidio IESS estimado informativo)."""
    if sick_days <= 0:
        return Decimal(0), Decimal(0), Decimal(0)
    eligibility = data.get('sick_eligibility')
    daily = wage/30
    if eligibility == 'eligible':
        full = max(Decimal(0), min(sick_days, SICK_EMPLOYER_DAYS-number(data.get('sick_prior_days', 0))))
        subsidized = sick_days-full
        complement = number(data.get('sick_complement_pct', 0))
        if not 0 <= complement <= 100:
            raise ValueError('El complemento patronal debe estar entre 0 y 100 %.')
        pay = money(daily*full+daily*subsidized*complement/100)
        rate = number(data.get('sick_iess_rate', 0) or 0)
        base = number(data.get('sick_iess_base', 0))
        estimate = money(base/30*rate/100*subsidized) if rate and base else Decimal(0)
        return pay, Decimal(0), estimate
    if eligibility == 'ineligible':
        if number(data.get('sick_annual_prior_days', 0))+sick_days > SICK_ANNUAL_EMPLOYER_DAYS:
            raise ValueError('Se alcanzó el límite anual de %s días a cargo del empleador sin derecho al subsidio del IESS: registra la resolución de RR. HH. y paga la parte restante como novedad documentada.' % SICK_ANNUAL_EMPLOYER_DAYS)
        return money(daily*sick_days/2), sick_days, Decimal(0)
    raise ValueError('La licencia por enfermedad está pendiente de revisión: registra la calificación del derecho al subsidio del IESS con su respaldo, el certificado y la continuidad del episodio.')


def calculate(data, parameters, year, month):
    validate_parameters(parameters)
    start = date.fromisoformat(data['start_date'])
    end_date = date.fromisoformat(data['end_date']) if data.get('end_date') else None
    if end_date is not None and end_date < start:
        raise ValueError('La fecha de salida no puede ser anterior al ingreso.')
    days = days_worked(start, year, month, end_date)
    wage = number(data['wage'])
    if days <= 0 or wage < number(parameters['minimum_salary']) or number(parameters['monthly_hours']) <= 0:
        raise ValueError('Revisa vigencia laboral, salario mínimo y jornada mensual.')
    # Caso 11 (DI25-03, criterio del titular, 23-09-2026): la Reforma a la LOREG unificó el
    # incremento salarial de Galápagos (antes 75%/100% fijo, "antitécnico") con el mismo índice
    # técnico que ya usa el SRI para el tope de gastos personales (IPCEG, calculado con el INEC).
    # `wage` se declara como el salario de referencia continental; para un empleado elegible en
    # Galápagos el motor lo escala por el mismo GALAPAGOS_IPCEG_FACTOR ya sellado en D5, antes de
    # calcular salario, horas extra, IESS, décimos, vacaciones y fondo de reserva. Un empleado
    # tributa igual que en el continente (misma tabla progresiva) sobre esta base ya escalada. No
    # cubre "derechos adquiridos" de empleados anteriores a la reforma con el 75%/100% fijo: para
    # ellos se declara directamente el salario congelado como `wage`, sin activar este factor.
    if data.get('galapagos') == 'SI':
        wage = money(wage*number(GALAPAGOS_IPCEG_FACTOR))
    for key, value in data.items():
        if key in ('bonus', 'commission', 'non_taxable_income', 'advances', 'loans', 'other_deductions', 'personal_expenses', 'hours_50', 'hours_100', 'night_hours', 'vacation_payout',
                   'sick_days', 'maternity_days', 'unpaid_leave_days', 'unexcused_absence_days', 'paternity_days',
                   'net_income_target', 'employer_assumed_tax', 'sick_prior_days', 'sick_annual_prior_days', 'sick_iess_base', 'sick_complement_pct') and number(value) < 0:
            raise ValueError('Las novedades y descuentos deben ser no negativos.')
    # Caso 8 (DI25-03): ausencias, verificadas contra el Oficio PGE No. 10097 (17-02-2025, art. 54
    # Código del Trabajo y art. 16 Reglamento General sobre Prestación de Subsidios en Dinero) y
    # contra el art. 152 del Código del Trabajo (reforma 2023). Días 1-3 de enfermedad: el
    # empleador paga el 100 %, pero esos días no son materia gravada de IESS (sí de IR); desde el
    # día 4 el empleador no paga nada (subsidio directo del IESS, ajeno a esta nómina; se reporta
    # como novedad "Subsidiado", no se calcula aquí). Maternidad: el empleador paga el 25 % de
    # todos los días de licencia y ese 25 % sí es materia gravada de IESS (continuidad de
    # aportación). Permiso no pagado y falta injustificada: 0 % de pago, reducen tanto IESS como
    # IR. Paternidad: el empleador paga el 100 % y es materia gravada de IESS, igual que un día
    # trabajado normal — no cambia ningún cálculo, solo se registra para control de asistencia.
    sick_days = number(data.get('sick_days', 0))
    sick_pay, sick_days_employer50, sick_iess_estimate = sick_leave_pay(data, wage, sick_days)
    maternity_days = number(data.get('maternity_days', 0))
    unpaid_leave_days = number(data.get('unpaid_leave_days', 0))
    unexcused_absence_days = number(data.get('unexcused_absence_days', 0))
    absence_days = sick_days+maternity_days+unpaid_leave_days+unexcused_absence_days
    if absence_days > days:
        raise ValueError('Los días de ausencia no pueden superar los días del período.')
    normal_days = days-absence_days
    salary = money(wage*normal_days/30)
    maternity_pay = money(wage*maternity_days/30*Decimal('0.25'))
    hourly = wage/number(parameters['monthly_hours'])
    overtime = sum(money(hourly*number(data.get(key, 0))*number(parameters[factor])) for key, factor in [('hours_50','overtime_50'), ('hours_100','overtime_100'), ('night_hours','night_rate')])
    base = money(salary+maternity_pay+overtime+number(data.get('bonus', 0))+number(data.get('commission', 0)))
    iess = money(base*number(parameters['personal_rate']))
    employer = money(base*number(parameters['employer_rate']))
    employer_other = money(base*number(parameters.get('employer_other_rate',0)))
    # D6 (DI25-03): con meses contabilizados del mismo ejercicio se proyecta sobre lo acumulado, se recalcula el
    # impuesto causado y la rebaja, se restan las retenciones ya efectuadas y el saldo se reparte entre los meses
    # que faltan. Sin historial rige la proyección anual de siempre (12 meses, sin retenciones previas).
    prior_months = int(data.get('prior_months', 0) or 0)
    remaining_months = max(1, 12-prior_months) if prior_months else 12
    other_income = number(data.get('other_income', 0))-number(data.get('other_iess', 0))
    # Gravado de IR, no de IESS (caso 3/caso 8, DI25-03): liquidación de vacaciones no gozadas,
    # beneficios propios sin aporte y el pago de los días 1-3 de enfermedad (catálogo RDEP
    # vigente, campo sobSuelComRemu). Es un pago del mes, no una proyección: se suma una sola vez
    # a la base anual, igual que other_income (D8), sin multiplicarla por los meses que faltan.
    vacation_payout = number(data.get('vacation_payout', 0))+sick_pay
    annual_base = max(Decimal(0), number(data.get('prior_base', 0))+(base-iess)*remaining_months+other_income+vacation_payout)
    _, exemption, annual_base = apply_personal_exemption(annual_base, parameters, data.get('exemptions', ()))
    annual_tax, rebate, tax_after_rebate = annual_income_tax(
        annual_base, data.get('personal_expenses', 0), parameters,
        data.get('dependents_count', 0), data.get('galapagos', 'NO'),
        special_expense=data.get('special_expense', False))
    # Caso 11 (DI25-03): impuesto asumido por el empleador ("contrato de ingreso neto en nómina",
    # casillero 381 F107). net_income_target es el neto MENSUAL garantizado por contrato (igual de
    # recurrente que wage, no un pago único como vacation_payout); se suma íntegro al bruto del
    # trabajador y NO pasa por el IESS ni por la retención mensual de este período (el empleador lo
    # paga aparte a la SRI, no se lo descuenta al trabajador). Para el impuesto que el empleador
    # asume se proyecta el mismo neto a los meses que faltan (igual que la base salarial, arriba),
    # se resuelve el impuesto ANUAL por bisección (gross_up_assumed_tax) contra la base anual ya
    # calculada, y se reparte entre los meses que faltan -- mismo patrón que already_withheld/tax
    # más abajo. Se suma al monto manual del campo, si lo hubiera, para reportarlo en el RDEP
    # (impRentEmpl/valImpAsuEsteEmpl). No se combina con el convenio de doble imposición: son
    # mecanismos independientes que no se han visto juntos en un mismo caso real.
    net_income_target = number(data.get('net_income_target', 0))
    employer_assumed_tax = number(data.get('employer_assumed_tax', 0))
    if net_income_target:
        annual_assumed_tax = gross_up_assumed_tax(
            net_income_target*remaining_months, annual_base, data.get('personal_expenses', 0), parameters,
            data.get('dependents_count', 0), data.get('galapagos', 'NO'),
            special_expense=data.get('special_expense', False))
        employer_assumed_tax += money(annual_assumed_tax/remaining_months)
    # Caso 11 (DI25-03): convenio de doble imposición registrado (erpec.payroll.tax.treaty) para
    # el país de residencia del empleado. "exempt" (potestad exclusiva del país de residencia,
    # p. ej. Decisión 578 CAN): no se retiene impuesto a la renta en Ecuador por esta relación de
    # dependencia. "capped_rate": el tratado fija una tasa tope sobre la base anual, en vez de la
    # tabla progresiva y la rebaja de gastos personales (que no aplican bajo un tope de tratado).
    treaty_mechanism = data.get('treaty_mechanism')
    if treaty_mechanism == 'exempt':
        annual_tax = rebate = tax_after_rebate = Decimal(0)
    elif treaty_mechanism == 'capped_rate':
        tax_after_rebate = annual_tax = money(annual_base*number(data.get('treaty_rate', 0))/100)
        rebate = Decimal(0)
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
    gross = money(base+number(data.get('non_taxable_income', 0))+monthly13+monthly14+reserve_paid+vacation_payout+net_income_target)
    advances, loans, other = [money(data.get(key, 0)) for key in ('advances','loans','other_deductions')]
    deductions = money(iess+tax+advances+loans+other)
    net = money(gross-deductions)
    if net < 0:
        raise ValueError('El neto a recibir no puede ser negativo.')
    accrued13, accrued14, reserve_iess = thirteenth-monthly13, fourteenth-monthly14, reserve-reserve_paid
    # Importes ya pagados con el rol por mensualización: el finiquito los descuenta para no pagarlos dos veces.
    cost = money(gross+employer+employer_other+accrued13+accrued14+vacation+reserve_iess+employer_assumed_tax)
    # Estas magnitudes son proyecciones mensuales; el RDEP aplica la misma tarifa
    # a los acumulados efectivos, sin copiar una proyección de un mes aislado.
    return {key: float(value) for key, value in {'days':days, 'salary':salary, 'overtime':overtime, 'base':base, 'gross':gross, 'personal_iess':iess, 'tax':tax, 'advances':advances, 'loans':loans, 'other_deductions':other, 'deductions':deductions, 'net':net, 'employer_iess':employer, 'employer_other':employer_other, 'thirteenth':accrued13, 'fourteenth':accrued14, 'vacation':vacation, 'vacation_payout':vacation_payout, 'reserve_iess':reserve_iess, 'cost':cost, 'annual_tax_caused':annual_tax, 'personal_expense_rebate':rebate, 'personal_expense_rebate_applied':min(annual_tax,rebate), 'annual_tax_after_rebate':tax_after_rebate, 'personal_exemption':exemption, 'employer_assumed_tax':employer_assumed_tax, 'sick_days_employer50':sick_days_employer50, 'sick_iess_estimate':sick_iess_estimate, 'thirteenth_paid':monthly13, 'fourteenth_paid':monthly14, 'reserve_paid':reserve_paid}.items()}


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
