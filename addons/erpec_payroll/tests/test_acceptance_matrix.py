"""La matriz de pendientes DI25-03 no puede afirmar un control sin prueba ni marcarse a mano."""
import re
from pathlib import Path

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

TESTS_DIRECTORY = Path(__file__).resolve().parent
# Decisión de cada punto en el pronunciamiento técnico del 21-09-2026 (fuente independiente de los datos del módulo).
PRONOUNCEMENT = {
    'D1': 'corregir', 'D2': 'corregir', 'D3': 'aceptar', 'D4': 'condicionar', 'D5': 'corregir', 'D6': 'condicionar',
    'D7': 'rechazar', 'D8': 'corregir',
    'C01': 'condicionar', 'C02': 'parcial', 'C03': 'bloquear', 'C04': 'condicionar', 'C05': 'bloquear', 'C06': 'bloquear',
    'C07': 'bloquear', 'C08': 'mixto', 'C09': 'bloquear', 'C10': 'bloquear', 'C11': 'mixto',
}


def repository_tests():
    names = set()
    for path in TESTS_DIRECTORY.glob('test_*.py'):
        names |= set(re.findall(r'def (test_\w+)', path.read_text(encoding='utf-8')))
    return names


@tagged('post_install', '-at_install')
class AcceptanceMatrixCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.rows = self.env['erpec.payroll.acceptance.matrix'].search([])

    def test_every_decision_and_case_of_the_pronouncement_is_present_with_its_decision(self):
        self.assertEqual({row.code: row.expert_decision for row in self.rows}, PRONOUNCEMENT)

    def test_every_claimed_control_cites_tests_that_exist(self):
        existing = repository_tests()
        for row in self.rows:
            cited = [name.strip() for name in (row.tests or '').split(',') if name.strip()]
            with self.subTest(code=row.code):
                if row.control_state != 'external':
                    self.assertTrue(cited, 'La fila %s declara un control sin pruebas.' % row.code)
                self.assertEqual([name for name in cited if name not in existing], [], 'Pruebas inexistentes en %s.' % row.code)

    def test_nothing_is_presented_as_accepted(self):
        for row in self.rows:
            with self.subTest(code=row.code):
                self.assertTrue(row.pending.strip() and row.owner.strip())
                self.assertIn('Pendiente', row.external_acceptance)
        self.assertNotIn('homologated', {state for state, _label in self.rows._fields['control_state'].selection})

    def test_states_are_consistent_with_the_documented_limits(self):
        by_code = {row.code: row for row in self.rows}
        # Lo que depende del SRI nunca figura como control automático completo.
        for code in ('D5', 'C10'):
            self.assertNotEqual(by_code[code].control_state, 'automated', code)
        # C09 (décimos y fondos de reserva) y C03 (matriz de incidencia estatutaria, con la
        # decisión explícita de aportabilidad para beneficios propios) sí son automáticos: el
        # titular confirmó/aportó sus especificaciones (18.0.1.14.7 y 18.0.1.14.9).
        self.assertEqual(by_code['C03'].control_state, 'automated')
        self.assertEqual(by_code['D8'].control_state, 'automated')
        self.assertEqual(by_code['C09'].control_state, 'automated')

    def test_the_matrix_is_read_only_for_payroll_managers(self):
        manager = new_test_user(self.env, login='matriz_solo_lectura', groups='base.group_user,erpec_payroll.group_payroll_manager')
        row = self.rows[:1]
        self.assertEqual(row.with_user(manager).code, row.code)  # puede leer
        for operation in ('write', 'create', 'unlink'):  # el permiso de acceso lo niega antes de cualquier escritura
            with self.subTest(operation=operation), self.assertRaises(AccessError):
                row.with_user(manager).check_access(operation)
        # Defensa en el modelo: aun con permiso, sin superusuario no se cambia la matriz.
        for action in (lambda: row.with_user(manager).write({'control_state': 'automated'}),
                       lambda: self.env['erpec.payroll.acceptance.matrix'].with_user(manager).create({'code': 'X', 'item': 'x'}),
                       lambda: row.with_user(manager).unlink()):
            with self.assertRaises(ValidationError):
                action()

    def test_views_compile_and_the_menu_is_exposed(self):
        model = self.env['erpec.payroll.acceptance.matrix']
        views = model.get_views([(False, 'list'), (False, 'form'), (False, 'search')])
        self.assertEqual(set(views['views']), {'list', 'form', 'search'})
        menu = self.env.ref('erpec_payroll.acceptance_matrix_menu')
        self.assertEqual(menu.parent_id, self.env.ref('erpec_payroll.payroll_menu'))
        self.assertEqual(menu.action.res_model, 'erpec.payroll.acceptance.matrix')
