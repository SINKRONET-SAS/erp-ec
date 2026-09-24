"""La matriz de aceptación no puede apuntar a pruebas que ya no existen."""
import re
from pathlib import Path

from odoo.tests import TransactionCase, tagged

from ..matrix import CYCLES, ROLES

ADDONS = Path(__file__).resolve().parents[2]


def _defines(module, filename, method):
    path = ADDONS / module / 'tests' / filename
    return path.is_file() and re.search(r'def %s\(' % re.escape(method), path.read_text(encoding='utf-8')) is not None


@tagged('post_install', '-at_install')
class MatrixCase(TransactionCase):
    def test_every_cycle_step_points_to_an_existing_test(self):
        missing = [(cycle, step) for cycle, steps in CYCLES.items() for step, module, filename, method in steps
                   if not _defines(module, filename, method)]
        self.assertFalse(missing, 'Pasos de la matriz sin prueba: %s' % missing)

    def test_every_role_aspect_points_to_an_existing_test(self):
        missing = [(role, ref) for role, refs in ROLES.items() for ref in refs if not _defines(*ref)]
        self.assertFalse(missing, 'Roles de la matriz sin prueba: %s' % missing)

    def test_all_required_cycles_and_roles_are_listed(self):
        self.assertEqual(len(CYCLES), 7)
        for needle in ('vendedor', 'comprador', 'operario', 'nómina', 'contador', 'administrador', 'multiempresa', 'concurrente'):
            self.assertTrue(any(needle in role for role in ROLES), needle)
