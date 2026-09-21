"""Matriz de pendientes DI25-03: estado real de cada decisión y caso del pronunciamiento técnico.

Los datos se cargan desde `acceptance_matrix_data.xml` y solo cambian con una versión del módulo. Es de
solo lectura: nadie marca una fila como resuelta a mano. Una prueba automática exige que cada fila
declarada como control automático, parcial o bloqueo cite pruebas que existan en el repositorio.
"""
from odoo import api, fields, models
from odoo.exceptions import ValidationError

DECISIONS = [('corregir', 'Corregir'), ('aceptar', 'Aceptar'), ('condicionar', 'Condicionar'), ('rechazar', 'Rechazar'),
             ('parcial', 'Parcial'), ('bloquear', 'Bloquear'), ('mixto', 'Mixto')]
STATES = [('automated', 'Control automático'), ('partial', 'Control parcial'), ('blocked', 'Bloqueo automático'),
          ('external', 'Depende de un tercero')]


class AcceptanceMatrix(models.Model):
    _name = 'erpec.payroll.acceptance.matrix'
    _description = 'Matriz de pendientes DI25-03'
    _order = 'sequence, code'

    sequence = fields.Integer('Orden', readonly=True)
    code = fields.Char('Código', readonly=True, required=True)
    item = fields.Char('Decisión o caso', readonly=True, required=True)
    expert_decision = fields.Selection(DECISIONS, 'Decisión del responsable tributario', readonly=True, required=True)
    control_state = fields.Selection(STATES, 'Estado del control', readonly=True, required=True)
    control = fields.Text('Control que existe hoy', readonly=True, required=True)
    tests = fields.Char('Pruebas que lo respaldan', readonly=True,
                        help='Nombres de pruebas del repositorio, separados por coma. Una prueba automática verifica que existan.')
    pending = fields.Text('Lo que sigue pendiente', readonly=True, required=True)
    owner = fields.Char('Quién lo destraba', readonly=True, required=True)
    external_acceptance = fields.Char('Aceptación externa', readonly=True, default='Pendiente: no homologado por el responsable tributario')
    _sql_constraints = [('code_unique', 'unique(code)', 'El código de la matriz es único.')]

    def _guard(self):
        if not self.env.su:
            raise ValidationError('La matriz de pendientes es de solo lectura: cambia con la versión del módulo y su evidencia.')

    @api.model_create_multi
    def create(self, values_list):
        self._guard()
        return super().create(values_list)

    def write(self, values):
        self._guard()
        return super().write(values)

    def unlink(self):
        self._guard()
        return super().unlink()
