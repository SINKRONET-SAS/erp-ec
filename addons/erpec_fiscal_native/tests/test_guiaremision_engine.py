"""Motor XML de guía de remisión v1.1.0; validación real contra el XSD oficial."""
from odoo.tests import TransactionCase, tagged

from .. import guiaremision_engine


@tagged('post_install', '-at_install')
class GuiaRemisionEngineCase(TransactionCase):
    def _data(self, **overrides):
        data = {
            'date': '2026-09-18', 'number': '001-001-000000003', 'numeric': '12345678', 'issuer_vat': '1709053506001',
            'issuer_name': 'EMISOR', 'issuer_address': 'Matriz', 'accounting': 'NO', 'origin_address': 'Bodega Norte',
            'carrier_type': '04', 'carrier_vat': '1793235327001', 'carrier_name': 'Transportes SA', 'plate': 'ABC1234',
            'date_start': '2026-09-19', 'date_end': '2026-09-20', 'recipient_vat': '1793235327001',
            'recipient_name': 'Cliente', 'recipient_address': 'Dir cliente', 'reason': 'Venta',
            'support': {'doc_type': '01', 'doc_number': '001-001-000000005', 'doc_date': '2026-09-18'},
            'items': [{'code': 'A1', 'description': 'Caja', 'quantity': 2.5}],
        }
        data.update(overrides)
        return data

    def test_valid_xml_and_key(self):
        key, xml = guiaremision_engine.generate(self._data())
        self.assertEqual(key[8:10], '06')
        self.assertIn(b'<guiaRemision', xml)
        self.assertIn(b'<placa>ABC1234</placa>', xml)
        self.assertIn(b'<cantidad>2.5</cantidad>', xml)
        self.assertIn(b'<numDocSustento>001-001-000000005</numDocSustento>', xml)

    def test_support_is_optional(self):
        _key, xml = guiaremision_engine.generate(self._data(support=None))
        self.assertNotIn(b'numDocSustento', xml)

    def test_dates_and_required_data(self):
        with self.assertRaises(ValueError):
            guiaremision_engine.generate(self._data(date_start='2026-09-17', date_end='2026-09-17'))
        with self.assertRaises(ValueError):
            guiaremision_engine.generate(self._data(date_start='2026-09-20', date_end='2026-09-19'))
        with self.assertRaises(ValueError):
            guiaremision_engine.generate(self._data(plate=''))
        with self.assertRaises(ValueError):
            guiaremision_engine.generate(self._data(items=[]))
        with self.assertRaises(ValueError):
            guiaremision_engine.generate(self._data(items=[{'description': 'x', 'quantity': 0}]))

    def test_carrier_identification(self):
        with self.assertRaises(ValueError):
            guiaremision_engine.generate(self._data(carrier_vat='123'))
        guiaremision_engine.generate(self._data(carrier_type='05', carrier_vat='1710034065'))

    def test_environment_in_key(self):
        key, xml = guiaremision_engine.generate(self._data(ambiente='2'))
        self.assertEqual(key[23], '2')
        self.assertIn(b'<ambiente>2</ambiente>', xml)
