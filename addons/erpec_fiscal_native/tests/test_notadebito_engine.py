"""Motor XML de nota de débito; validación real contra NotaDebito_V1.0.0.xsd, sin firma ni red."""
from odoo.tests import TransactionCase, tagged

from .. import notadebito_engine


@tagged('post_install', '-at_install')
class NotaDebitoEngineCase(TransactionCase):
    def _data(self, **overrides):
        data = {
            'date': '2026-09-18', 'number': '001-001-000000021', 'numeric': '12345678',
            'issuer_vat': '1793235327001', 'issuer_name': 'ENSAYO SA', 'issuer_address': 'Matriz',
            'buyer_type': '05', 'buyer_vat': '1710034065', 'buyer_name': 'Cliente Ensayo', 'buyer_address': 'Dir cliente',
            'accounting': 'SI', 'modified_type': '01', 'modified_number': '001-001-000000005',
            'modified_date': '2026-09-01', 'payment': '20', 'total': 115.0,
            'items': [{'description': 'Intereses de mora', 'subtotal': 100.0, 'rate': 15, 'tax': 15.0}],
        }
        data.update(overrides)
        return data

    def test_generates_valid_xml_against_official_schema(self):
        key, xml = notadebito_engine.generate(self._data())
        self.assertEqual(len(key), 49)
        self.assertEqual(key[8:10], '05')
        self.assertIn(b'<notaDebito', xml)
        self.assertIn(b'<razon>Intereses de mora</razon>', xml)
        self.assertIn(b'<valorTotal>115.00</valorTotal>', xml)
        self.assertIn(b'<formaPago>20</formaPago>', xml)

    def test_payment_block_is_optional(self):
        _key, xml = notadebito_engine.generate(self._data(payment=False))
        self.assertNotIn(b'<pagos>', xml)

    def test_requires_modified_document_and_reason_per_motive(self):
        with self.assertRaises(ValueError):
            notadebito_engine.generate(self._data(modified_number=False))
        with self.assertRaises(ValueError):
            notadebito_engine.generate(self._data(items=[{'description': ' ', 'subtotal': 100.0, 'rate': 15, 'tax': 15.0}]))

    def test_rejects_mismatched_total_and_tax(self):
        with self.assertRaises(ValueError):
            notadebito_engine.generate(self._data(total=999.0))
        with self.assertRaises(ValueError):
            notadebito_engine.generate(self._data(items=[{'description': 'x', 'subtotal': 100.0, 'rate': 15, 'tax': 1.0}]))

    def test_mixed_rates_are_grouped(self):
        _key, xml = notadebito_engine.generate(self._data(total=215.0, items=[
            {'description': 'Con IVA', 'subtotal': 100.0, 'rate': 15, 'tax': 15.0},
            {'description': 'Sin IVA', 'subtotal': 100.0, 'rate': 0, 'tax': 0.0}]))
        self.assertEqual(xml.count(b'<impuesto>'), 2)
