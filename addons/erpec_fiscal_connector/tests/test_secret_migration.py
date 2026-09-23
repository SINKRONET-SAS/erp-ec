"""DI25-05.1: la clave API del conector fiscal se guarda cifrada, nunca en claro; rotación y
recuperación probadas contra el mismo mecanismo (erpec_secrets) que ya usa erpec_payphone."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.erpec_secrets import secret_store

KEY_A = 'a' * 48
KEY_B = 'b' * 48


@tagged('post_install', '-at_install')
class SecretMigrationCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.values = {'company_id': self.env.company.id, 'base_url': 'http://127.0.0.1:3099',
                        'organization_ref': 'organizacion-sintetica', 'empresa_ref': 901,
                        'workspace_ref': 902, 'emission_point_ref': 903}

    def _connection(self, api_key='sk_test_sintetica'):
        return self.env['erpec.fiscal.connection'].sudo().create(dict(self.values, api_key=api_key))

    def _row(self, connection):
        self.env.flush_all()
        self.env.cr.execute('SELECT api_key_encrypted, api_key_loaded FROM erpec_fiscal_connection WHERE id=%s', [connection.id])
        return self.env.cr.fetchone()

    def test_api_key_always_reads_back_empty(self):
        connection = self._connection()
        connection.invalidate_recordset()
        self.assertFalse(connection.api_key)

    def test_database_never_holds_plaintext(self):
        connection = self._connection('sk_test_no_debe_verse_en_claro')
        encrypted, loaded = self._row(connection)
        self.assertTrue(encrypted.startswith('v2:'))
        self.assertNotIn('sk_test_no_debe_verse_en_claro', encrypted)
        self.assertTrue(loaded)
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='erpec_fiscal_connection' AND column_name='api_key'")
        if self.env.cr.fetchone():
            self.env.cr.execute('SELECT api_key FROM erpec_fiscal_connection WHERE id=%s', [connection.id])
            self.assertIsNone(self.env.cr.fetchone()[0])

    def test_secret_api_key_round_trips_the_exact_value(self):
        connection = self._connection('sk_test_valor_exacto')
        connection.invalidate_recordset()
        self.assertEqual(connection.sudo()._secret_api_key(), 'sk_test_valor_exacto')

    def test_writing_a_new_key_replaces_the_previous_one(self):
        connection = self._connection('sk_test_original')
        old, _loaded = self._row(connection)
        connection.write({'api_key': 'sk_live_reemplazo'})
        new, _loaded = self._row(connection)
        self.assertNotEqual(old, new)
        self.assertEqual(secret_store.decrypt(new, 'fiscal_connector:%d:api_key' % connection.id), b'sk_live_reemplazo')

    def test_tampered_value_is_rejected(self):
        connection = self._connection('sk_test_valido')
        token, _loaded = self._row(connection)
        flipped = token[:50] + ('B' if token[50] != 'B' else 'C') + token[51:]
        self.env.cr.execute('UPDATE erpec_fiscal_connection SET api_key_encrypted=%s WHERE id=%s', [flipped, connection.id])
        connection.invalidate_recordset()
        with self.assertRaises(ValidationError):
            connection.sudo()._secret_api_key()

    def test_migration_encrypts_legacy_plaintext_and_clears_the_column(self):
        connection = self._connection(api_key=False)
        self.env.flush_all()
        self.env.cr.execute('ALTER TABLE erpec_fiscal_connection ADD COLUMN IF NOT EXISTS api_key varchar')
        self.env.cr.execute('UPDATE erpec_fiscal_connection SET api_key_encrypted=NULL, api_key_loaded=FALSE, api_key=%s WHERE id=%s',
                            ['  sk_test_heredado_en_claro  ', connection.id])
        path = Path(__file__).resolve().parents[1] / 'migrations' / '18.0.1.1.0' / 'post-migration.py'
        spec = importlib.util.spec_from_file_location('fiscal_connector_migration_18_0_1_1_0', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, None)
        connection.invalidate_recordset()
        self.assertEqual(connection.sudo()._secret_api_key(), 'sk_test_heredado_en_claro')
        self.env.cr.execute('SELECT api_key FROM erpec_fiscal_connection WHERE id=%s', [connection.id])
        self.assertIsNone(self.env.cr.fetchone()[0])

    def test_rotation_wizard_reencrypts_and_connection_keeps_working(self):
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': KEY_A, 'ERPEC_SECRET_KEY_PREVIOUS': ''}):
            connection = self._connection('sk_test_para_rotar')
            old_id = secret_store.current_key_id()
            encrypted, _loaded = self._row(connection)
            self.assertEqual(secret_store.token_key_id(encrypted), old_id)
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': KEY_B, 'ERPEC_SECRET_KEY_PREVIOUS': KEY_A}):
            new_id = secret_store.current_key_id()
            wizard = self.env['erpec.secret.rotation'].create({})
            self.assertGreaterEqual(wizard.pending, 1)
            count = wizard.reencrypt_all()
            self.assertGreaterEqual(count, 1)
            encrypted, _loaded = self._row(connection)
            self.assertEqual(secret_store.token_key_id(encrypted), new_id)
            connection.invalidate_recordset()
            self.assertEqual(connection.sudo()._secret_api_key(), 'sk_test_para_rotar')
