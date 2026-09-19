"""El token de PayPhone se guarda cifrado; el texto plano no existe en la base."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.erpec_secrets import secret_store


class TestPayphoneSecretToken(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(user=self.env.ref('base.user_admin'), su=False,
                            context=dict(self.env.context, allowed_company_ids=[self.env.company.id], no_reset_password=True))
        self.provider = self.env['erpec.payphone.provider'].create({
            'company_id': self.env.company.id, 'token': 'TOKEN-SINTETICO-SECRETO', 'store_id': 'STORE-SINTETICO',
            'test_acknowledged': True, 'public_url': 'https://pruebas.sinkronet.com.ec'})

    def _row(self):
        self.env.flush_all()
        self.env.cr.execute('SELECT token_encrypted, token_loaded FROM erpec_payphone_provider WHERE id=%s', [self.provider.id])
        return self.env.cr.fetchone()

    def test_database_never_holds_the_plaintext_token(self):
        encrypted, loaded = self._row()
        self.assertTrue(encrypted.startswith('v1:'))
        self.assertNotIn('SECRETO', encrypted)
        self.assertTrue(loaded)
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='erpec_payphone_provider' AND column_name='token'")
        if self.env.cr.fetchone():
            self.env.cr.execute('SELECT token FROM erpec_payphone_provider WHERE id=%s', [self.provider.id])
            self.assertIsNone(self.env.cr.fetchone()[0])

    def test_token_reads_back_empty_and_status_still_ready(self):
        self.provider.invalidate_recordset()
        self.assertFalse(self.provider.token)
        self.assertTrue(self.provider.token_loaded)
        self.assertIn('Lista', self.provider.status)

    def test_request_sends_the_decrypted_token(self):
        response = type('R', (), {'status_code': 200, 'json': lambda self: {'ok': 1}})()
        with patch('odoo.addons.erpec_payphone.models.payphone.requests.post', return_value=response) as post:
            self.provider._request('Prepare', {'amount': 100})
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer TOKEN-SINTETICO-SECRETO')

    def test_replacing_the_token_encrypts_the_new_value(self):
        old, _loaded = self._row()
        self.provider.write({'token': 'OTRO-TOKEN-SINTETICO'})
        new, _loaded = self._row()
        self.assertNotEqual(old, new)
        self.assertEqual(secret_store.decrypt(new, 'payphone:%d:token' % self.provider.id), b'OTRO-TOKEN-SINTETICO')

    def test_tampered_token_is_rejected(self):
        token, _loaded = self._row()
        flipped = token[:40] + ('B' if token[40] != 'B' else 'C') + token[41:]
        self.env.cr.execute('UPDATE erpec_payphone_provider SET token_encrypted=%s WHERE id=%s', [flipped, self.provider.id])
        self.provider.invalidate_recordset()
        with self.assertRaisesRegex(ValidationError, 'descifrar'):
            self.provider._bearer_token()

    def test_migration_encrypts_the_legacy_plaintext_column(self):
        self.env.flush_all()
        self.env.cr.execute('ALTER TABLE erpec_payphone_provider ADD COLUMN IF NOT EXISTS token varchar')
        self.env.cr.execute('UPDATE erpec_payphone_provider SET token_encrypted=NULL, token_loaded=FALSE, token=%s WHERE id=%s', ['  TOKEN-LEGADO  ', self.provider.id])
        path = Path(__file__).resolve().parents[1] / 'migrations' / '18.0.1.1.0' / 'post-migration.py'
        spec = importlib.util.spec_from_file_location('erpec_payphone_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, None)
        self.provider.invalidate_recordset()
        self.assertEqual(self.provider._bearer_token(), 'TOKEN-LEGADO')
        self.env.cr.execute('SELECT token FROM erpec_payphone_provider WHERE id=%s', [self.provider.id])
        self.assertIsNone(self.env.cr.fetchone()[0])
