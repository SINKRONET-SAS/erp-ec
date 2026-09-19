"""Factura de reembolso (codDocReembolso 41): sustentos de terceros dentro de la factura. Firma real con
certificado sintético; sin transmisión."""
import base64

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate


@tagged('post_install', '-at_install')
class ReimbursementCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({
            'vat': ISSUER_RUC, 'street': 'Matriz de ensayo', 'ec_native_ordinary': True, 'ec_native_accounting': 'SI'})
        self.partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Cliente reembolso', 'vat': ISSUER_RUC, 'street': 'Dirección cliente',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_ruc').id})
        group = self.env['account.tax.group'].create({'name': 'IVA no objeto', 'l10n_ec_type': 'not_charged_vat'})
        self.no_object = self.env['account.tax'].create({'name': 'No objeto ensayo', 'amount_type': 'percent', 'amount': 0,
                                                           'type_tax_use': 'sale', 'tax_group_id': group.id})
        self.point = self.env['erpec.fiscal.point'].create({
            'establishment': '001', 'establishment_name': 'Matriz', 'establishment_address': 'Av. 1', 'emission': '006', 'name': 'Caja'})
        p12, _key, _cert, _now = _build_certificate()
        certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        certificate.action_verify()

    def _invoice(self, amount=150):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'journal_id': self.point.journal_ids.id, 'partner_id': self.partner.id,
            'invoice_date': '2026-09-18', 'date': '2026-09-18', 'ec_fiscal_payment_code': '01',
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_01').id,
            'invoice_line_ids': [(0, 0, {'name': 'Reembolso de gastos', 'quantity': 1, 'price_unit': amount, 'tax_ids': [(6, 0, self.no_object.ids)]})]})
        move.l10n_latam_document_number = '001-006-000000001'
        move.action_post()
        return move

    def _support(self, move, base=130.43, **values):
        vals = {'move_id': move.id, 'provider_type': '04', 'provider_vat': '1793235327001', 'provider_kind': '02', 'doc_type': '01',
                'doc_number': '001-002-000000008', 'doc_date': '2026-09-10', 'authorization': '1009202601179323532700110010020000000081234567814',
                'base_amount': base, 'tax_kind': 'vat15'}
        vals.update(values)
        return self.env['erpec.fiscal.reimbursement'].create(vals)

    def test_reimbursement_invoice_is_signed_with_support_block(self):
        move = self._invoice()
        support = self._support(move)
        self.assertEqual(support.tax_amount, 19.56)
        emission = self.env['erpec.fiscal.emission'].browse(move.action_native_emit()['res_id'])
        self.assertEqual(emission.access_key[8:10], '01')
        xml = base64.b64decode(emission.xml_unsigned)
        self.assertIn(b'<codDocReembolso>41</codDocReembolso>', xml)
        self.assertIn(b'<reembolsoDetalle>', xml)
        self.assertIn(b'<codigoPorcentaje>6</codigoPorcentaje>', xml)
        with self.assertRaisesRegex(ValidationError, 'no se modifican'):
            support.base_amount = 10

    def test_supports_cannot_exceed_invoice_total(self):
        move = self._invoice(amount=100)
        self._support(move, base=200)
        with self.assertRaisesRegex(ValidationError, 'no pueden superar'):
            move.action_native_emit()

    def test_support_data_is_validated(self):
        move = self._invoice()
        with self.assertRaises(ValidationError):
            self._support(move, doc_number='1-2-3')
        with self.assertRaises(ValidationError):
            self._support(move, authorization='123')
        with self.assertRaises(ValidationError):
            self._support(move, base=0)

    def test_no_object_invoice_without_supports_is_valid(self):
        move = self._invoice(amount=50)
        emission = self.env['erpec.fiscal.emission'].browse(move.action_native_emit()['res_id'])
        self.assertNotIn(b'codDocReembolso', base64.b64decode(emission.xml_unsigned))
