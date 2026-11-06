"""Regresiones del motor real sin Odoo ni PostgreSQL; no sustituyen pruebas ORM."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'di06_payroll'
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / 'addons/erpec_payroll')]
sys.modules[PACKAGE] = package


def load(name):
    spec = importlib.util.spec_from_file_location(PACKAGE + '.' + name, ROOT / 'addons/erpec_payroll' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


engine = load('engine')
settlement = load('settlement')
params = load('parameters_ec2026').PARAMS


def result(start, end, **extra):
    data = dict(cause='despido_intempestivo', modality='rol_primero', start_date=start,
                end_date=end, wage=1200, fourteenth_regime='sierra_amazonia')
    data.update(extra)
    return settlement.settle(data, params)


class CalendarRegression(unittest.TestCase):
    def test_snapshot_changes_when_calculation_changes(self):
        from unittest.mock import patch
        data = dict(cause='despido_intempestivo', modality='rol_primero', start_date=date(2024, 1, 1),
                    end_date=date(2026, 12, 31), wage=1200, fourteenth_regime='sierra_amazonia')
        current, digest = settlement.calculation_snapshot(data, params)
        old = dict(current, dismissal=4800)
        with patch.object(settlement, 'settle', return_value=old):
            _, old_digest = settlement.calculation_snapshot(data, params)
        self.assertNotEqual(digest, old_digest)
        self.assertEqual(settlement.calculation_snapshot(data, dict(reversed(list(params.items()))))[1], digest)

    def test_snapshot_changes_when_inputs_change(self):
        data = dict(cause='despido_intempestivo', modality='rol_primero', start_date=date(2024, 1, 1),
                    end_date=date(2026, 12, 31), wage=1200, fourteenth_regime='sierra_amazonia')
        self.assertNotEqual(settlement.calculation_snapshot(data, params)[1],
                            settlement.calculation_snapshot(dict(data, other_deductions=1), params)[1])

    def test_three_calendar_years_include_leap_day(self):
        self.assertEqual(result(date(2024, 1, 1), date(2026, 12, 31))['dismissal'], 3600)

    def test_fraction_after_three_years(self):
        self.assertEqual(result(date(2024, 1, 1), date(2027, 1, 1))['dismissal'], 4800)

    def test_desahucio_before_first_anniversary(self):
        self.assertEqual(result(date(2024, 1, 1), date(2024, 12, 30))['desahucio'], 0)

    def test_desahucio_full_year_inclusive(self):
        self.assertEqual(result(date(2024, 1, 1), date(2024, 12, 31))['desahucio'], 300)

    def test_dismissal_cap(self):
        self.assertEqual(result(date(1990, 1, 1), date(2026, 1, 1))['dismissal'], 30000)

    def test_february_anniversary(self):
        self.assertEqual(settlement.service_years(date(2024, 2, 29), date(2025, 2, 27)), (1, False))
        self.assertEqual(settlement.service_years(date(2024, 2, 29), date(2025, 2, 28)), (1, True))

    def test_same_day_and_invalid_order(self):
        self.assertEqual(result(date(2026, 1, 1), date(2026, 1, 1))['desahucio'], 0)
        with self.assertRaises(ValueError):
            result(date(2026, 1, 2), date(2026, 1, 1))

    def test_no_double_last_salary(self):
        self.assertEqual(result(date(2024, 1, 1), date(2026, 11, 15))['pending_salary'], 0)
        self.assertEqual(result(date(2024, 1, 1), date(2026, 11, 15), modality='con_finiquito')['pending_salary'], 600)

    def test_sickness_keeps_episode_continuity(self):
        from decimal import Decimal
        pay, days, subsidy = engine.sick_leave_pay({'sick_eligibility': 'eligible', 'sick_prior_days': 2,
            'sick_iess_rate': 75, 'sick_iess_base': 1200}, Decimal(1200), Decimal(3))
        self.assertEqual((pay, days, subsidy), (Decimal(40), Decimal(0), Decimal(60)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
