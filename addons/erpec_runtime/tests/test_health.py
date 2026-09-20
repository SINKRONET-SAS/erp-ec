"""Salud del runtime Linux: solo responde 200 con la identidad de esta instancia lista."""
import os
from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

INSTANCE = 'a' * 32


@tagged('post_install', '-at_install')
class TestHealth(HttpCase):
    def setUp(self):
        super().setUp()
        # runtime.py crea esta tabla al inicializar; en la prueba se crea dentro de la transacción.
        self.env.cr.execute('CREATE TABLE erpec_runtime_identity (singleton boolean PRIMARY KEY CHECK(singleton), instance varchar(32) NOT NULL, profile varchar(16) NOT NULL, ready boolean NOT NULL DEFAULT false)')

    def _set_identity(self, instance, ready):
        self.env.cr.execute('INSERT INTO erpec_runtime_identity(singleton,instance,profile,ready) VALUES(true,%s,%s,%s)', [instance, 'customer', ready])

    def _health(self):
        return self.url_open('/erpec/health')

    def test_ready_instance_passes(self):
        self._set_identity(INSTANCE, True)
        with patch.dict(os.environ, {'ERPEC_INSTANCE_ID': INSTANCE}):
            response = self._health()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'pass'})
        self.assertEqual(response.headers.get('Cache-Control'), 'no-store')

    def test_unfinished_initialization_fails(self):
        self._set_identity(INSTANCE, False)
        with patch.dict(os.environ, {'ERPEC_INSTANCE_ID': INSTANCE}):
            response = self._health()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'fail'})

    def test_database_of_another_instance_fails(self):
        self._set_identity('b' * 32, True)
        with patch.dict(os.environ, {'ERPEC_INSTANCE_ID': INSTANCE}):
            response = self._health()
        self.assertEqual(response.status_code, 503)

    def test_missing_identity_row_fails(self):
        with patch.dict(os.environ, {'ERPEC_INSTANCE_ID': INSTANCE}):
            response = self._health()
        self.assertEqual(response.status_code, 503)
