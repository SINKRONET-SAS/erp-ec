"""El certificado .p12 y su contraseña se guardan cifrados en reposo; el texto plano no existe en la base."""
import base64
import os
import tempfile
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import config

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from .. import secret_store


@tagged('post_install', '-at_install')
class SecretStoreCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company.with_context(no_vat_validation=True).write({'vat': ISSUER_RUC})
        self.p12, _key, _cert, _now = _build_certificate()
        self.certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(self.p12), 'p12_password': P12_PASSWORD.decode()})

    def _row(self):
        self.env.flush_all()
        self.env.cr.execute('SELECT p12_encrypted, p12_password_encrypted, p12_loaded, p12_fingerprint FROM erpec_fiscal_certificate WHERE id=%s',
                            [self.certificate.id])
        return self.env.cr.fetchone()

    def _legacy_plaintext_columns(self):
        """Columnas de texto plano de versiones anteriores: no deben existir (base nueva) o deben estar vacías (base migrada)."""
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='erpec_fiscal_certificate' "
                            "AND column_name IN ('p12_file','p12_password')")
        return [row[0] for row in self.env.cr.fetchall()]

    def test_database_never_holds_plaintext(self):
        encrypted, password_encrypted, loaded, fingerprint = self._row()
        self.assertTrue(encrypted.startswith('v2:') and password_encrypted.startswith('v2:'))
        for column in self._legacy_plaintext_columns():
            self.env.cr.execute('SELECT %s FROM erpec_fiscal_certificate WHERE id=%%s' % column, [self.certificate.id])
            self.assertIsNone(self.env.cr.fetchone()[0])
        self.assertNotIn(P12_PASSWORD.decode(), password_encrypted)
        self.assertNotIn(base64.b64encode(self.p12).decode()[:40], encrypted)
        self.assertTrue(loaded)
        self.assertEqual(len(fingerprint), 64)

    def test_inputs_always_read_back_empty(self):
        self.certificate.invalidate_recordset()
        self.assertFalse(self.certificate.p12_file)
        self.assertFalse(self.certificate.p12_password)
        self.assertFalse(self.certificate.sudo().p12_file)
        self.assertTrue(self.certificate.p12_loaded)

    def test_signing_material_round_trips(self):
        raw, password = self.certificate._signing_material()
        self.assertEqual(raw, self.p12)
        self.assertEqual(password, P12_PASSWORD)

    def test_verify_and_test_signature_work_with_encrypted_storage(self):
        self.certificate.action_verify()
        self.assertTrue(self.certificate.verified)
        self.certificate.action_test_signature()
        self.assertTrue(self.certificate.signature_tested)

    def test_replacing_the_file_requires_verifying_again(self):
        self.certificate.action_verify()
        p12, _key, _cert, _now = _build_certificate()
        self.certificate.write({'p12_file': base64.b64encode(p12)})
        self.assertFalse(self.certificate.verified)

    def test_tampered_or_moved_ciphertext_is_rejected(self):
        token = self._row()[0]
        flipped = token[:50] + ('B' if token[50] != 'B' else 'C') + token[51:]
        self.env.cr.execute('UPDATE erpec_fiscal_certificate SET p12_encrypted=%s WHERE id=%s', [flipped, self.certificate.id])
        self.certificate.invalidate_recordset()
        with self.assertRaisesRegex(ValidationError, 'descifrar'):
            self.certificate._signing_material()

    def test_ciphertext_is_bound_to_its_context(self):
        token = secret_store.encrypt(b'secreto', 'cert:1:p12')
        self.assertEqual(secret_store.decrypt(token, 'cert:1:p12'), b'secreto')
        with self.assertRaises(secret_store.SecretError):
            secret_store.decrypt(token, 'cert:2:p12')
        with self.assertRaises(secret_store.SecretError):
            secret_store.decrypt(token, 'cert:1:password')
        self.assertNotEqual(secret_store.encrypt(b'secreto', 'cert:1:p12'), token)

    def test_key_comes_from_environment_and_never_from_the_database(self):
        token = secret_store.encrypt(b'dato', 'ctx')
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': 'k' * 40}):
            with self.assertRaises(secret_store.SecretError):
                secret_store.decrypt(token, 'ctx')
            self.assertEqual(secret_store.decrypt(secret_store.encrypt(b'otro', 'ctx'), 'ctx'), b'otro')
        with patch.dict(os.environ, {'ERPEC_SECRET_KEY': 'corta'}):
            with self.assertRaisesRegex(secret_store.SecretError, 'al menos'):
                secret_store.encrypt(b'x', 'ctx')

    def test_key_file_is_generated_once_in_the_data_directory(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ERPEC_SECRET_KEY', None)
            with patch.dict(config.options, {'data_dir': directory, 'erpec_secret_key': ''}):
                token = secret_store.encrypt(b'dato', 'ctx')
                path = os.path.join(directory, secret_store.KEY_FILE)
                self.assertTrue(os.path.exists(path))
                first = open(path).read()
                self.assertEqual(secret_store.decrypt(token, 'ctx'), b'dato')
                secret_store.encrypt(b'otro', 'ctx')
                self.assertEqual(open(path).read(), first)

    def test_oversized_file_is_still_rejected(self):
        certificate = self.env['erpec.fiscal.certificate'].sudo()
        other = self.env['res.company'].create({'name': 'Otra empresa cifrado'})
        with self.assertRaisesRegex(ValidationError, 'tamaño máximo'):
            certificate.create({'company_id': other.id, 'p12_file': base64.b64encode(b'0' * 300000), 'p12_password': 'x'})

    def test_legacy_binary_column_values_are_normalized_to_real_p12_bytes(self):
        self.assertEqual(secret_store.p12_bytes(self.p12), self.p12)
        self.assertEqual(secret_store.p12_bytes(base64.b64encode(self.p12)), self.p12)
        self.assertEqual(secret_store.p12_bytes(memoryview(base64.b64encode(self.p12))), self.p12)
        with self.assertRaises(Exception):
            secret_store.p12_bytes(b'esto no es base64 ni un p12 !!!')

    def _run_migration(self, version):
        import importlib.util
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / 'migrations' / version / 'post-migration.py'
        spec = importlib.util.spec_from_file_location('erpec_migration_' + version.replace('.', '_'), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, None)
        self.certificate.invalidate_recordset()

    def test_migration_encrypts_legacy_plaintext_columns_with_real_p12_bytes(self):
        self.env.flush_all()
        self.env.cr.execute('ALTER TABLE erpec_fiscal_certificate ADD COLUMN p12_file bytea, ADD COLUMN p12_password varchar')
        # Así guarda Odoo una columna Binary sin adjunto: el valor en base64 como bytes.
        self.env.cr.execute('UPDATE erpec_fiscal_certificate SET p12_encrypted=NULL, p12_password_encrypted=NULL, p12_loaded=FALSE, '
                            'p12_file=%s, p12_password=%s WHERE id=%s', [base64.b64encode(self.p12), P12_PASSWORD.decode(), self.certificate.id])
        self._run_migration('18.0.1.5.0')
        raw, password = self.certificate._signing_material()
        self.assertEqual(raw, self.p12)
        self.assertEqual(password, P12_PASSWORD)
        self.env.cr.execute('SELECT p12_file, p12_password FROM erpec_fiscal_certificate WHERE id=%s', [self.certificate.id])
        self.assertEqual(self.env.cr.fetchone(), (None, None))
        self.certificate.action_verify()
        self.assertTrue(self.certificate.verified)

    def test_repair_migration_fixes_certificates_encrypted_from_base64_text(self):
        wrong = secret_store.encrypt(base64.b64encode(self.p12), self.certificate._secret_context('p12'))
        self.env.flush_all()
        self.env.cr.execute('UPDATE erpec_fiscal_certificate SET p12_encrypted=%s WHERE id=%s', [wrong, self.certificate.id])
        self.certificate.invalidate_recordset()
        self.assertNotEqual(self.certificate._signing_material()[0], self.p12)
        self._run_migration('18.0.1.5.1')
        self.assertEqual(self.certificate._signing_material()[0], self.p12)
        self._run_migration('18.0.1.5.1')
        self.assertEqual(self.certificate._signing_material()[0], self.p12)
