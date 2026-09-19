"""Cifra los tokens de PayPhone guardados en claro (columna token) y borra el texto plano."""
import logging

from odoo.addons.erpec_secrets import secret_store

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name='erpec_payphone_provider' AND column_name='token'")
    if not cr.fetchone():
        return
    cr.execute("SELECT id, token FROM erpec_payphone_provider WHERE token IS NOT NULL AND token <> ''")
    for record_id, token in cr.fetchall():
        cr.execute('UPDATE erpec_payphone_provider SET token_encrypted=%s, token_loaded=TRUE WHERE id=%s',
                   [secret_store.encrypt(token.strip().encode('utf-8'), 'payphone:%d:token' % record_id), record_id])
        _logger.info('Token PayPhone %s cifrado en reposo.', record_id)
    cr.execute('UPDATE erpec_payphone_provider SET token=NULL WHERE token IS NOT NULL')
