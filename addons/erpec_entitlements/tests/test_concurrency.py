"""Ejecuta la concurrencia en un proceso sin los bloqueos globales del arnés Odoo."""
import configparser
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import odoo
from odoo.tests import TransactionCase, tagged
from odoo.tools import config


@tagged('post_install', '-at_install')
class EntitlementConcurrencyCase(TransactionCase):
    def test_both_orders_with_real_independent_transactions(self):
        if not (self.env.cr.dbname.startswith('ec_integrated_test_') or self.env.cr.dbname == 'linux_test'):
            raise AssertionError('Se requiere una base desechable del ejecutor integrado.')
        with tempfile.TemporaryDirectory(prefix='cm28-concurrency-') as directory:
            options = {key: str(config[key]) for key in ('db_host', 'db_port', 'db_user', 'db_password', 'addons_path', 'data_dir') if config[key]}
            options.update(db_name=self.env.cr.dbname, max_cron_threads='0', list_db='False',
                           logfile=str(Path(directory) / 'probe.log'))
            settings = configparser.ConfigParser(interpolation=None)
            settings['options'] = options
            filename = Path(directory) / 'probe.conf'
            with filename.open('w', encoding='utf-8') as handle:
                settings.write(handle)
            executable = Path(odoo.__file__).resolve().parents[1] / 'odoo-bin'
            code = 'from odoo.addons.erpec_entitlements.tests.concurrency_probe import run\nrun(env)\n'
            result = subprocess.run([sys.executable, str(executable), 'shell', '-c', str(filename), '--no-http'],
                                    input=code, capture_output=True, text=True, encoding='utf-8', timeout=300,
                                    env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})
            self.assertEqual(result.returncode, 0, result.stderr[-5000:])
            self.assertIn('CM28_CONCURRENCY_OK', result.stdout)
