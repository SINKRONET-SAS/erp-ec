"""Ensayo criptográfico aislado; no usa el certificado del emisor ni transmite al SRI."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import hashlib
import unittest
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'addons/erpec_fiscal_native/xades.py'
spec=importlib.util.spec_from_file_location('xades',SOURCE)
xades=importlib.util.module_from_spec(spec);spec.loader.exec_module(xades)

class SignatureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.now=datetime.now(timezone.utc)
        cls.ruc='1700000000001'
        cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Certificado sintético de ensayo'),
                        x509.NameAttribute(NameOID.SERIAL_NUMBER,'1700000000-ENSAYO')])
        cls.cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(cls.key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(cls.now-timedelta(days=1))
            .not_valid_after(cls.now+timedelta(days=1))
            .add_extension(x509.KeyUsage(True,True,False,False,False,False,False,False,False),critical=True)
            .sign(cls.key,hashes.SHA256()))
        cls.p12=pkcs12.serialize_key_and_certificates(b'ensayo',cls.key,cls.cert,None,
            serialization.BestAvailableEncryption(b'clave-sintetica'))
        cls.xml=('<factura id="comprobante" version="2.1.0"><infoTributaria><ruc>'+cls.ruc+
                 '</ruc></infoTributaria><infoFactura><importeTotal>115.00</importeTotal></infoFactura></factura>').encode()
    def signed(self):
        return xades.sign(self.xml,self.p12,b'clave-sintetica',self.ruc,now=self.now)
    def test_signature_and_all_references(self):
        self.assertTrue(xades.verify(self.signed(),self.cert))
    def test_changed_amount(self):
        with self.assertRaises(ValueError):
            xades.verify(self.signed().replace(b'115.00',b'999.00'),self.cert)
    def test_changed_properties(self):
        signed=self.signed().replace('Factura electrónica'.encode(),'Factura alterada'.encode())
        with self.assertRaises(ValueError):xades.verify(signed,self.cert)
    def test_changed_signature(self):
        root=xades.parse_xml(self.signed())
        root.find('.//ds:SignatureValue',xades.NS).text=xades.b64(b'0'*256)
        from cryptography.exceptions import InvalidSignature
        with self.assertRaises(InvalidSignature):xades.verify(xades.etree.tostring(root),self.cert)
    def test_wrong_password(self):
        with self.assertRaises(ValueError):xades.sign(self.xml,self.p12,b'otra',self.ruc)
    def test_expired_certificate(self):
        with self.assertRaises(ValueError):
            xades.sign(self.xml,self.p12,b'clave-sintetica',self.ruc,now=self.now+timedelta(days=2))
    def test_wrong_issuer(self):
        with self.assertRaises(ValueError):
            xades.sign(self.xml.replace(self.ruc.encode(),b'1711111111001'),self.p12,b'clave-sintetica','1711111111001')
    def test_duplicate_id(self):
        with self.assertRaises(ValueError):
            xades.parse_xml(self.xml.replace(b'<infoFactura>',b'<infoFactura Id="comprobante">'))
    def test_entities_rejected(self):
        with self.assertRaises(ValueError):
            xades.parse_xml(b'<!DOCTYPE factura [<!ENTITY x SYSTEM "file:///private">]><factura>&x;</factura>')
    def test_signing_twice_rejected(self):
        with self.assertRaises(ValueError):
            xades.sign(self.signed(),self.p12,b'clave-sintetica',self.ruc)

before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SignatureCase))
assert before==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'sourceSha256':before,'testedAt':datetime.now(timezone.utc).isoformat(),
        'syntheticCertificate':True,'realIssuerCertificateUsed':False,'sriSubmission':False,
        'scope':'Firma y verificación del motor aislado; sin homologación SRI ni verificador independiente'}
text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
assert text.encode('utf-8').decode('utf-8')==text
(ROOT/'.cache/windows/xades-local-result.json').write_text(text,encoding='utf-8',newline='\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
