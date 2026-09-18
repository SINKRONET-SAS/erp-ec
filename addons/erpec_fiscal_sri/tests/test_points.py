"""Establecimientos y puntos de emisión: diario por ambiente (consecutivos independientes entre
pruebas y producción), habilitación explícita de producción y coherencia de numeración."""
import base64

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged, new_test_user

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate


@tagged('post_install', '-at_install')
class EmissionPointCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({
            'vat': ISSUER_RUC, 'street': 'Matriz de ensayo', 'ec_native_ordinary': True, 'ec_native_accounting': 'SI'})
        self.partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Cliente punto', 'vat': ISSUER_RUC, 'street': 'Dirección cliente',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_ruc').id})
        group = self.env['account.tax.group'].create({'name': 'IVA punto', 'l10n_ec_type': 'vat15'})
        self.tax = self.env['account.tax'].create({'name': 'IVA 15 punto', 'amount_type': 'percent', 'amount': 15,
                                                     'type_tax_use': 'sale', 'tax_group_id': group.id})
        self.point = self.env['erpec.fiscal.point'].create({
            'establishment': '001', 'establishment_name': 'Matriz', 'establishment_address': 'Av. Principal 123',
            'emission': '002', 'name': 'Caja 1'})
        p12, _key, _cert, _now = _build_certificate()
        self.certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        self.certificate.action_verify()

    def _invoice(self, journal, number):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'journal_id': journal.id, 'partner_id': self.partner.id,
            'invoice_date': '2026-09-18', 'date': '2026-09-18', 'ec_fiscal_payment_code': '20',
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_01').id,
            'invoice_line_ids': [(0, 0, {'name': 'Servicio', 'quantity': 1, 'price_unit': 100, 'tax_ids': [(6, 0, self.tax.ids)]})]})
        move.l10n_latam_document_number = number
        move.action_post()
        return move

    def test_creating_a_point_creates_its_testing_journal(self):
        journal = self.point.journal_ids
        self.assertEqual(len(journal), 1)
        self.assertEqual((journal.l10n_ec_entity, journal.l10n_ec_emission, journal.ec_sri_ambiente), ('001', '002', '1'))
        self.assertTrue(journal.l10n_latam_use_documents)
        self.assertEqual(self.point.ambiente, '1')

    def test_codes_are_validated_and_unique(self):
        with self.assertRaises(ValidationError):
            self.point.copy({'establishment': '1', 'emission': '003'})
        with self.assertRaises(ValidationError):
            self.point.copy({'establishment': '000', 'emission': '003'})
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.point.copy({})

    def test_environment_cannot_be_written_directly(self):
        with self.assertRaisesRegex(ValidationError, 'habilitación'):
            self.point.write({'ambiente': '2'})

    def test_production_requires_manager_and_recognized_certificate(self):
        accountant = new_test_user(self.env, login='point_accountant', groups='account.group_account_user')
        with self.assertRaisesRegex(ValidationError, 'responsable contable'):
            self.point.with_user(accountant).action_enable_production()
        with self.assertRaisesRegex(ValidationError, 'reconocida'):
            self.point.action_enable_production()

    def test_production_switch_uses_a_separate_journal_and_blocks_the_testing_one(self):
        self.certificate.issuer_trusted = True
        testing_journal = self.point.journal_ids
        testing_invoice = self._invoice(testing_journal, '001-002-000000001')
        self.point.action_enable_production()
        self.assertEqual(self.point.ambiente, '2')
        self.assertTrue(self.point.production_acknowledged)
        production_journal = self.point.journal_ids - testing_journal
        self.assertEqual(production_journal.ec_sri_ambiente, '2')
        self.assertNotEqual(production_journal.code, testing_journal.code)
        self.assertEqual(self.env['account.move'].search_count([('journal_id', '=', production_journal.id)]), 0)
        with self.assertRaisesRegex(ValidationError, 'diario de producción'):
            testing_invoice.action_native_emit()
        production_invoice = self._invoice(production_journal, '001-002-000000001')
        emission = self.env['erpec.fiscal.emission'].browse(production_invoice.action_native_emit()['res_id'])
        self.assertEqual(emission.ambiente, '2')
        self.assertEqual(emission.access_key[23], '2')
        self.assertIn(b'<ambiente>2</ambiente>', base64.b64decode(emission.xml_unsigned))
        self.assertIn(b'<dirEstablecimiento>Av. Principal 123</dirEstablecimiento>', base64.b64decode(emission.xml_unsigned))
        self.point.action_enable_testing()
        self.assertEqual(self.point.ambiente, '1')
        self.assertFalse(self.point.production_acknowledged)
        self.assertEqual(self.point.journal_ids, testing_journal | production_journal)

    def test_number_must_match_the_point(self):
        journal = self.point.journal_ids
        invoice = self._invoice(journal, '001-009-000000001')
        with self.assertRaisesRegex(ValidationError, 'no corresponde al establecimiento'):
            invoice.action_native_emit()

    def test_journal_numbers_must_match_the_point(self):
        with self.assertRaises(ValidationError):
            self.point.journal_ids.l10n_ec_emission = '005'
