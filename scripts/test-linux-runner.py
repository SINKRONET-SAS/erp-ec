"""Prueba el contrato de salida del ejecutor Linux con Docker simulado, sin contenedores."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else '/bin/bash'
FAKE = """#!/usr/bin/env bash
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
                        'docker() { bash "$FAKE_DOCKER" "$@"; }; export -f docker; bash deployment/linux/run-tests.sh erpec_base'],
                        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
