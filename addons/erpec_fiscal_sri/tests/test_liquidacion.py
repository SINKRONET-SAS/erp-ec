"""Liquidación de compra (codDoc 03): la emite el comprador; el consecutivo sale del punto de emisión
del diario de compras, por ambiente. Firma real con certificado sintético; transmisión simulada."""
import base64
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from .. import sri_client


@tagged('post_install', '-at_install')
class LiquidationCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({
            'vat': ISSUER_RUC, 'street': 'Matriz de ensayo', 'ec_native_ordinary': True, 'ec_native_accounting': 'SI'})
        self.provider = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Proveedor sin RUC', 'vat': '1710034065', 'street': 'Calle del proveedor',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_dni').id})
        group = self.env['account.tax.group'].create({'name': 'IVA compras liq', 'l10n_ec_type': 'vat15'})
        self.tax = self.env['account.tax'].create({'name': 'IVA 15 compras liq', 'amount_type': 'percent', 'amount': 15,
                                                     'type_tax_use': 'purchase', 'tax_group_id': group.id})
        self.point = self.env['erpec.fiscal.point'].create({
            'establishment': '001', 'establishment_name': 'Matriz', 'establishment_address': 'Av. Principal 123',
            'emission': '003', 'name': 'Compras'})
        self.journal = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], limit=1)
        self.journal.write({'l10n_latam_use_documents': True, 'ec_point_id': self.point.id})
        p12, _key, _cert, _now = _build_certificate()
        self.certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        self.certificate.action_verify()

    def _liquidation(self, doc_type='l10n_ec.ec_dt_03'):
        return self.env['account.move'].create({
            'move_type': 'in_invoice', 'journal_id': self.journal.id, 'partner_id': self.provider.id,
            'invoice_date': '2026-09-18', 'date': '2026-09-18', 'ec_fiscal_payment_code': '01',
            'l10n_latam_document_type_id': self.env.ref(doc_type).id,
            'invoice_line_ids': [(0, 0, {'name': 'Servicio de jardinería', 'quantity': 1, 'price_unit': 100, 'tax_ids': [(6, 0, self.tax.ids)]})]})

    def test_emit_assigns_number_posts_and_signs(self):
        move = self._liquidation()
        self.assertTrue(move.ec_is_liquidation)
        emission = self.env['erpec.fiscal.emission'].browse(move.action_native_emit_liquidation()['res_id'])
        self.assertEqual(move.state, 'posted')
        self.assertEqual(move.l10n_latam_document_number, '001-003-000000001')
        self.assertEqual(emission.state, 'signed')
        self.assertEqual(emission.access_key[8:10], '03')
        xml = base64.b64decode(emission.xml_unsigned)
        self.assertIn(b'<liquidacionCompra', xml)
        self.assertIn(b'<identificacionProveedor>1710034065</identificacionProveedor>', xml)
        self.assertEqual(move.action_native_emit_liquidation()['res_id'], emission.id)

    def test_numbering_is_per_environment(self):
        first = self._liquidation()
        first.action_native_emit_liquidation()
        second = self._liquidation()
        second.action_native_emit_liquidation()
        self.assertEqual(second.l10n_latam_document_number, '001-003-000000002')
        self.certificate.issuer_trusted = True
        self.point.action_enable_production()
        with self.assertRaisesRegex(ValidationError, 'diario'):
            self._liquidation().action_native_emit_liquidation()
        self.assertEqual(self.point._next_sequence('liquidation'), '001-003-000000001')

    def test_requires_point_and_liquidation_type(self):
        with self.assertRaisesRegex(ValidationError, 'Liquidación de compra'):
            self._liquidation('l10n_ec.ec_dt_01').action_native_emit_liquidation()
        self.journal.ec_point_id = False
        with self.assertRaisesRegex(ValidationError, 'punto de emisión'):
            self._liquidation().action_native_emit_liquidation()

    def test_full_flow_builds_liquidation_ride(self):
        move = self._liquidation()
        emission = self.env['erpec.fiscal.emission'].browse(move.action_native_emit_liquidation()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('RECIBIDA', [])):
            emission.action_process()
        emission._save(next_attempt=False)
        answer = {'comprobante': base64.b64decode(emission.xml_signed), 'numero': '1234567890', 'fecha': '2026-09-18T10:00:00-05:00'}
        with patch.object(sri_client, 'consultar_autorizacion', return_value=('AUTORIZADO', answer, [])):
            emission.action_process()
        self.assertEqual(emission.state, 'authorized')
        self.assertTrue(base64.b64decode(emission.ride_pdf).startswith(b'%PDF'))
