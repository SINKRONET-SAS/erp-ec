"""Verifica la integridad del catálogo ATS transcrito del archivo oficial del SRI."""
from odoo.tests import TransactionCase, tagged
from .. import ats_catalog


@tagged('post_install', '-at_install')
class AtsCatalogCase(TransactionCase):
    def test_months_complete(self):
        self.assertEqual(set(ats_catalog.MONTHS), {'%02d' % month for month in range(1, 13)})

    def test_identification_codes_reference_known_transactions(self):
        known_transactions = {'COMPRA', 'VENTA', 'EXPORTACION', 'TARJETA DE CREDITO', 'RENDIMIENTOS FINANCIEROS', 'FONDOS Y FIDEICOMISOS', 'COMPROBANTES ANULADOS'}
        for code, entry in ats_catalog.IDENTIFICATION_CODES.items():
            self.assertEqual(len(code), 2)
            self.assertIn(entry['transaction'], known_transactions)

    def test_voucher_types_reference_only_declared_support_codes(self):
        for code, voucher in ats_catalog.VOUCHER_TYPES.items():
            for support in voucher['validSustento']:
                self.assertIn(support, ats_catalog.SUPPORT_CODES, 'Comprobante %s referencia un sustento %s no declarado' % (code, support))

    def test_support_codes_reference_only_declared_voucher_types(self):
        for code, support in ats_catalog.SUPPORT_CODES.items():
            for voucher in support['validVoucherTypes']:
                self.assertIn(voucher, ats_catalog.VOUCHER_TYPES, 'Sustento %s referencia un comprobante %s no declarado' % (code, voucher))

    def test_country_codes_include_ecuador_and_are_three_digits(self):
        self.assertEqual(ats_catalog.COUNTRY_CODES['593'], 'ECUADOR')
        for code in ats_catalog.COUNTRY_CODES:
            self.assertEqual(len(code), 3)
            self.assertTrue(code.isdigit())

    def test_source_is_documented(self):
        self.assertIn('url', ats_catalog.SOURCE)
        self.assertIn('downloadedAt', ats_catalog.SOURCE)
