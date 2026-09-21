"""Casos sintéticos con referencias aritméticas independientes del motor."""
BASE_INPUTS = dict(current_income=18000, current_iess=1701, current_withheld=50,
                   other_income=0, other_iess=0, other_withheld=0,
                   personal_expenses=1000, dependents=0, remaining_months=3,
                   exempt_thirteenth=0, exempt_fourteenth=0, exempt_reserve=0,
                   galapagos='NO', special_condition='none')
CASES = {
    'baseline': ('01 · Sin otro empleador', {}, 16299, 242, 62, 12,
                 '18.000 − 1.701 = 16.299; 167 + (16.299 − 15.549) × 10 % = 242; '
                 'gastos 1.000 × 18 % = 180; IR 62; menos retención 50: saldo 12.'),
    'previous': ('02 · Ingreso anterior de USD 6.000',
                 dict(other_income=6000, other_iess=567, other_withheld=150),
                 21732, 816.28, 636.28, 436.28,
                 '24.000 − 2.268 = 21.732; 631 + (21.732 − 20.188) × 12 % = 816,28; '
                 'rebaja 180; IR 636,28; menos retenciones 200: saldo 436,28. Acumulado anterior incluido una sola vez.'),
    'higher': ('03 · Ingreso anterior de USD 10.000',
               dict(other_income=10000, other_iess=945, other_withheld=150),
               25354, 1250.92, 1070.92, 870.92,
               '28.000 − 2.646 = 25.354; 631 + (25.354 − 20.188) × 12 % = 1.250,92; '
               'rebaja 180; IR 1.070,92; menos retenciones 200: saldo 870,92.'),
    'salary_change': ('04 · Cambio salarial a mitad del año',
                      dict(current_income=21000, current_iess=1984.50),
                      19015.50, 513.65, 333.65, 283.65,
                      '6 meses × 1.500 + 6 × 2.000 = 21.000; IESS supuesto 9,45 % = 1.984,50; '
                      'base 19.015,50; 167 + (19.015,50 − 15.549) × 10 % = 513,65; '
                      'rebaja 180; IR 333,65; saldo 283,65. No calcula automáticamente contratos.'),
    'absence': ('05 · Mes con ingreso reducido por ausencia',
                dict(current_income=17500, current_iess=1653.75),
                15846.25, 196.73, 16.73, 0,
                'Hipótesis a revisar: 11 × 1.500 + 1 × 1.000 = 17.500; IESS 1.653,75; '
                'base 15.846,25; 167 + (15.846,25 − 15.549) × 10 % = 196,725; '
                'rebaja 180; IR redondeado 16,73. Retención 50: excedente 33,27. '
                'Revisar la naturaleza de la ausencia y base IESS; no valida el descuento laboral.'),
}
# USD 5.000 mensuales: base 60.000 − 5.670 = 54.330.
# IR causado independiente: 4.965 + (54.330 − 46.575) × 25 % = 6.903,75.
# Cada valor siguiente es referencia explícita; no se obtiene llamando al motor.
SALARY_5000 = (
    ('NO', 0, 5868.28), ('NO', 1, 5572.43), ('NO', 2, 5276.59),
    ('NO', 3, 4832.81), ('NO', 4, 4389.04), ('NO', 5, 3945.27),
    ('SI', 0, 5036.80), ('SI', 1, 4503.39), ('SI', 2, 3969.97),
    ('SI', 3, 3169.85), ('SI', 4, 2369.73), ('SI', 5, 1569.61),
)
for index, (region, dependents, expected) in enumerate(SALARY_5000, start=6):
    label = 'Galápagos' if region == 'SI' else 'Continente'
    baskets = (7, 9, 11, 14, 17, 20)[dependents]
    factor = ' × 1,803' if region == 'SI' else ''
    CASES['salary5000_'+region.lower()+'_'+str(dependents)] = (
        f'{index:02d} · USD 5.000 · {label} · {dependents} cargas',
        dict(current_income=60000, current_iess=5670, current_withheld=0, personal_expenses=30000,
             remaining_months=12, dependents=dependents, galapagos=region),
        54330, 6903.75, expected, expected,
        f'60.000 − 5.670 = 54.330; 4.965 + (54.330 − 46.575) × 25 % = 6.903,75. '
        f'Rebaja máxima de referencia = 821,80 × {baskets}{factor} × 18 %. '
        f'IR anual esperado: {expected:.2f}. Gastos ficticios 30.000 para alcanzar el tope; '
        'la rebaja real depende de gastos sustentados y cargas válidas. '
        'Galápagos requiere confirmar elegibilidad; no se usa la deducción histórica de 2016.')
