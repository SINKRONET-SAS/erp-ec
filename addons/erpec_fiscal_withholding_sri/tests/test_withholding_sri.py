"""Retención electrónica firmada: firma real con certificado sintético; la transmisión al SRI se
simula. Numeración separada por ambiente (pruebas/producción)."""
import base64
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from odoo.addons.erpec_fiscal_sri import sri_client


@tagged('post_install', '-at_install')
class WithholdingSriCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({
            'vat': ISSUER_RUC, 'street': 'Matriz de ensayo', 'ec_native_ordinary': True, 'ec_native_accounting': 'SI',
            'ec_agent_resolution': '12345678'})
        self.supplier = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Proveedor de ensayo', 'vat': '1793235327001', 'street': 'Dirección proveedor',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_ruc').id})
        group = self.env['account.tax.group'].create({'name': 'IVA compras ensayo', 'l10n_ec_type': 'vat15'})
        tax = self.env['account.tax'].create({'name': 'IVA 15 compras ensayo', 'amount_type': 'percent', 'amount': 15,
                                               'type_tax_use': 'purchase', 'tax_group_id': group.id})
        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], limit=1)
        purchase_journal.l10n_latam_use_documents = True
        self.bill = self.env['account.move'].create({
            'move_type': 'in_invoice', 'journal_id': purchase_journal.id, 'partner_id': self.supplier.id,
            'invoice_date': '2026-09-10', 'date': '2026-09-10',
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_01').id,
            'invoice_line_ids': [(0, 0, {'name': 'Servicio contratado', 'quantity': 1, 'price_unit': 100, 'tax_ids': [(6, 0, tax.ids)]})]})
        self.bill.l10n_latam_document_number = '001-002-000000123'
        self.bill.action_post()
        self.journal = self.env['account.journal'].search([('company_id', '=', self.env.company.id), ('type', '=', 'general')], limit=1)
        self.liability = self.env['account.account'].create({'name': 'Retenciones por pagar ensayo', 'code': 'ECRETSRI1', 'account_type': 'liability_current'})
        p12, _key, _cert, _now = _build_certificate()
        certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        certificate.action_verify()

    def _retention(self, lines=None, reference='RET-1'):
        lines = lines or [
            {'name': 'Renta 2%', 'kind': 'income', 'sri_code': '312', 'base': 100, 'rate': 2},
            {'name': 'IVA 30%', 'kind': 'vat', 'sri_code': '1', 'base': 15, 'rate': 30}]
        retention = self.env['erpec.withholding'].create({
            'invoice_id': self.bill.id, 'reference': reference, 'date': '2026-09-18', 'journal_id': self.journal.id,
            'sri_sustento_code': '01', 'line_ids': [(0, 0, dict(line, account_id=self.liability.id)) for line in lines]})
        retention.action_post()
        return retention

    def test_emit_signs_retention_and_assigns_number(self):
        retention = self._retention()
        emission = self.env['erpec.fiscal.emission'].browse(retention.action_sri_emit()['res_id'])
        self.assertEqual(emission.state, 'signed')
        self.assertEqual(emission.access_key[8:10], '07')
        self.assertEqual(emission.access_key[23], '1')
        self.assertEqual(retention.sri_number, '001-001-000000001')
        xml = base64.b64decode(emission.xml_unsigned)
        self.assertIn(b'<comprobanteRetencion', xml)
        self.assertIn(b'<numDocSustento>001002000000123</numDocSustento>', xml)
        self.assertIn(b'<agenteRetencion>12345678</agenteRetencion>', xml)
        self.assertEqual(retention.action_sri_emit()['res_id'], emission.id)

    def test_numbering_is_separate_per_environment(self):
        first = self._retention()
        first.action_sri_emit()
        second = self._retention(reference='RET-2', lines=[{'name': 'Renta', 'kind': 'income', 'sri_code': '312', 'base': 50, 'rate': 2}])
        second.action_sri_emit()
        self.assertEqual(second.sri_number, '001-001-000000002')
        self.journal.ec_sri_ambiente = '2'
        production_number = self._retention(reference='RET-3', lines=[{'name': 'Renta', 'kind': 'income', 'sri_code': '312', 'base': 10, 'rate': 2}])._next_sri_number()
        self.assertEqual(production_number, '001-001-000000001')
        self.journal.ec_sri_ambiente = '1'
        self.assertEqual(first._next_sri_number(), '001-001-000000003')

    def test_production_environment_is_not_enabled(self):
        retention = self._retention()
        self.journal.ec_sri_ambiente = '2'
        with self.assertRaisesRegex(ValidationError, 'producción'):
            retention.action_sri_emit()
        self.assertFalse(retention.emission_ids)

    def test_vat_code_must_match_percentage(self):
        retention = self._retention(lines=[{'name': 'IVA', 'kind': 'vat', 'sri_code': '9', 'base': 15, 'rate': 30}])
        with self.assertRaisesRegex(ValidationError, 'Tabla 20'):
            retention.action_sri_emit()

    def test_requires_sustento_and_posted_state(self):
        retention = self._retention()
        retention.sri_sustento_code = False
        with self.assertRaisesRegex(ValidationError, 'sustento'):
            retention.action_sri_emit()

    def test_full_flow_builds_retention_ride(self):
        retention = self._retention()
        emission = self.env['erpec.fiscal.emission'].browse(retention.action_sri_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('RECIBIDA', [])):
            emission.action_process()
        emission._save(next_attempt=False)
        answer = {'comprobante': base64.b64decode(emission.xml_signed), 'numero': '1234567890', 'fecha': '2026-09-18T10:00:00-05:00'}
        with patch.object(sri_client, 'consultar_autorizacion', return_value=('AUTORIZADO', answer, [])):
            emission.action_process()
        self.assertEqual(emission.state, 'authorized')
        self.assertTrue(base64.b64decode(emission.ride_pdf).startswith(b'%PDF'))
