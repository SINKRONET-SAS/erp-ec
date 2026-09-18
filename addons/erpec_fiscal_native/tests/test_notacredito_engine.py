"""Pruebas del motor de generación XML de nota de crédito (sin firma ni transmisión, igual que
test_native.py para factura); validación real contra NotaCredito_V1.1.0.xsd, no simulada."""
from odoo.tests import TransactionCase, tagged

from .. import notacredito_engine


@tagged('post_install', '-at_install')
class NotaCreditoEngineCase(TransactionCase):
    def _data(self, **overrides):
        data = {
            'date': '2026-09-18', 'number': '001-001-000000012', 'numeric': '12345678',
            'issuer_vat': '1793235327001', 'issuer_name': 'ENSAYO SA', 'issuer_address': 'Matriz',
            'buyer_type': '05', 'buyer_vat': '1710034065', 'buyer_name': 'Cliente Ensayo', 'buyer_address': 'Dir cliente',
            'accounting': 'SI', 'modified_type': '01', 'modified_number': '001-001-000000005',
            'modified_date': '2026-09-01', 'reason': 'Devolución de mercadería',
            'total': 115.0,
            'items': [{'description': 'Servicio', 'quantity': 1, 'unit': 100, 'discount': 0,
                       'rate': 15, 'subtotal': 100.0, 'tax': 15.0}],
        }
        data.update(overrides)
        return data

    def test_generates_valid_xml_against_official_schema(self):
        key, xml = notacredito_engine.generate(self._data())
        self.assertEqual(len(key), 49)
        self.assertEqual(key[8:10], '04')
        self.assertIn(b'<notaCredito', xml)
        self.assertIn(b'<codDocModificado>01</codDocModificado>', xml)
        self.assertIn(b'<numDocModificado>001-001-000000005</numDocModificado>', xml)
        self.assertIn(b'<valorModificacion>115.00</valorModificacion>', xml)

    def test_access_key_doc_type_is_04_rest_matches_factura(self):
        # Estructura de la clave: fecha(8) + tipoComprobante(2) + ruc(13) + ambiente(1) +
        # estab-ptoemi-secuencial(15) + codigoNumerico(8) + tipoEmision(1) + verificador(1).
        from ..engine import access_key
        factura_key = access_key('2026-09-18', '1793235327001', '001-001-000000012', '12345678')
        nc_key, _xml = notacredito_engine.generate(self._data())
        self.assertEqual(factura_key[:8], nc_key[:8])
        self.assertEqual(factura_key[8:10], '01')
        self.assertEqual(nc_key[8:10], '04')
        self.assertEqual(factura_key[10:48], nc_key[10:48])

    def test_requires_modified_document_reference(self):
        with self.assertRaises(ValueError):
            notacredito_engine.generate(self._data(modified_number=False))
        with self.assertRaises(ValueError):
            notacredito_engine.generate(self._data(modified_type=False))

    def test_requires_reason(self):
        with self.assertRaises(ValueError):
            notacredito_engine.generate(self._data(reason='   '))

    def test_rejects_mismatched_total(self):
        with self.assertRaises(ValueError):
            notacredito_engine.generate(self._data(total=999.0))

    def test_zero_rate_item_valid(self):
        key, xml = notacredito_engine.generate(self._data(
            total=100.0, items=[{'description': 'Exento', 'quantity': 1, 'unit': 100, 'discount': 0,
                                  'rate': 0, 'subtotal': 100.0, 'tax': 0.0}]))
        self.assertIn(b'<codigoPorcentaje>0</codigoPorcentaje>', xml)
