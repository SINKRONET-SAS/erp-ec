"""Evita falsos positivos del ejecutor de auditoría, sin conexión a ninguna base."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('di25_runner', Path(__file__).with_name('verify-di25-demo-runner.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class DemoRunnerTests(unittest.TestCase):
    def report(self, **changes):
        return dict({'passed': True, 'database': 'erpec_demo', 'cases': [{}] * 32,
                     'moduleVersion': '18.0.1.12.0', 'problems': []}, **changes)

    def execute(self, report=None, returncode=0, raw=None, error=None):
        with tempfile.TemporaryDirectory(prefix='di25-auditoria-') as directory:
            output = Path(directory) / 'resultado.json'
            text = raw if raw is not None else 'DI25_AUDIT_BEGIN\n' + json.dumps(report or self.report()) + '\nDI25_AUDIT_END'
            completed = subprocess.CompletedProcess([], returncode, text, '')
            with patch.object(runner.sys, 'argv', ['auditoria', '--output', str(output)]), \
                 patch.object(runner.subprocess, 'run', return_value=completed, side_effect=error), \
                 contextlib.redirect_stdout(io.StringIO()):
                code = runner.main()
            return code, json.loads(output.read_text(encoding='utf-8'))

    def test_complete_success(self):
        code, record = self.execute()
        self.assertEqual(code, 0)
        self.assertTrue(record['passed'])
        self.assertEqual(record['processExit'], 0)

    def test_process_failure_overrides_positive_report(self):
        code, record = self.execute(returncode=1)
        self.assertEqual(code, 1)
        self.assertFalse(record['passed'])

    def test_discrepancy_overrides_zero_exit(self):
        code, record = self.execute(self.report(passed=False, problems=[{'reason': 'Entradas editadas'}]))
        self.assertEqual(code, 1)
        self.assertFalse(record['passed'])

    def test_other_database_is_rejected(self):
        code, record = self.execute(self.report(database='otra_base'))
        self.assertEqual(code, 1)
        self.assertFalse(record['passed'])

    def test_missing_report_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError, 'informe completo'):
            self.execute(raw='Solo un registro de arranque')

    def test_invalid_json_is_not_success(self):
        with self.assertRaises(ValueError):
            self.execute(raw='DI25_AUDIT_BEGIN\n{incompleto\nDI25_AUDIT_END')

    def test_timeout_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError, '180 segundos'):
            self.execute(error=subprocess.TimeoutExpired('auditoria', 180))


if __name__ == '__main__':
    unittest.main()
