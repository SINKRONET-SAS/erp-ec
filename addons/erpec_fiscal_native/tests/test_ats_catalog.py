"""Verifica la integridad del catálogo ATS transcrito del archivo oficial del SRI."""
import xlrd
from odoo.tests import TransactionCase, tagged
from .. import ats_catalog, ats_catalog_seal


@tagged('post_install', '-at_install')
class AtsCatalogCase(TransactionCase):
    def test_months_complete(self):
        self.assertEqual(set(ats_catalog.MONTHS), {'%02d' % month for month in range(1, 13)})

    def test_bundled_catalog_and_schema_are_the_files_downloaded_from_the_sri_portal(self):
        # DI25-04.1: huella sellada a mano (ats_catalog_seal.py) de los archivos bundleados en
        # addons/erpec_fiscal_native/reference/ y xsd/. Cualquier reemplazo silencioso rompe esta prueba.
        self.assertEqual(ats_catalog_seal.verify_bundled_files_integrity(), [])
        self.assertEqual(ats_catalog_seal.verify_source_metadata(), [])

    def test_country_codes_match_the_catalog_tabla16_sheet(self):
        # DI25-04.1: recontraste del 23-09-2026 contra una descarga fresca del archivo oficial
        # (ficha listada 06-08-2026, posterior a la primera transcripción del 13-09-2026): corrige
        # 24 códigos de país faltantes desde entonces, entre ellos Argentina (101), Bolivia (102),
        # Brasil (103), Canadá (104) y Colombia (105).
        workbook = xlrd.open_workbook(ats_catalog_seal.MODULE_ROOT / 'reference' / 'Catalogo_ATS_2026.xls')
        sheet = workbook.sheet_by_name('TABLAS REFERENCIALES')
        found = {}
        for row in range(277, 367):
            for start in (1, 3, 5):
                name, code = sheet.cell_value(row, start), sheet.cell_value(row, start + 1)
                if isinstance(name, str) and name.strip() and isinstance(code, float):
                    found[str(int(code)).zfill(3)] = name.strip()
        self.assertEqual(found, ats_catalog.COUNTRY_CODES)

    def test_voucher_type_374_is_transcribed(self):
        # Código presente en la hoja oficial (fila 86, Tabla 4) desde antes de la primera
        # transcripción; se había omitido por error.
        self.assertIn('374', ats_catalog.VOUCHER_TYPES)
        self.assertEqual(ats_catalog.VOUCHER_TYPES['374']['validSustento'], [])

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
