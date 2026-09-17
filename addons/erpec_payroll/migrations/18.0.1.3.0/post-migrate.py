"""Migración real (no solo el hook de instalación fresca): rellena los campos tipados de
erpec.payroll.policy para versiones creadas antes de que esos campos existieran. Actualizar el
módulo agrega columnas nuevas con su valor por defecto (cero); no reescribe registros ya
guardados. Bug real encontrado por el titular en una versión activa del 11-09-2026: mostraba
ceros en "Parámetros legales" pese a tener un `parameters` JSON correcto y ya usado por el
motor de cálculo. Corre también sobre versiones activas (usa el token interno dentro de
Policy._apply_parameters_json), porque no cambia ningún valor de negocio: solo hace visibles
como campos los mismos datos que ya estaban en el JSON."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for policy in env['erpec.payroll.policy'].search([]):
        if policy.minimum_salary == 0 and policy.parameters:
            policy._apply_parameters_json(policy.parameters)
