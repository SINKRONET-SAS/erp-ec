"""Pruebas negativas de ejecutor sin conectar ni eliminar bases reales."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('runner', Path(__file__).with_name('test-integrated.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerSafety(unittest.TestCase):
    def test_each_run_gets_its_own_free_http_port(self):
        ports = {runner.free_port() for _ in range(5)}
        self.assertTrue(all(1024 < port < 65536 for port in ports))
        self.assertNotIn(8069, ports)
        # Dos suites en paralelo no comparten el puerto por defecto de las pruebas HTTP (fallo TestHealth del 21-09-2026).
        source = Path(__file__).with_name('test-integrated.py').read_text(encoding='utf-8')
        self.assertIn("'http_port': str(free_port())", source)

    def test_foreign_names(self):
        for name in ['erpec_demo', 'postgres', 'ec_integrated_test_', '../ec_integrated_test_a']:
            with self.assertRaises(ValueError):
                runner.validate_name(name)

    def test_existing_resource_rejected_before_creation(self):
        cursor = Mock()
        cursor.fetchone.return_value = (True,)
        with self.assertRaises(ValueError):
            runner.ensure_absent(cursor, 'ec_integrated_test_probe')
        self.assertEqual(cursor.execute.call_count, 1)

    def test_cleanup_does_not_drop_uncreated_database(self):
        connection = Mock()
        runner.cleanup_owned(connection, 'ec_integrated_test_probe', False, True)
        commands = connection.cursor.return_value.execute.call_args_list
        self.assertEqual(len(commands), 1)
        self.assertIn('DROP ROLE', str(commands[0]))
        self.assertNotIn('DROP DATABASE', str(commands))

    def test_cleanup_without_owned_resources(self):
        connection = Mock()
        runner.cleanup_owned(connection, 'ec_integrated_test_probe', False, False)
        connection.cursor.return_value.execute.assert_not_called()

    def test_changed_owner_blocks_cleanup(self):
        connection = Mock()
        connection.cursor.return_value.fetchone.return_value = ('another_owner',)
        with self.assertRaises(RuntimeError):
            runner.cleanup_owned(connection, 'ec_integrated_test_probe', True, True)
        self.assertEqual(connection.cursor.return_value.execute.call_count, 1)

    def test_green_summary_cannot_hide_failed_exit(self):
        log = 'odoo.tests.stats: erpec_base: 2 tests\nodoo.tests.result: 0 failed, 0 error(s) of 2 tests'
        self.assertEqual(runner.assess(log, 0, ['erpec_base']), 2)
        with self.assertRaises(ValueError):
            runner.assess(log, 1, ['erpec_base'])

    def test_empty_or_missing_module_rejected(self):
        for log in ['', 'odoo.tests.result: 0 failed, 0 error(s) of 0 tests', 'odoo.tests.result: 0 failed, 0 error(s) of 2 tests']:
            with self.assertRaises(ValueError):
                runner.assess(log, 0, ['erpec_base'])


if __name__ == '__main__':
    unittest.main()
