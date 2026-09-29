"""Prueba el contrato de salida del ejecutor Linux con Docker simulado, sin contenedores."""
import os
import importlib.util
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else '/bin/bash'
FAKE = """#!/usr/bin/env bash
if [ "$1" = "exec" ] && [[ "$*" == *"pg_isready"* ]] && [[ "$*" != *"-h 127.0.0.1"* ]]; then
  exit 1
fi
if [ "$1" = "run" ] && [[ "$*" == *"--entrypoint"* ]]; then
  if [ "$CASE" != "missing" ]; then echo "odoo.tests.stats: erpec_base: 2 tests"; fi
  if [ "$CASE" = "zero" ]; then
    echo "odoo.tests.result: 0 failed, 0 error(s) of 0 tests"
  else
    echo "odoo.tests.result: 0 failed, 0 error(s) of 2 tests"
  fi
  if [ "$CASE" = "exit" ]; then exit 7; fi
fi
exit 0
"""


class LinuxRunnerContract(unittest.TestCase):
    def test_real_shell_preserves_exit_and_requires_coverage(self):
        (ROOT / '.cache').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='di25-runner-', dir=ROOT / '.cache') as directory:
            fake = Path(directory) / 'docker.sh'
            fake.write_text(FAKE, encoding='utf-8', newline='\n')
            for case, expected in [('ok', 0), ('exit', 1), ('zero', 1), ('missing', 1)]:
                with self.subTest(case=case):
                    env = dict(os.environ, CASE=case, FAKE_DOCKER=fake.as_posix(), ERPEC_SKIP_BUILD='1')
                    result = subprocess.run([BASH, '-c',
                        'docker() { bash "$FAKE_DOCKER" "$@"; }; sleep() { :; }; export -f docker sleep; bash deployment/linux/run-tests.sh erpec_base'],
                        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


class PostgresReadiness(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('verify_linux_readiness',ROOT/'scripts/verify-linux.py')
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_waits_for_tcp_instead_of_accepting_temporary_socket(self):
        def probe(*args,**kwargs):
            # El socket temporal ya respondería, pero TCP solo acepta tras el reinicio.
            tcp='-h' in args and args[args.index('-h')+1]=='127.0.0.1'
            return SimpleNamespace(returncode=0 if not tcp or docker_mock.call_count>=3 else 1)
        with patch.object(self.module,'docker',side_effect=probe) as docker_mock, patch.object(self.module.time,'sleep') as sleep_mock:
            self.module.wait_postgres('ensayo')
        self.assertEqual(docker_mock.call_count,3)
        self.assertEqual(sleep_mock.call_count,2)

    def test_unavailable_tcp_fails_after_bounded_wait(self):
        with patch.object(self.module,'docker',return_value=SimpleNamespace(returncode=1)) as docker_mock, patch.object(self.module.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'TCP definitivo'):
                self.module.wait_postgres('ensayo')
        self.assertEqual(docker_mock.call_count,30)


if __name__ == '__main__':
    unittest.main()
