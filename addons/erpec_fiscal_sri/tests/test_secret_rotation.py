"""El asistente de rotación re-cifra los secretos reales (certificado) y no modifica nada si alguno no se puede descifrar."""
import base64
import os
import tempfile
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import config

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from .. import secret_store

KEY_A = 'a' * 48
KEY_B = 'b' * 48


@tagged('post_install', '-at_install')
class SecretRotationCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company.with_context(no_vat_validation=True).write({'vat': ISSUER_RUC})
        self.p12, _key, _cert, _now = _build_certificate()

    def _certificate(self):
        certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(self.p12), 'p12_password': P12_PASSWORD.decode()})
        self.env.flush_all()
        return certificate

    def _kids(self, certificate):
        self.env.cr.execute('SELECT p12_encrypted, p12_password_encrypted FROM erpec_fiscal_certificate WHERE id=%s', [certificate.id])
        return [secret_store.token_key_id(token) for token in self.env.cr.fetchone()]

    def test_registered_fields_are_re_encrypted_with_the_current_key(self):
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': KEY_A, 'ERPEC_SECRET_KEY_PREVIOUS': ''}):
            certificate = self._certificate()
            old_id = secret_store.current_key_id()
            self.assertEqual(self._kids(certificate), [old_id, old_id])
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': KEY_B, 'ERPEC_SECRET_KEY_PREVIOUS': KEY_A}):
            new_id = secret_store.current_key_id()
            wizard = self.env['erpec.secret.rotation'].create({})
            self.assertGreaterEqual(wizard.pending, 2)
            self.assertIn('%s = ' % old_id, wizard.inventory)
            count = wizard.reencrypt_all()
            self.assertGreaterEqual(count, 2)
            self.assertEqual(self._kids(certificate), [new_id, new_id])
            certificate.invalidate_recordset()
            self.assertEqual(certificate._signing_material(), (self.p12, P12_PASSWORD))
            self.assertEqual(self.env['erpec.secret.rotation'].create({}).pending, 0)
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': KEY_B, 'ERPEC_SECRET_KEY_PREVIOUS': ''}):
            certificate.invalidate_recordset()
            self.assertEqual(certificate._signing_material(), (self.p12, P12_PASSWORD))

    def test_nothing_is_modified_when_a_secret_cannot_be_decrypted(self):
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': KEY_A, 'ERPEC_SECRET_KEY_PREVIOUS': ''}):
            certificate = self._certificate()
            before = self._kids(certificate)
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': KEY_B, 'ERPEC_SECRET_KEY_PREVIOUS': ''}):
            with self.assertRaisesRegex(ValidationError, 'No se re-cifró nada'):
                self.env['erpec.secret.rotation'].create({}).reencrypt_all()
        self.assertEqual(self._kids(certificate), before)

    def test_generate_and_reencrypt_rotates_the_key_file_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ.pop('ERPEC_SECRET_KEY', None)
            with patch.dict(os.environ, {'ERPEC_SECRET_KEY_PREVIOUS': ''}), \
                    patch.dict(config.options, {'data_dir': directory, 'erpec_secret_key': '', 'erpec_secret_key_previous': ''}):
                os.environ.pop('ERPEC_SECRET_KEY', None)
                certificate = self._certificate()
                old_id = secret_store.current_key_id()
                wizard = self.env['erpec.secret.rotation'].create({})
                wizard.action_generate_and_reencrypt()
                new_id = secret_store.current_key_id()
                self.assertNotEqual(old_id, new_id)
                self.assertEqual(self._kids(certificate), [new_id, new_id])
                certificate.invalidate_recordset()
                self.assertEqual(certificate._signing_material(), (self.p12, P12_PASSWORD))

    def test_only_system_administrators_can_rotate(self):
        user = new_test_user(self.env, login='rotation_accountant', groups='account.group_account_user')
        with self.assertRaises(AccessError):
            self.env['erpec.secret.rotation'].with_user(user).create({})
        wizard = self.env['erpec.secret.rotation'].create({})
        with self.assertRaises(AccessError):
            wizard.with_user(user).reencrypt_all()
