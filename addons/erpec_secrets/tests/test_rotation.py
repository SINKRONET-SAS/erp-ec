"""Rotación de la clave maestra: identificador de clave, claves anteriores y rotación del archivo de clave."""
import os
import tempfile
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.tools import config

from odoo.addons.erpec_secrets import secret_store

KEY_A = 'a' * 48
KEY_B = 'b' * 48
KEY_C = 'c' * 48


@tagged('post_install', '-at_install')
class RotationCase(TransactionCase):
    def _env(self, current, previous=''):
        values = {'ERPEC_SECRET_KEY': current, 'ERPEC_SECRET_KEY_PREVIOUS': previous}
        return patch.dict(os.environ, {k: v for k, v in values.items()})

    def test_new_format_carries_the_key_id(self):
        with self._env(KEY_A):
            token = secret_store.encrypt(b'dato', 'ctx')
            kid = secret_store.current_key_id()
        self.assertTrue(token.startswith('v2:%s:' % kid))
        self.assertEqual(secret_store.token_key_id(token), kid)

    def test_legacy_v1_tokens_are_still_readable(self):
        with self._env(KEY_A):
            body = secret_store._fernet('ctx').encrypt(b'antiguo').decode('ascii')
            self.assertEqual(secret_store.decrypt('v1:' + body, 'ctx'), b'antiguo')
            self.assertEqual(secret_store.token_key_id('v1:' + body), 'v1')

    def test_previous_key_decrypts_during_rotation_and_new_encryptions_use_the_current_key(self):
        with self._env(KEY_A):
            old_token = secret_store.encrypt(b'dato', 'ctx')
            old_id = secret_store.current_key_id()
        with self._env(KEY_B, KEY_A):
            self.assertEqual(secret_store.decrypt(old_token, 'ctx'), b'dato')
            new_token = secret_store.encrypt(b'dato', 'ctx')
            self.assertNotEqual(secret_store.token_key_id(new_token), old_id)
            self.assertEqual(secret_store.token_key_id(new_token), secret_store.current_key_id())
            self.assertEqual(len(secret_store.known_keys()), 2)

    def test_missing_previous_key_gives_a_clear_error_naming_the_key_id(self):
        with self._env(KEY_A):
            token = secret_store.encrypt(b'dato', 'ctx')
            old_id = secret_store.current_key_id()
        with self._env(KEY_B):
            with self.assertRaisesRegex(secret_store.SecretError, old_id):
                secret_store.decrypt(token, 'ctx')

    def test_several_previous_keys_are_supported(self):
        with self._env(KEY_A):
            first = secret_store.encrypt(b'uno', 'ctx')
        with self._env(KEY_B, KEY_A):
            second = secret_store.encrypt(b'dos', 'ctx')
        with self._env(KEY_C, '%s,%s' % (KEY_B, KEY_A)):
            self.assertEqual(secret_store.decrypt(first, 'ctx'), b'uno')
            self.assertEqual(secret_store.decrypt(second, 'ctx'), b'dos')

    def test_key_file_rotation_keeps_the_old_key_only_for_decrypting(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('ERPEC_SECRET_KEY', None)
                os.environ.pop('ERPEC_SECRET_KEY_PREVIOUS', None)
                with patch.dict(config.options, {'data_dir': directory, 'erpec_secret_key': '', 'erpec_secret_key_previous': ''}):
                    token = secret_store.encrypt(b'dato', 'ctx')
                    old_id = secret_store.current_key_id()
                    new_id = secret_store.rotate_key_file()
                    self.assertNotEqual(new_id, old_id)
                    self.assertEqual(secret_store.current_key_id(), new_id)
                    self.assertEqual(secret_store.decrypt(token, 'ctx'), b'dato')
                    self.assertEqual(secret_store.token_key_id(secret_store.encrypt(b'x', 'ctx')), new_id)
                    self.assertTrue(os.path.exists(os.path.join(directory, secret_store.PREVIOUS_FILE)))

    def test_key_file_rotation_is_refused_when_the_key_comes_from_the_environment(self):
        with self._env(KEY_A):
            with self.assertRaisesRegex(secret_store.SecretError, 'ERPEC_SECRET_KEY_PREVIOUS'):
                secret_store.rotate_key_file()

    def test_short_keys_are_rejected(self):
        with self._env('corta'):
            with self.assertRaisesRegex(secret_store.SecretError, 'al menos'):
                secret_store.encrypt(b'x', 'ctx')
