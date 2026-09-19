"""Motor XML del comprobante de retención v2.0.0; validación real contra el XSD oficial."""
from odoo.tests import TransactionCase, tagged

from .. import retencion_engine
from ..engine import access_key


@tagged('post_install', '-at_install')
class RetencionEngineCase(TransactionCase):
    def _data(self, **overrides):
        data = {
            'date': '2026-09-18', 'number': '001-001-000000007', 'numeric': '12345678',
            'issuer_vat': '1709053506001', 'issuer_name': 'EMISOR', 'issuer_address': 'Dir', 'accounting': 'NO',
            'subject_type': '04', 'subject_vat': '1793235327001', 'subject_name': 'Proveedor', 'subject_kind': '02', 'related_party': 'NO',
            'support': {'sustento_code': '01', 'doc_type': '01', 'doc_number': '001-002-000000123', 'doc_date': '2026-09-10',
                        'untaxed': 100, 'total': 115, 'payment': '20',
                        'taxes': [{'code': '2', 'percent_code': '4', 'base': 100, 'rate': 15, 'amount': 15}]},
            'lines': [{'kind': 'income', 'sri_code': '312', 'base': 100, 'rate': 2, 'amount': 2.0},
                      {'kind': 'vat', 'sri_code': '2', 'base': 15, 'rate': 70, 'amount': 10.5}],
        }
        data.update(overrides)
        return data

    def test_valid_xml_and_key(self):
        key, xml = retencion_engine.generate(self._data())
        self.assertEqual(key[8:10], '07')
        self.assertIn(b'<periodoFiscal>09/2026</periodoFiscal>', xml)
        self.assertIn(b'<valorRetenido>10.50</valorRetenido>', xml)
        self.assertNotIn(b'tipoSujetoRetenido', xml)
        _key, foreign = retencion_engine.generate(self._data(subject_type='08', subject_vat='EXT123'))
        self.assertIn(b'<tipoSujetoRetenido>02</tipoSujetoRetenido>', foreign)

    def test_vat_code_percentage_table(self):
        for rate, code in ((10, '9'), (20, '10'), (30, '1'), (50, '11'), (70, '2'), (100, '3')):
            amount = round(15 * rate / 100, 2)
            retencion_engine.generate(self._data(lines=[{'kind': 'vat', 'sri_code': code, 'base': 15, 'rate': rate, 'amount': amount}]))
        with self.assertRaises(ValueError):
            retencion_engine.generate(self._data(lines=[{'kind': 'vat', 'sri_code': '9', 'base': 15, 'rate': 30, 'amount': 4.5}]))

    def test_rejects_bad_amounts_and_missing_code(self):
        with self.assertRaises(ValueError):
            retencion_engine.generate(self._data(lines=[{'kind': 'income', 'sri_code': '312', 'base': 100, 'rate': 2, 'amount': 5}]))
        with self.assertRaises(ValueError):
            retencion_engine.generate(self._data(lines=[{'kind': 'income', 'sri_code': '', 'base': 100, 'rate': 2, 'amount': 2}]))

    def test_income_catalog_validates_code_and_rate(self):
        with self.assertRaisesRegex(ValueError, 'catálogo'):
            retencion_engine.generate(self._data(lines=[{'kind': 'income', 'sri_code': '999', 'base': 100, 'rate': 2, 'amount': 2}]))
        with self.assertRaisesRegex(ValueError, 'no corresponde al código 312'):
            retencion_engine.generate(self._data(lines=[{'kind': 'income', 'sri_code': '312', 'base': 100, 'rate': 1.75, 'amount': 1.75}]))

    def test_environment_changes_key_and_xml(self):
        key1, xml1 = retencion_engine.generate(self._data())
        key2, xml2 = retencion_engine.generate(self._data(ambiente='2'))
        self.assertEqual(key1[23], '1')
        self.assertEqual(key2[23], '2')
        self.assertIn(b'<ambiente>2</ambiente>', xml2)
        self.assertEqual(access_key('2026-09-18', '1709053506001', '001-001-000000007', '12345678', ambiente='2')[23], '2')
        with self.assertRaises(ValueError):
            access_key('2026-09-18', '1709053506001', '001-001-000000007', '12345678', ambiente='3')
