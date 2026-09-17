"""Pruebas de erpec.fiscal.emission: firma real (certificado sintético) y transmisión SOAP
simulada (sin contactar al SRI real en la batería automática, igual que erpec_payphone mockea
Provider._request)."""
import base64
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged, new_test_user

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from .. import sri_client


@tagged('post_install', '-at_install')
class EmissionCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({
            'vat': ISSUER_RUC, 'street': 'Matriz de ensayo', 'ec_native_ordinary': True, 'ec_native_accounting': 'SI'})
        self.partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Cliente de ensayo', 'vat': ISSUER_RUC, 'street': 'Dirección de ensayo',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_ruc').id})
        group = self.env['account.tax.group'].create({'name': 'IVA de ensayo', 'l10n_ec_type': 'vat15'})
        self.tax = self.env['account.tax'].create({'name': 'IVA 15 ensayo', 'amount_type': 'percent', 'amount': 15,
                                                     'type_tax_use': 'sale', 'tax_group_id': group.id})
        self.move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner.id, 'invoice_date': '2026-09-16', 'date': '2026-09-16',
            'ec_fiscal_payment_code': '20',
            'invoice_line_ids': [(0, 0, {'name': 'Servicio de ensayo', 'quantity': 1, 'price_unit': 100, 'tax_ids': [(6, 0, self.tax.ids)]})]})
        self.move.name = '001-001-000000444'
        self.move.action_post()
        p12, _key, _cert, _now = _build_certificate()
        self.certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        self.certificate.action_verify()
        self.assertTrue(self.certificate.verified)

    def _authorized_response(self, access_key):
        factura = ('<factura id="comprobante" version="2.1.0"><infoTributaria><claveAcceso>' + access_key +
                   '</claveAcceso></infoTributaria><infoFactura><importeTotal>115.00</importeTotal>'
                   '<totalSinImpuestos>100.00</totalSinImpuestos><totalDescuento>0.00</totalDescuento>'
                   '<razonSocialComprador>Cliente de ensayo</razonSocialComprador>'
                   '<identificacionComprador>' + ISSUER_RUC + '</identificacionComprador>'
                   '<direccionComprador>Dirección de ensayo</direccionComprador><fechaEmision>16/09/2026</fechaEmision>'
                   '<propina>0.00</propina><totalConImpuestos/><pagos><pago><formaPago>20</formaPago><total>115.00</total></pago></pagos>'
                   '</infoFactura><detalles/></factura>')
        return {'comprobante': factura.encode('utf-8'), 'numero': '1234567890', 'fecha': '2026-09-16T10:00:00-05:00'}

    def test_emit_requires_verified_certificate(self):
        self.certificate.write({'verified': False})
        with self.assertRaisesRegex(ValidationError, 'certificado'):
            self.move.action_native_emit()

    def test_emit_signs_and_creates_emission(self):
        result = self.move.action_native_emit()
        emission = self.env['erpec.fiscal.emission'].browse(result['res_id'])
        self.assertEqual(emission.state, 'signed')
        self.assertEqual(len(emission.access_key), 49)
        self.assertTrue(emission.xml_signed)
        # Repetir no crea una segunda emisión.
        result2 = self.move.action_native_emit()
        self.assertEqual(result2['res_id'], emission.id)
        self.assertEqual(self.env['erpec.fiscal.emission'].search_count([('move_id', '=', self.move.id)]), 1)

    def test_full_flow_to_authorized(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('RECIBIDA', [])):
            emission.action_process()
        self.assertEqual(emission.state, 'waiting')
        emission._save(next_attempt=False)  # Simula que pasó el tiempo de espera del sondeo.
        with patch.object(sri_client, 'consultar_autorizacion', return_value=('AUTORIZADO', self._authorized_response(emission.access_key), [])):
            emission.action_process()
        self.assertEqual(emission.state, 'authorized')
        self.assertTrue(emission.ride_pdf)
        self.assertEqual(emission.authorization_number, '1234567890')

    def test_returned_by_recepcion(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('DEVUELTA', [{'mensaje': 'CLAVE_ACCESO_REGISTRADA'}])):
            emission.action_process()
        self.assertEqual(emission.state, 'returned')

    def test_not_authorized_by_sri(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('RECIBIDA', [])):
            emission.action_process()
        emission._save(next_attempt=False)  # Simula que pasó el tiempo de espera del sondeo.
        with patch.object(sri_client, 'consultar_autorizacion', return_value=('NO AUTORIZADO', None, [{'mensaje': 'FIRMA_INVALIDA'}])):
            emission.action_process()
        self.assertEqual(emission.state, 'rejected')

    def test_connection_error_retries_then_blocks(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', side_effect=sri_client.SriError('SRI_CONEXION', retry=True)):
            emission.action_process()
        self.assertEqual(emission.state, 'signed')
        self.assertEqual(emission.attempts, 1)
        self.assertTrue(emission.next_attempt)

    def test_mutual_exclusion_with_external_connector(self):
        from odoo.addons.erpec_fiscal_connector.connector import _INTERNAL
        connection = self.env['erpec.fiscal.connection'].create({
            'company_id': self.env.company.id, 'base_url': 'http://127.0.0.1:3099', 'organization_ref': 'ensayo',
            'empresa_ref': 1, 'workspace_ref': 1, 'emission_point_ref': 1})
        self.env['erpec.fiscal.job'].with_context(_fiscal_internal=_INTERNAL).create({
            'move_id': self.move.id, 'connection_id': connection.id, 'external_reference': 'ensayo-sri-block',
            'correlation_id': 'ensayo', 'payload': {}})
        with self.assertRaisesRegex(ValidationError, 'Facturador externo'):
            self.move.action_native_emit()

    def test_unlink_blocked(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        with self.assertRaises(ValidationError):
            emission.unlink()

    def test_write_blocked_outside_actions(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        with self.assertRaises(ValidationError):
            emission.write({'state': 'authorized'})

    def test_permissions_and_isolation(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        other = self.env['res.company'].create({'name': 'Otra empresa ensayo SRI'})
        user = new_test_user(self.env, login='fiscal_sri_other', groups='account.group_account_user',
                              company_id=other.id, company_ids=[(6, 0, other.ids)])
        with self.assertRaises(AccessError):
            emission.with_user(user).read(['access_key'])
        with self.assertRaises(AccessError):
            self.certificate.with_user(user).write({'verified': True})
