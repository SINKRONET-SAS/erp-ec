"""Cifra las claves API del conector fiscal guardadas en claro (columna api_key) y borra el texto plano."""
import logging

from odoo.addons.erpec_secrets import secret_store

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name='erpec_fiscal_connection' AND column_name='api_key'")
    if not cr.fetchone():
        return
    cr.execute("SELECT id, api_key FROM erpec_fiscal_connection WHERE api_key IS NOT NULL AND api_key <> ''")
    for record_id, api_key in cr.fetchall():
        cr.execute('UPDATE erpec_fiscal_connection SET api_key_encrypted=%s, api_key_loaded=TRUE WHERE id=%s',
                   [secret_store.encrypt(api_key.strip().encode('utf-8'), 'fiscal_connector:%d:api_key' % record_id), record_id])
        _logger.info('Clave API del conector fiscal %s cifrada en reposo.', record_id)
    cr.execute('UPDATE erpec_fiscal_connection SET api_key=NULL WHERE api_key IS NOT NULL')
