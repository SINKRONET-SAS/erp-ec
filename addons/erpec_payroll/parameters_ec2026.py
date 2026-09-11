"""Parámetros Ecuador 2026: régimen privado general, territorio continental.
Fuentes oficiales verificadas el 11-09-2026. La base de 240 es divisor salarial,
no una jornada efectiva mensual. El recargo nocturno se agrega al salario base.
"""
PARAMS = {
    'minimum_salary': 482, 'monthly_hours': 240,
    'personal_rate': 0.0945, 'employer_rate': 0.1115, 'employer_other_rate': 0.01,
    'reserve_rate': 0.0833, 'reserve_months': 12,
    'thirteenth_rate': 1/12, 'fourteenth_rate': 1/12, 'vacation_rate': 1/24,
    'expense_limit': 5752.60, 'rebate_rate': 0.18,
    'overtime_50': 1.5, 'overtime_100': 2, 'night_rate': 0.25,
    'tax_brackets': [
        {'from':0, 'to':12208, 'base':0, 'rate':0},
        {'from':12208, 'to':15549, 'base':0, 'rate':0.05},
        {'from':15549, 'to':20188, 'base':167, 'rate':0.10},
        {'from':20188, 'to':26700, 'base':631, 'rate':0.12},
        {'from':26700, 'to':35136, 'base':1412, 'rate':0.15},
        {'from':35136, 'to':46575, 'base':2678, 'rate':0.20},
        {'from':46575, 'to':62005, 'base':4965, 'rate':0.25},
        {'from':62005, 'to':82679, 'base':8823, 'rate':0.30},
        {'from':82679, 'to':109956, 'base':15025, 'rate':0.35},
        {'from':109956, 'to':None, 'base':24572, 'rate':0.37},
    ],
}
SOURCES = {
    'sbu': 'https://www.trabajo.gob.ec/wp-content/plugins/download-monitor/download.php?force=1&id=4933',
    'iess': 'https://www.iess.gob.ec/es/preguntas-frecuentes-afiliacion',
    'reserve': 'https://www.iess.gob.ec/web/afiliado/fondos-de-reserva',
    'hours': 'https://calculadoras.trabajo.gob.ec/valor',
    'income_tax': 'https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/fa75d2ba-c784-4b33-af3a-8390f2f7af13/Tablas%20c%C3%A1lculo%20IR.pdf',
    'expenses': 'https://www.sri.gob.ec/detalle-noticias?idnoticia=1261&marquesina=1',
    'employer_other': 'https://www.epam.gob.ec/wp-content/uploads/2016/03/CODIGO-ORGANICO-MONETARIO-Y-FINANCIERO.pdf',
    'vacation': 'https://www.gob.ec/sites/default/files/regulations/2018-10/C%C3%B3digo-del-Trabajo.pdf',
    'benefits': 'https://www.trabajo.gob.ec/29-cual-es-el-plazo-y-como-se-debe-realizar-la-solicitud-para-la-acumulacion-del-pago-de-la-decima-tercera-y-decima-cuarta-remuneracion/',
}