CASES['exempt_benefits'] = (
    '18 · Décimos y reserva separados del ingreso gravado',
    dict(current_income=60000, current_iess=5670, current_withheld=0, personal_expenses=30000,
         remaining_months=12, exempt_thirteenth=5000, exempt_fourteenth=482, exempt_reserve=5000),
    54330, 6903.75, 5868.28, 5868.28,
    'Gravados 60.000; décimos y reserva informativos 5.000 + 482 + 5.000 = 10.482. '
    'Total informado 70.482, pero base IR 54.330 e IR 5.868,28. La mensualización no convierte '
    'los conceptos exentos en gravados. Montos dados para contraste; no devengo ni mapeo RDEP automático.')
CASES['annual_close'] = (
    '19 · Cierre anual con retenciones conciliadas',
    dict(other_income=6000, other_iess=567, other_withheld=150, current_withheld=486.28,
         remaining_months=1),
    21732, 816.28, 636.28, 0,
    'Base 21.732; IR después de rebaja 636,28. Retenciones 486,28 + 150 = 636,28; saldo cero. '
    'Conciliación del impuesto en este ensayo; no valida por sí sola todo el XML ni sus casilleros.')

# Referencias explícitas: 100 × 821,80 = 82.180; Galápagos × 1,803 = 148.170,54.
# Las cargas no multiplican ni se suman al tope especial.
SPECIAL_CASES = (
    ('special_holder', '20 · Titular · 100 canastas · gastos 30.000', 'holder', 'NO', 0, 60000, 5670, 30000, 54330, 6903.75, 1503.75,
     'Rebaja 30.000 × 18 % = 5.400; IR 6.903,75 − 5.400 = 1.503,75.'),
    ('special_dependent', '21 · Carga familiar · 100 canastas · gastos 30.000', 'dependent', 'NO', 1, 60000, 5670, 30000, 54330, 6903.75, 1503.75,
     'Una carga con condición especial: mismo tope 82.180; rebaja 5.400; IR 1.503,75.'),
    ('special_zero', '22 · Rebaja especial mayor al impuesto · sin devolución', 'holder', 'NO', 0, 60000, 5670, 100000, 54330, 6903.75, 0,
     'Rebaja calculada 82.180 × 18 % = 14.792,40; supera el causado 6.903,75. IR cero; la diferencia no genera devolución.'),
    ('special_cap', '23 · Tope especial continental · gastos 200.000', 'dependent', 'NO', 5, 240000, 22680, 200000, 217320, 64296.68, 49504.28,
     'Base 217.320; causado 24.572 + (217.320 − 109.956) × 37 % = 64.296,68; rebaja 14.792,40; IR 49.504,28. No sumar canastas por cinco cargas.'),
    ('special_galapagos', '24 · Tope especial Galápagos · gastos 200.000', 'holder', 'SI', 0, 240000, 22680, 200000, 217320, 64296.68, 37625.98,
     'Tope 82.180 × 1,803 = 148.170,54; rebaja 26.670,70; IR 64.296,68 − 26.670,70 = 37.625,98. Elegibilidad insular pendiente.'),
    ('special_no_expenses', '25 · Supuesto especial sin gastos · sin rebaja', 'holder', 'NO', 0, 60000, 5670, 0, 54330, 6903.75, 6903.75,
     'La condición especial no concede automáticamente el máximo: gastos cero; rebaja cero; IR 6.903,75.'),
)
for key, label, condition, region, dependents, income, iess, expenses, base, caused, annual, note in SPECIAL_CASES:
    CASES[key] = (label, dict(special_condition=condition, galapagos=region, dependents=dependents,
                             current_income=income, current_iess=iess, current_withheld=0,
                             personal_expenses=expenses, remaining_months=12),
                  base, caused, annual, annual,
                  note + ' Solo rebaja por gastos; no calcula exención personal por discapacidad ni valida certificados.')
