"""Pruebas del código de sustento tributario ATS (Catálogo ATS, Tabla 5) resuelto
automáticamente desde el caso aplicable del tercero y del producto, sobre líneas reales de
factura de compra."""
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class AtsSustentoCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.reference = self.env['erpec.tax.reference'].create({
            'name': 'Referencia sintética ATS, no normativa', 'family': 'ENSAYO-ATS',
            'code': 'TX-ATS', 'version': 'ensayo', 'source_url': 'https://www.sri.gob.ec/facturacion-electronica'})
        self.account = self.env['account.account'].create({'name': 'Cuenta caso ATS ensayo', 'code': 'TXATS01',
            'account_type': 'liability_current', 'company_ids': [Command.set(self.company.ids)]})
        self.tax = self.env['account.tax'].create({
            'name': 'Detalle sintético ATS', 'amount': 10, 'type_tax_use': 'purchase', 'erpec_reference_id': self.reference.id})
        (self.tax.invoice_repartition_line_ids | self.tax.refund_repartition_line_ids).filtered(
            lambda line: line.repartition_type == 'tax').account_id = self.account
        self.partner_type = self.env['erpec.tax.classification'].create({'name': 'Proveedor ATS ensayo', 'kind': 'partner'})
        self.product_type = self.env['erpec.tax.classification'].create({'name': 'Producto ATS ensayo', 'kind': 'product'})
        self.partner = self.env['res.partner'].create({'name': 'Tercero ATS', 'erpec_tax_type_id': self.partner_type.id})
        self.product = self.env['product.product'].create({'name': 'Producto ATS', 'erpec_tax_type_id': self.product_type.id,
            'supplier_taxes_id': [Command.clear()], 'taxes_id': [Command.clear()]})
        self.left_policy = self.env['erpec.tax.policy'].create({'name': 'Plan ATS del tercero'})
        self.right_policy = self.env['erpec.tax.policy'].create({'name': 'Plan ATS del producto'})
        self.left_case = self.env['erpec.tax.case'].create({'name': 'Caso ATS tercero', 'policy_id': self.left_policy.id,
            'tax_ids': [Command.set(self.tax.ids)], 'ats_sustento_code': '02'})
        self.right_case = self.env['erpec.tax.case'].create({'name': 'Caso ATS producto', 'policy_id': self.right_policy.id,
            'tax_ids': [Command.set(self.tax.ids)], 'ats_sustento_code': '02'})
        self.partner.erpec_policy_ids = self.left_policy
        self.product.erpec_policy_ids = self.right_policy

    def _make_bill(self, price=100):
        return self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': self.partner.id,
            'invoice_line_ids': [Command.create({'product_id': self.product.id, 'quantity': 1, 'price_unit': price})]})

    def test_case_rejects_sustento_on_sale_operation(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.tax.case'].create({'name': 'Caso venta con sustento', 'policy_id': self.left_policy.id,
                'operation': 'sale', 'tax_ids': [Command.set(self.tax.ids)], 'ats_sustento_code': '02'})

    def test_intersection_resolves_matching_sustento_code(self):
        result = self.env['erpec.tax.policy']._intersection(self.company, 'purchase', self.partner, self.product)
        self.assertEqual(result['sustento_code'], '02')

    def test_intersection_leaves_sustento_blank_when_cases_disagree(self):
        self.right_case.ats_sustento_code = '06'
        result = self.env['erpec.tax.policy']._intersection(self.company, 'purchase', self.partner, self.product)
        self.assertFalse(result['sustento_code'])
        self.assertIn('ambiguo', result['message'])

    def test_intersection_leaves_sustento_blank_when_not_configured(self):
        self.left_case.ats_sustento_code = False
        self.right_case.ats_sustento_code = False
        result = self.env['erpec.tax.policy']._intersection(self.company, 'purchase', self.partner, self.product)
        self.assertFalse(result['sustento_code'])
        self.assertIn('Falta configurar', result['message'])

    def test_sale_operation_never_populates_sustento_code(self):
        result = self.env['erpec.tax.policy']._intersection(self.company, 'sale', self.partner, self.product)
        self.assertFalse(result['sustento_code'])

    def test_bill_line_gets_real_sustento_code_from_intersection(self):
        bill = self._make_bill()
        self.assertEqual(bill.invoice_line_ids.erpec_ats_sustento_code, '02')

    def test_sale_invoice_line_never_gets_sustento_code(self):
        self.tax.type_tax_use = 'sale'
        self.left_case.write({'ats_sustento_code': False, 'operation': 'sale', 'tax_ids': [Command.set(self.tax.ids)]})
        self.right_case.write({'ats_sustento_code': False, 'operation': 'sale', 'tax_ids': [Command.set(self.tax.ids)]})
        invoice = self.env['account.move'].create({'move_type': 'out_invoice', 'partner_id': self.partner.id,
            'invoice_line_ids': [Command.create({'product_id': self.product.id, 'quantity': 1, 'price_unit': 100})]})
        self.assertFalse(invoice.invoice_line_ids.erpec_ats_sustento_code)

    def test_reading_the_plan_notice_never_overwrites_a_manual_sustento(self):
        # DI26-02: antes, leer el aviso informativo recalculaba y guardaba el sustento del plan sobre el valor manual.
        bill = self._make_bill()
        line = bill.invoice_line_ids
        self.assertEqual(line.erpec_ats_sustento_code, '02')
        line.erpec_ats_sustento_code = '01'
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertTrue(line.erpec_tax_notice is not None)
        self.assertTrue(line.erpec_retention_ids is not None)
        self.env.flush_all()
        self.env.cr.execute('SELECT erpec_ats_sustento_code FROM account_move_line WHERE id=%s', [line.id])
        self.assertEqual(self.env.cr.fetchone()[0], '01')

    def test_manual_override_persists_when_intersection_cannot_resolve(self):
        bill = self._make_bill()
        self.assertEqual(bill.invoice_line_ids.erpec_ats_sustento_code, '02')
        self.right_case.ats_sustento_code = '06'
        bill.invoice_line_ids.erpec_ats_sustento_code = '01'
        bill.invoice_line_ids._compute_erpec_selection()
        bill.invoice_line_ids._compute_erpec_sustento()
        self.assertEqual(bill.invoice_line_ids.erpec_ats_sustento_code, '01')
