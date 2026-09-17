"""Pruebas del autoservicio de carga del certificado .p12 (erpec.fiscal.certificate): permiso
ampliado a account.group_account_user (no solo base.group_system), vista previa sin persistir,
límite de tamaño, catálogo de entidades certificadoras confiables, límite de intentos de
verificación y prueba de firma real -- adaptado de sinkroniq-mobile
(backend/src/services/certificados/certificateLifecycleService.js), sin copiar su código."""
import base64
import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, TransactionCase, new_test_user, tagged

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from ..models import MAX_P12_BYTES


def _build_trusted_certificate(ruc=ISSUER_RUC):
    """Certificado sintético cuyo emisor coincide con el catálogo local de CAs reconocidas
    (a diferencia de _build_certificate(), autofirmado con CN='SINKRONET S.A.S.')."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'TITULAR DE ENSAYO'),
                          x509.NameAttribute(NameOID.SERIAL_NUMBER, ruc)])
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'AUTORIDAD DE CERTIFICACION SECURITY DATA')])
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=365))
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                           data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False,
                           encipher_only=False, decipher_only=False), critical=True)
            .sign(key, hashes.SHA256()))
    return pkcs12.serialize_key_and_certificates(b'ensayo', key, cert, None,
        serialization.BestAvailableEncryption(P12_PASSWORD))


@tagged('post_install', '-at_install')
class CertificateCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({'vat': ISSUER_RUC, 'street': 'Matriz de ensayo'})
        self.p12, _key, _cert, _now = _build_certificate()

    def test_account_user_can_self_service_without_sudo(self):
        """Núcleo del incremento: un usuario account.group_account_user (no base.group_system)
        puede crear, verificar y reemplazar su propio certificado sin necesitar sudo()."""
        user = new_test_user(self.env, login='fiscal_sri_self_service', groups='account.group_account_user',
                              company_id=self.env.company.id, company_ids=[(6, 0, self.env.company.ids)])
        certificate = self.env['erpec.fiscal.certificate'].with_user(user).create({
            'company_id': self.env.company.id,
            'p12_file': base64.b64encode(self.p12),
            'p12_password': P12_PASSWORD.decode(),
        })
        certificate.with_user(user).action_verify()
        self.assertTrue(certificate.verified)
        self.assertIn('SINKRONET', certificate.subject_summary)

    def test_untrusted_issuer_warns_but_does_not_block(self):
        certificate = self.env['erpec.fiscal.certificate'].create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(self.p12), 'p12_password': P12_PASSWORD.decode()})
        certificate.action_verify()
        self.assertTrue(certificate.verified)
        self.assertFalse(certificate.issuer_trusted)
        self.assertIn('no está en el catálogo local', certificate.notice)

    def test_trusted_issuer_recognized(self):
        p12 = _build_trusted_certificate()
        certificate = self.env['erpec.fiscal.certificate'].create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        certificate.action_verify()
        self.assertTrue(certificate.verified)
        self.assertTrue(certificate.issuer_trusted)
        self.assertNotIn('no está en el catálogo local', certificate.notice)

    def test_oversized_file_rejected(self):
        oversized = base64.b64encode(b'0' * (MAX_P12_BYTES + 1))
        with self.assertRaises(ValidationError):
            self.env['erpec.fiscal.certificate'].create({
                'company_id': self.env.company.id, 'p12_file': oversized, 'p12_password': P12_PASSWORD.decode()})

    def test_onchange_preview_does_not_persist(self):
        with Form(self.env['erpec.fiscal.certificate']) as form:
            form.company_id = self.env.company
            form.p12_file = base64.b64encode(self.p12)
            form.p12_password = P12_PASSWORD.decode()
            self.assertIn('Vista previa', form.notice)
        certificate = form.save()
        self.assertFalse(certificate.verified)

    def test_verify_rate_limit_blocks_after_max_attempts(self):
        certificate = self.env['erpec.fiscal.certificate'].create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(self.p12), 'p12_password': P12_PASSWORD.decode()})
        for _ in range(5):
            certificate.action_verify()
        with self.assertRaisesRegex(UserError, 'Demasiados intentos'):
            certificate.action_verify()

    def test_signature_probe_requires_verified_certificate(self):
        certificate = self.env['erpec.fiscal.certificate'].create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(self.p12), 'p12_password': P12_PASSWORD.decode()})
        with self.assertRaises(UserError):
            certificate.action_test_signature()

    def test_signature_probe_succeeds_on_verified_certificate(self):
        certificate = self.env['erpec.fiscal.certificate'].create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(self.p12), 'p12_password': P12_PASSWORD.decode()})
        certificate.action_verify()
        certificate.action_test_signature()
        self.assertTrue(certificate.signature_tested)
        self.assertTrue(certificate.signature_tested_at)

    def test_company_isolation_still_enforced(self):
        certificate = self.env['erpec.fiscal.certificate'].create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(self.p12), 'p12_password': P12_PASSWORD.decode()})
        other = self.env['res.company'].create({'name': 'Otra empresa ensayo certificado'})
        user = new_test_user(self.env, login='fiscal_sri_other_cert', groups='account.group_account_user',
                              company_id=other.id, company_ids=[(6, 0, other.ids)])
        with self.assertRaises(AccessError):
            certificate.with_user(user).read(['subject_summary'])
