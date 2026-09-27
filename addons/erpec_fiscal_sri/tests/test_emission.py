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

    def _di25_emission(self, move=None, state='signed'):
        from ..models import _INTERNAL
        return self.env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=_INTERNAL).create({
            'move_id': (move or self.move).id, 'state': state, 'access_key': '1' * 49,
            'xml_signed': base64.b64encode(b'<ensayo/>')})

    def test_di25_queue_does_not_starve_signed(self):
        signed = self._di25_emission()
        for _ in range(10):
            self._di25_emission(self.move.copy(), 'blocked')
        with patch.object(type(signed), '_transmit', autospec=True) as transmit:
            self.env['erpec.fiscal.emission']._cron_process()
        self.assertIn(signed.id, [call.args[0].id for call in transmit.call_args_list])

    def test_di25_native_blocks_external(self):
        from odoo.addons.erpec_fiscal_connector.connector import _INTERNAL
        connection = self.env['erpec.fiscal.connection'].create({
            'company_id': self.env.company.id, 'base_url': 'http://127.0.0.1:3099',
            'organization_ref': 'ensayo', 'empresa_ref': 1, 'workspace_ref': 1, 'emission_point_ref': 1})
        connection.with_context(_fiscal_internal=_INTERNAL).write({'verified': True})
        self._di25_emission()
        with self.assertRaisesRegex(ValidationError, 'nativa'):
            self.move.action_queue_fiscal()

    def test_di25_signed_content_is_immutable(self):
        self._di25_emission()
        with self.assertRaises(ValidationError):
            self.move.invoice_line_ids.write({'name': 'Concepto alterado después de firmar'})
        with self.assertRaises(ValidationError):
            self.move.write({'ec_fiscal_payment_code': '01'})
        with self.assertRaises(ValidationError):
            self.move.button_draft()

    def test_di25_failure_isolated_and_latency_visible(self):
        first = self._di25_emission()
        second = self._di25_emission(self.move.copy())
        def transmit(emission):
            if emission == first:
                raise RuntimeError('Fallo sintético del trabajo')
            emission._save(state='waiting', next_attempt=__import__('datetime').datetime(2099, 1, 1))
        with patch.object(type(first), '_transmit', autospec=True, side_effect=transmit):
            self.env['erpec.fiscal.emission']._cron_process()
        self.assertEqual(first.state, 'blocked')
        self.assertEqual(first.last_error, 'FISCAL_TRABAJO_ERROR')
        self.assertEqual(second.state, 'waiting')
        self.assertTrue(second.first_attempt_at)
        self.assertGreaterEqual(second.dispatch_delay_seconds, 0)

    def test_di25_recovery_queries_original_key_without_resigning(self):
        emission = self._di25_emission(state='blocked')
        original = (emission.access_key, emission.xml_signed)
        emission.action_review()
        with patch.object(sri_client, 'consultar_autorizacion', return_value=('NO AUTORIZADO', None, [])), patch.object(sri_client, 'enviar_recepcion') as send:
            emission.action_process()
        send.assert_not_called()
        self.assertEqual(emission.state, 'rejected')
        self.assertEqual((emission.access_key, emission.xml_signed), original)

    def test_di25_commit_trigger_and_idempotency(self):
        with patch.object(type(self.env['ir.cron']), '_trigger', autospec=True) as trigger:
            one = self.move.action_native_emit()
            two = self.move.action_native_emit()
        self.assertEqual(one['res_id'], two['res_id'])
        self.assertEqual(trigger.call_count, 1)

    def test_di25_cannot_move_line_into_signed_document(self):
        other = self.move.copy()
        self._di25_emission()
        with self.assertRaises(ValidationError):
            other.invoice_line_ids.write({'move_id': self.move.id})

    def test_di25_preview_matches_signed_economic_content(self):
        from lxml import etree
        preview = self.env['erpec.fiscal.preview'].browse(self.move.action_native_preview()['res_id'])
        emission = self.env['erpec.fiscal.emission'].browse(self.move.action_native_emit()['res_id'])
        a = etree.fromstring(base64.b64decode(preview.xml_file))
        b = etree.fromstring(base64.b64decode(emission.xml_unsigned))
        for tag in ['detalles', 'infoFactura']:
            self.assertEqual(etree.tostring(a.find(tag)), etree.tostring(b.find(tag)))

    def test_it26_sri_status_and_action(self):
        self.assertEqual(self.move.ec_sri_status, 'Sin emitir')
        action_before = self.move.action_view_sri_emission()
        self.assertEqual(action_before['res_model'], 'erpec.fiscal.emission')
        self.move.action_native_emit()
        self.assertEqual(self.move.ec_sri_status, 'Pendiente')
        action_after = self.move.action_view_sri_emission()
        self.assertEqual(action_after['res_model'], 'erpec.fiscal.emission')
        self.assertEqual(action_after['view_mode'], 'form')
        emission = self.move.ec_fiscal_emission_ids[0]
        emission.state = 'authorized'
        self.assertEqual(self.move.ec_sri_status, 'Autorizado')
        emission.state = 'rejected'
        self.assertEqual(self.move.ec_sri_status, 'Rechazado')
