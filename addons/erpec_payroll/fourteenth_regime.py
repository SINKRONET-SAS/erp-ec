"""Régimen regional del décimo cuarto sueldo (DI26-C.1, hallazgo DI26-05).

Base legal verificada el 25-09-2026 en la base legal publicada por el Ministerio del Trabajo
(salarios.trabajo.gob.ec/documentos/base legal.pdf): el décimo cuarto se paga hasta el 15 de marzo en las regiones
Costa e Insular y hasta el 15 de agosto en las regiones Sierra y Amazónica, según el régimen escolar de la
circunscripción. Los instructivos del Ministerio de Economía y Finanzas (Sierra 2025, Costa 2026) fijan los períodos
de cálculo del 1 de agosto al 31 de julio y del 1 de marzo al último día de febrero, respectivamente."""
from odoo import fields, models

FOURTEENTH_REGIMES = [
    ('sierra_amazonia', 'Sierra y Amazonía (pago hasta el 15 de agosto)'),
    ('costa_insular', 'Costa e Insular (pago hasta el 15 de marzo)'),
]


class Company(models.Model):
    _inherit = 'res.company'
    ec_fourteenth_regime = fields.Selection(FOURTEENTH_REGIMES, string='Régimen del décimo cuarto por defecto',
        help='Se propone a cada empleado nuevo; el régimen efectivo es el del empleado (según el régimen escolar de la '
             'circunscripción donde trabaja).')


class Employee(models.Model):
    _inherit = 'hr.employee'
    ec_fourteenth_regime = fields.Selection(FOURTEENTH_REGIMES, string='Régimen del décimo cuarto',
        default=lambda self: self.env.company.ec_fourteenth_regime,
        help='Determina el período de cálculo y la fecha límite de pago del décimo cuarto sueldo de este empleado.')
