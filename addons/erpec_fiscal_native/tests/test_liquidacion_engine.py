"""Motor XML de liquidación de compra v1.1.0; validación real contra el XSD oficial."""
from odoo.tests import TransactionCase, tagged

from .. import liquidacion_engine


@tagged('post_install', '-at_install')
class LiquidacionEngineCase(TransactionCase):
    def _data(self, **overrides):
        data = {
            'date': '2026-09-18', 'number': '001-001-000000004', 'numeric': '12345678', 'issuer_vat': '1709053506001',
            'issuer_name': 'EMISOR', 'issuer_address': 'Matriz', 'accounting': 'NO', 'payment': '01', 'total': 115.0,
            'provider_type': '05', 'provider_vat': '1710034065', 'provider_name': 'Proveedor', 'provider_address': 'Calle 1',
            'items': [{'code': 'S1', 'description': 'Servicio', 'quantity': 1, 'unit': 100, 'discount': 0, 'rate': 15, 'subtotal': 100.0, 'tax': 15.0}],
        }
        data.update(overrides)
        return data

    def test_valid_xml(self):
        key, xml = liquidacion_engine.generate(self._data())
        self.assertEqual(key[8:10], '03')
        self.assertIn(b'<liquidacionCompra', xml)
        self.assertIn(b'<importeTotal>115.00</importeTotal>', xml)
        self.assertNotIn(b'<propina>', xml)

    def test_passport_and_foreign_ids_accepted(self):
        liquidacion_engine.generate(self._data(provider_type='06', provider_vat='AB123456'))

    def test_rejects_bad_provider_and_totals(self):
        with self.assertRaises(ValueError):
            liquidacion_engine.generate(self._data(provider_vat='123'))
        with self.assertRaises(ValueError):
            liquidacion_engine.generate(self._data(provider_type='07'))
        with self.assertRaises(ValueError):
            liquidacion_engine.generate(self._data(total=1.0))

    def test_environment_in_key(self):
        key, _xml = liquidacion_engine.generate(self._data(ambiente='2'))
        self.assertEqual(key[23], '2')
