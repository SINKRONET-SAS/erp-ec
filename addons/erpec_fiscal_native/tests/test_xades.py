"""Pruebas de xades.py: firma y verificación XAdES-BES con certificado sintético autofirmado
(no un certificado real emitido por una entidad certificadora ecuatoriana)."""
import datetime
from odoo.tests.common import BaseCase
from odoo.addons.erpec_fiscal_native import xades

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

ISSUER_RUC = '1793235327001'
P12_PASSWORD = b'ensayo-sintetico'


def _build_certificate(ruc=ISSUER_RUC, key_size=2048, days_valid=365, with_key_usage=True, not_before_offset=0):
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    now = datetime.datetime.now(datetime.timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'SINKRONET S.A.S.'),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, ruc),
    ])
    builder = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(
        now + datetime.timedelta(days=not_before_offset)).not_valid_after(now + datetime.timedelta(days=days_valid))
    if with_key_usage:
        builder = builder.add_extension(
            x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                          data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False,
                          encipher_only=False, decipher_only=False), critical=True)
    cert = builder.sign(key, hashes.SHA256())
    p12 = pkcs12.serialize_key_and_certificates(b'ensayo', key, cert, None,
        serialization.BestAvailableEncryption(P12_PASSWORD))
    return p12, key, cert, now


FACTURA_XML = (b'<factura id="comprobante" version="2.1.0"><infoTributaria><ruc>' + ISSUER_RUC.encode() +
               b'</ruc></infoTributaria></factura>')


class TestXades(BaseCase):
    def test_sign_and_verify_round_trip(self):
        p12, _key, cert, now = _build_certificate()
        signed = xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=now)
        self.assertIn(b'<ds:Signature', signed)
        self.assertIn(b'xades:QualifyingProperties', signed)
        self.assertTrue(xades.verify(signed, cert))

    def test_tampered_document_fails_verification(self):
        p12, _key, cert, now = _build_certificate()
        signed = xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=now)
        tampered = signed.replace(b'1793235327001', b'1793235327002', 1)
        with self.assertRaises(ValueError):
            xades.verify(tampered, cert)

    def test_wrong_password_is_rejected(self):
        p12, _key, _cert, now = _build_certificate()
        with self.assertRaises(ValueError):
            xades.sign(FACTURA_XML, p12, b'contrasena-incorrecta', ISSUER_RUC, now=now)

    def test_ruc_mismatch_is_rejected(self):
        p12, _key, _cert, now = _build_certificate(ruc='0193235327001')
        with self.assertRaises(ValueError):
            xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=now)

    def test_expired_certificate_is_rejected(self):
        p12, _key, _cert, now = _build_certificate(days_valid=1)
        future = now + datetime.timedelta(days=10)
        with self.assertRaises(ValueError):
            xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=future)

    def test_weak_key_is_rejected(self):
        p12, _key, _cert, now = _build_certificate(key_size=1024)
        with self.assertRaises(ValueError):
            xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=now)

    def test_missing_key_usage_is_rejected(self):
        p12, _key, _cert, now = _build_certificate(with_key_usage=False)
        with self.assertRaises(ValueError):
            xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=now)

    def test_already_signed_document_is_rejected(self):
        p12, _key, _cert, now = _build_certificate()
        signed = xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=now)
        with self.assertRaises(ValueError):
            xades.sign(signed, p12, P12_PASSWORD, ISSUER_RUC, now=now)

    def test_verify_with_different_certificate_fails(self):
        p12, _key, _cert, now = _build_certificate()
        signed = xades.sign(FACTURA_XML, p12, P12_PASSWORD, ISSUER_RUC, now=now)
        _p12_other, _key_other, other_cert, _now_other = _build_certificate()
        with self.assertRaises(ValueError):
            xades.verify(signed, other_cert)

    def test_rejects_dtd(self):
        malicious = b'<!DOCTYPE factura [<!ENTITY x "y">]><factura id="comprobante"/>'
        with self.assertRaises(ValueError):
            xades.parse_xml(malicious)

    def test_rejects_duplicate_ids(self):
        malicious = b'<factura id="comprobante"><a Id="x"/><b Id="x"/></factura>'
        with self.assertRaises(ValueError):
            xades.parse_xml(malicious)
