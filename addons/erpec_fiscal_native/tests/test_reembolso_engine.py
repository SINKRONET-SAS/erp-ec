"""Factura con IVA no objeto/exento y bloque de reembolsos; validación real contra el XSD oficial."""
from odoo.tests import TransactionCase, tagged

from .. import engine


@tagged('post_install', '-at_install')
class ReimbursementEngineCase(TransactionCase):
    def _data(self, **overrides):
        data = {
            'date': '2026-09-18', 'number': '001-001-000000010', 'numeric': '12345678', 'issuer_vat': '1709053506001',
            'issuer_name': 'E', 'issuer_address': 'M', 'accounting': 'NO', 'buyer_type': '05', 'buyer_vat': '1710034065',
            'buyer_name': 'C', 'buyer_address': 'D', 'payment': '01', 'total': 150.0,
            'items': [{'code': 'R1', 'description': 'Reembolso', 'quantity': 1, 'unit': 150, 'discount': 0, 'rate': 'no_object', 'subtotal': 150.0, 'tax': 0.0}],
            'reimbursements': [{'provider_type': '04', 'provider_vat': '1793235327001', 'provider_kind': '02', 'doc_type': '01',
                                'doc_number': '001-002-000000008', 'doc_date': '2026-09-10',
                                'authorization': '1009202601179323532700110010020000000081234567814',
                                'taxes': [{'rate_code': '4', 'rate': 15, 'base': 130.43, 'amount': 19.57}]}],
        }
        data.update(overrides)
        return data

    def test_reimbursement_block_and_totals(self):
        _key, xml = engine.generate(self._data())
        self.assertIn(b'<codDocReembolso>41</codDocReembolso>', xml)
        self.assertIn(b'<totalComprobantesReembolso>150.00</totalComprobantesReembolso>', xml)
        self.assertIn(b'<totalImpuestoReembolso>19.57</totalImpuestoReembolso>', xml)

    def test_special_vat_codes(self):
        for kind, code in (('no_object', b'<codigoPorcentaje>6</codigoPorcentaje>'), ('exempt', b'<codigoPorcentaje>7</codigoPorcentaje>')):
            item = {'code': 'X', 'description': 'x', 'quantity': 1, 'unit': 10, 'discount': 0, 'rate': kind, 'subtotal': 10.0, 'tax': 0.0}
            _key, xml = engine.generate(self._data(total=10.0, items=[item], reimbursements=[]))
            self.assertIn(code, xml)

    def test_rejects_invalid_reimbursement_data(self):
        bad = self._data()
        bad['reimbursements'][0]['authorization'] = '12'
        with self.assertRaises(ValueError):
            engine.generate(bad)
        with self.assertRaises(ValueError):
            engine.generate(self._data(total=100.0, items=[{'code': 'R', 'description': 'x', 'quantity': 1, 'unit': 100, 'discount': 0,
                                                            'rate': 'no_object', 'subtotal': 100.0, 'tax': 0.0}]))
