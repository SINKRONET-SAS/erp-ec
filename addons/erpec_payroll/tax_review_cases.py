"""Casos sintéticos con referencias aritméticas independientes del motor."""
BASE_INPUTS = dict(current_income=18000, current_iess=1701, current_withheld=50,
                   other_income=0, other_iess=0, other_withheld=0,
                   personal_expenses=1000, dependents=0, remaining_months=3,
                   exempt_thirteenth=0, exempt_fourteenth=0, exempt_reserve=0,
                   galapagos='NO', special_condition='none',
                   exemption_kind='none', disability_percentage=0, exemption_months=12)
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

# Exenciones personales de la base (LRTI art. 9 num. 12; Reglamento LRTI arts. 49-50; Reglamento LOD art. 6).
# Fracción básica 2026 = 12.208. Cada referencia es aritmética independiente del motor.
# Base común: 30.000 − 2.835 (IESS supuesto 9,45 %) = 27.165. Sin exención el IR sería 1.481,75.
EXEMPTION_CASES = (
    ('exempt_elderly', '26 · Adulto mayor · una fracción básica', dict(exemption_kind='elderly'), 27165, 137.45,
     'Exención 12.208; base gravable 14.957; (14.957 − 12.208) × 5 % = 137,45. No se prorratea por la fecha de cumpleaños.'),
    ('exempt_disability_40', '27 · Discapacidad 40 % · aplica 60 %', dict(exemption_kind='disability', disability_percentage=40), 27165, 15.37,
     '2 × 12.208 × 60 % = 14.649,60; base gravable 12.515,40; (12.515,40 − 12.208) × 5 % = 15,37.'),
    ('exempt_disability_50', '28 · Discapacidad 50 % · aplica 70 %', dict(exemption_kind='disability', disability_percentage=50), 27165, 0,
     '24.416 × 70 % = 17.091,20; base gravable 10.073,80, dentro de la fracción básica: IR cero.'),
    ('exempt_disability_100', '29 · Discapacidad 100 % · aplica 100 %', dict(exemption_kind='disability', disability_percentage=100), 27165, 0,
     'Exención 24.416; base gravable 2.749: IR cero.'),
    ('exempt_substitute', '30 · Sustituto 80 % durante seis meses', dict(exemption_kind='substitute', disability_percentage=80, exemption_months=6), 27165, 351.96,
     '24.416 × 80 % = 19.532,80; por 6/12 = 9.766,40; base gravable 17.398,60; 167 + (17.398,60 − 15.549) × 10 % = 351,96.'),
    ('exempt_capped', '31 · Exención limitada por la base disponible', dict(exemption_kind='elderly', current_income=10000, current_iess=945), 9055, 0,
     'Base 9.055 menor que 12.208: se aplica solo 9.055, no el monto máximo; base gravable cero.'),
    ('exempt_with_special', '32 · Discapacidad 100 % con tope de 100 canastas',
     dict(exemption_kind='disability', disability_percentage=100, special_condition='holder', current_income=60000,
          current_iess=5670, personal_expenses=8000), 54330, 454.10,
     'Base 54.330 − 24.416 = 29.914; 1.412 + (29.914 − 26.700) × 15 % = 1.894,10; rebaja 8.000 × 18 % = 1.440; IR 454,10. '
     'La exención de la base y el tope de gastos son beneficios distintos y coexisten.'),
)
for key, label, overrides, base, annual, note in EXEMPTION_CASES:
    inputs = dict(current_income=30000, current_iess=2835, current_withheld=0, personal_expenses=0, remaining_months=12)
    inputs.update(overrides)
    CASES[key] = (label, inputs, base, {'exempt_with_special': 1894.10}.get(key, annual), annual, annual,
                  note + ' Solo exención de la base y tarifa; no valida documentos, calificación ni la entrega del 15 de enero.')
