"""Repara certificados cifrados por la migración 18.0.1.5.0 con el defecto de cifrar el texto base64 en lugar de los
bytes del .p12. Idempotente: solo toca los que, al descifrarse, no son un PKCS#12 (DER) válido."""
import hashlib
import logging

from odoo.addons.erpec_fiscal_sri import secret_store

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT id, p12_encrypted FROM erpec_fiscal_certificate WHERE p12_encrypted IS NOT NULL")
    for record_id, token in cr.fetchall():
        context = 'cert:%d:p12' % record_id
        current = secret_store.decrypt(token, context)
        if current[:1] == b'\x30':
            continue
        raw = secret_store.p12_bytes(current)
        cr.execute('UPDATE erpec_fiscal_certificate SET p12_encrypted=%s, p12_fingerprint=%s WHERE id=%s',
                   [secret_store.encrypt(raw, context), hashlib.sha256(raw).hexdigest(), record_id])
        _logger.info('Certificado %s reparado (bytes reales del .p12 cifrados).', record_id)
