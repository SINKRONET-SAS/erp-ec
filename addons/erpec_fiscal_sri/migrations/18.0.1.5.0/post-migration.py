"""Cifra los certificados que se guardaron en claro (columnas p12_file y p12_password) y borra el texto plano."""
import hashlib
import logging

from odoo.addons.erpec_fiscal_sri import secret_store

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='erpec_fiscal_certificate' AND column_name IN ('p12_file','p12_password')")
    if {row[0] for row in cr.fetchall()} != {'p12_file', 'p12_password'}:
        return
    cr.execute("SELECT id, p12_file, p12_password FROM erpec_fiscal_certificate WHERE p12_file IS NOT NULL OR p12_password IS NOT NULL")
    for record_id, raw, password in cr.fetchall():
        values = {}
        if raw:
            raw = secret_store.p12_bytes(raw)
            values.update(p12_encrypted=secret_store.encrypt(raw, 'cert:%d:p12' % record_id), p12_loaded=True, p12_fingerprint=hashlib.sha256(raw).hexdigest())
        if password:
            values['p12_password_encrypted'] = secret_store.encrypt(password.encode('utf-8'), 'cert:%d:password' % record_id)
        if values:
            assignments = ', '.join('%s=%%s' % name for name in values)
            cr.execute('UPDATE erpec_fiscal_certificate SET %s WHERE id=%%s' % assignments, list(values.values()) + [record_id])
        cr.execute('UPDATE erpec_fiscal_certificate SET p12_file=NULL, p12_password=NULL WHERE id=%s', [record_id])
        _logger.info('Certificado %s cifrado en reposo y texto plano eliminado.', record_id)
