"""Guía de remisión electrónica: firma real con certificado sintético; transmisión simulada."""
import base64
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from odoo.addons.erpec_fiscal_sri import sri_client


@tagged('post_install', '-at_install')
class GuideSriCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({
            'vat': ISSUER_RUC, 'street': 'Matriz de ensayo', 'ec_native_ordinary': True, 'ec_native_accounting': 'SI'})
        self.partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Destinatario de ensayo', 'vat': '1793235327001', 'street': 'Calle destino 1'})
        self.point = self.env['erpec.fiscal.point'].create({
            'establishment': '001', 'establishment_name': 'Matriz', 'establishment_address': 'Bodega principal',
            'emission': '004', 'name': 'Despachos'})
        p12, _key, _cert, _now = _build_certificate()
        self.certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        self.certificate.action_verify()

    def _guide(self, **values):
        today = fields.Date.context_today(self.env['erpec.fiscal.guide'])
        vals = {'point_id': self.point.id, 'partner_id': self.partner.id, 'recipient_address': 'Calle destino 1',
                'origin_address': 'Bodega principal', 'carrier_name': 'Transportes SA', 'carrier_type': '04',
                'carrier_vat': '1793235327001', 'plate': 'ABC1234', 'date_start': today, 'date_end': today,
                'line_ids': [(0, 0, {'code': 'A1', 'description': 'Caja', 'quantity': 3})]}
        vals.update(values)
        return self.env['erpec.fiscal.guide'].create(vals)

    def test_emit_signs_guide_with_point_numbering(self):
        guide = self._guide()
        emission = self.env['erpec.fiscal.emission'].browse(guide.action_sri_emit()['res_id'])
        self.assertEqual(emission.state, 'signed')
        self.assertEqual(emission.access_key[8:10], '06')
        self.assertEqual(guide.sri_number, '001-004-000000001')
        self.assertEqual(guide.state, 'emitted')
        self.assertIn(b'<guiaRemision', base64.b64decode(emission.xml_unsigned))
        self.assertEqual(guide.action_sri_emit()['res_id'], emission.id)
        with self.assertRaisesRegex(ValidationError, 'no se modifica'):
            guide.plate = 'XYZ9999'
        with self.assertRaises(ValidationError):
            guide.unlink()

    def test_numbering_is_separate_per_environment(self):
        first = self._guide()
        first.action_sri_emit()
        second = self._guide()
        second.action_sri_emit()
        self.assertEqual(second.sri_number, '001-004-000000002')
        self.certificate.issuer_trusted = True
        self.point.action_enable_production()
        production = self._guide()
        self.assertEqual(production._next_number(), '001-004-000000001')
        emission = self.env['erpec.fiscal.emission'].browse(production.action_sri_emit()['res_id'])
        self.assertEqual(emission.ambiente, '2')
        self.assertEqual(emission.access_key[23], '2')

    def test_transport_must_start_after_emission(self):
        guide = self._guide(date_start='2026-01-01', date_end='2026-01-02')
        with self.assertRaisesRegex(ValidationError, 'antes de iniciar'):
            guide.action_sri_emit()

    def test_create_from_picking_loads_goods(self):
        product = self.env['product.product'].create({'name': 'Producto guía', 'default_code': 'PG1', 'type': 'consu'})
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('company_id', '=', self.env.company.id)], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id, 'partner_id': self.partner.id,
            'location_id': picking_type.default_location_src_id.id, 'location_dest_id': picking_type.default_location_dest_id.id,
            'move_ids': [(0, 0, {'name': 'Producto guía', 'product_id': product.id, 'product_uom_qty': 4, 'product_uom': product.uom_id.id,
                                 'location_id': picking_type.default_location_src_id.id, 'location_dest_id': picking_type.default_location_dest_id.id})]})
        self.assertEqual(picking.ec_guide_count, 0)
        result = picking.action_create_sri_guide()
        guide = self.env['erpec.fiscal.guide'].browse(result['res_id'])
        self.assertEqual(guide.picking_id, picking)
        self.assertEqual(guide.line_ids.mapped('quantity'), [4.0])
        self.assertEqual(guide.line_ids.code, 'PG1')
        self.assertEqual(picking.action_create_sri_guide()['res_id'], guide.id)
        self.assertEqual(picking.ec_guide_count, 1)
        action_view = picking.action_view_sri_guides()
        self.assertEqual(action_view['res_model'], 'erpec.fiscal.guide')
        self.assertEqual(action_view['res_id'], guide.id)

    def test_full_flow_builds_guide_ride(self):
        guide = self._guide()
        emission = self.env['erpec.fiscal.emission'].browse(guide.action_sri_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('RECIBIDA', [])):
            emission.action_process()
        emission._save(next_attempt=False)
        answer = {'comprobante': base64.b64decode(emission.xml_signed), 'numero': '1234567890', 'fecha': '2026-09-18T10:00:00-05:00'}
        with patch.object(sri_client, 'consultar_autorizacion', return_value=('AUTORIZADO', answer, [])):
            emission.action_process()
        self.assertEqual(emission.state, 'authorized')
        self.assertTrue(base64.b64decode(emission.ride_pdf).startswith(b'%PDF'))

    def test_default_point_uses_the_user_preference(self):
        other = self.env['erpec.fiscal.point'].create({
            'establishment': '001', 'establishment_name': 'Matriz', 'establishment_address': 'Otra', 'emission': '009', 'name': 'Otra caja'})
        self.assertFalse(self.env['erpec.fiscal.guide']._default_point())
        self.env.user.ec_point_id = other
        self.assertEqual(self.env['erpec.fiscal.guide']._default_point(), other)
