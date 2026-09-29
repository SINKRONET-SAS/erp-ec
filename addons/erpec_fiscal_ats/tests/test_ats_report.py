"""DI25-04.2: agregador real del ATS. Conciliación contra documentos reales del ERP (no datos
inventados) y vista previa de faltantes con su documento origen."""
from lxml import etree
from pathlib import Path
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError

XSD_PATH = Path(__file__).resolve().parent.parent.parent / 'erpec_fiscal_native' / 'xsd' / 'at.xsd'


@tagged('post_install', '-at_install')
class AtsReportCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_manager').id)]})
        # Cada prueba usa una compañía propia: nunca agrega los documentos de la copia restaurada.
        company = self.env['res.company'].create({
            'name': 'Empresa ATS de ensayo', 'country_id': self.env.ref('base.ec').id,
            'currency_id': self.env.ref('base.USD').id})
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=[company.id]))
        self.env['account.chart.template'].try_loading('ec', company, install_demo=False)
        self.env.company.with_context(no_vat_validation=True).write({'vat': '1790012345001', 'street': 'Matriz de ensayo'})
        self.supplier = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Proveedor & ensayo', 'vat': '0992222222001', 'street': 'Dir. proveedor',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_ruc').id})
        self.customer = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Cliente & ensayo', 'vat': '0602846586001', 'street': 'Dir. cliente',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_ruc').id})
        group = self.env['account.tax.group'].create({'name': 'IVA de ensayo ATS', 'l10n_ec_type': 'vat15'})
        self.tax = self.env['account.tax'].create({'name': 'IVA 15 ensayo ATS', 'amount_type': 'percent', 'amount': 15,
                                                     'type_tax_use': 'purchase', 'tax_group_id': group.id})
        self.sale_tax = self.tax.copy({'type_tax_use': 'sale'})
        self.journal = self.env['account.journal'].search([('company_id', '=', self.env.company.id), ('type', '=', 'general')], limit=1)
        self.liability = self.env['account.account'].create({'name': 'Retenciones ATS por pagar', 'code': 'ECATS01', 'account_type': 'liability_current'})
        self.doc_type_invoice = self.env.ref('l10n_ec.ec_dt_01')

    def purchase(self, sustento='01', authorization='9' * 30, number='001-001-000000123', payment_code='20'):
        move = self.env['account.move'].create({
            'move_type': 'in_invoice', 'partner_id': self.supplier.id, 'invoice_date': '2026-09-11', 'date': '2026-09-11',
            'l10n_latam_document_type_id': self.doc_type_invoice.id, 'ec_purchase_sri_authorization': authorization,
            'ec_fiscal_payment_code': payment_code,
            'invoice_line_ids': [(0, 0, {
                'name': 'Insumo de ensayo', 'quantity': 1, 'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax.ids)], 'erpec_ats_sustento_code': sustento})],
        })
        move.l10n_latam_document_number = number
        move.action_post()
        return move

    def sale(self, number='001-001-000000456'):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.customer.id, 'invoice_date': '2026-09-12', 'date': '2026-09-12',
            'l10n_latam_document_type_id': self.doc_type_invoice.id,
            'invoice_line_ids': [(0, 0, {'name': 'Servicio de ensayo', 'quantity': 1, 'price_unit': 500.0, 'tax_ids': [(6, 0, self.sale_tax.ids)]})],
        })
        move.l10n_latam_document_number = number
        move.action_post()
        return move

    def authorize_native(self, move, access_key=None):
        from odoo.addons.erpec_fiscal_sri.models import _INTERNAL
        return self.env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=_INTERNAL).create({
            'move_id': move.id, 'access_key': access_key or ('1' * 49), 'ambiente': '1',
            'state': 'authorized', 'authorization_number': access_key or ('1' * 49), 'authorization_date': '2026-09-12',
        })

    def report(self, month='09'):
        return self.env['erpec.ats.report'].create({'company_id': self.env.company.id, 'year': 2026, 'month': month})

    def test_purchase_without_authority_or_sustento_is_a_missing_gap_not_a_guess(self):
        move = self.purchase(authorization=False)
        report = self.report()
        report.action_build()
        self.assertEqual(report.compra_count, 0)
        self.assertEqual(report.missing_count, 1)
        self.assertEqual(report.missing_ids.move_id, move)
        self.assertIn('autorización SRI', report.missing_ids.reason)

    def test_purchase_with_full_data_produces_a_schema_valid_compra_row(self):
        move = self.purchase()
        report = self.report()
        report.action_build()
        self.assertEqual(report.missing_count, 0)
        self.assertEqual(report.compra_count, 1)
        line = report.compra_ids
        self.assertEqual(line.move_id, move)
        self.assertEqual(line.cod_sustento, '01')
        self.assertEqual(round(line.base_imp_grav, 2), 1000.0)
        self.assertEqual(round(line.monto_iva, 2), 150.0)
        schema = etree.XMLSchema(etree.parse(str(XSD_PATH)))
        import base64
        doc = etree.fromstring(base64.b64decode(report.xml_preview))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_purchase_over_500_without_payment_code_is_a_missing_gap(self):
        # Regla real del DIMM (no del esquema, que la marca opcional), descubierta validando un XML
        # real de la demo contra el motor real: una compra cuya suma de bases+IVA/ICE supera USD 500
        # exige formasDePago. Sin ec_fiscal_payment_code, el documento queda en faltantes.
        move = self.purchase(payment_code=False)
        report = self.report()
        report.action_build()
        self.assertEqual(report.compra_count, 0)
        self.assertEqual(report.missing_count, 1)
        self.assertIn('forma de pago', report.missing_ids.reason)
        self.assertEqual(report.missing_ids.move_id, move)

    def test_purchase_over_500_with_payment_code_includes_forma_pago_in_the_xml(self):
        self.purchase(payment_code='20')
        report = self.report()
        report.action_build()
        self.assertEqual(report.compra_count, 1)
        schema = etree.XMLSchema(etree.parse(str(XSD_PATH)))
        import base64
        doc = etree.fromstring(base64.b64decode(report.xml_preview))
        self.assertTrue(schema.validate(doc), schema.error_log)
        self.assertEqual(doc.find('compras/detalleCompras/formasDePago/formaPago').text, '20')

    def test_purchase_retention_pulls_real_withholding_line_by_sri_code(self):
        # sri_code '9' = tramo 10% (Tabla 20 de la Ficha Técnica, ya documentado en
        # erpec.withholding.line.sri_code) -> valRetBien10, sin inventar ningún dato adicional.
        move = self.purchase()
        withholding = self.env['erpec.withholding'].create({
            'invoice_id': move.id, 'reference': 'RET-ATS-1', 'date': '2026-09-11', 'journal_id': self.journal.id,
            'line_ids': [(0, 0, {'name': 'Retención IVA 10%', 'kind': 'vat', 'sri_code': '9', 'base': 150.0, 'rate': 10, 'account_id': self.liability.id})],
        })
        withholding.action_post()
        report = self.report()
        report.action_build()
        self.assertEqual(report.compra_count, 1)
        self.assertEqual(round(report.compra_ids.val_ret_bien10, 2), 15.0)

    def test_sale_without_sri_authorization_is_a_missing_gap(self):
        move = self.sale()
        report = self.report()
        report.action_build()
        self.assertEqual(report.venta_count, 0)
        self.assertEqual(report.missing_count, 1)
        self.assertEqual(report.missing_ids.move_id, move)

    def test_authorized_sale_groups_into_a_venta_row_with_idcliente(self):
        move = self.sale()
        self.authorize_native(move)
        report = self.report()
        report.action_build()
        self.assertEqual(report.missing_count, 0)
        self.assertEqual(report.venta_count, 1)
        row = report.venta_ids
        self.assertEqual(row.id_cliente, '0602846586001')
        self.assertEqual(row.numero_comprobantes, 1)
        self.assertEqual(round(row.base_imp_grav, 2), 500.0)
        schema = etree.XMLSchema(etree.parse(str(XSD_PATH)))
        import base64
        doc = etree.fromstring(base64.b64decode(report.xml_preview))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_two_sales_to_the_same_client_are_grouped_into_one_row(self):
        first = self.sale(number='001-001-000000456')
        self.authorize_native(first, access_key='1' * 49)
        second = self.sale(number='001-001-000000457')
        self.authorize_native(second, access_key='2' * 49)
        report = self.report()
        report.action_build()
        self.assertEqual(report.venta_count, 1)
        self.assertEqual(report.venta_ids.numero_comprobantes, 2)
        self.assertEqual(round(report.venta_ids.base_imp_grav, 2), 1000.0)

    def test_cancelled_and_authorized_sale_is_an_anulado_row(self):
        # erpec_fiscal_connector bloquea deliberadamente button_draft/button_cancel una vez que el
        # comprobante tiene una emisión fiscal ("La cancelación contable no anula una solicitud
        # fiscal."): en este ERP, un comprobante YA autorizado nunca llega a state=cancel por la UI.
        # anulados solo sería alcanzable por una migración de datos legados. Se fuerza el estado por
        # SQL únicamente para probar que _gather_anulados construye la fila correctamente si ese
        # dato llegara a existir; no se afirma que este camino sea alcanzable desde la interfaz.
        move = self.sale()
        self.authorize_native(move)
        self.env.cr.execute("UPDATE account_move SET state='cancel' WHERE id=%s", [move.id])
        move.invalidate_recordset(['state'])
        report = self.report()
        report.action_build()
        self.assertEqual(report.anulado_count, 1)
        self.assertEqual(report.anulado_ids.move_id, move)
        self.assertEqual(report.anulado_ids.secuencial_inicio, report.anulado_ids.secuencial_fin)

    def test_cancelled_but_never_authorized_sale_is_not_reported_at_all(self):
        move = self.sale()
        move.button_draft()
        move.button_cancel()
        report = self.report()
        report.action_build()
        self.assertEqual(report.anulado_count, 0)
        self.assertEqual(report.missing_count, 0)

    def test_period_is_unique_per_company(self):
        self.report()
        with self.assertRaises(Exception):
            self.env['erpec.ats.report'].create({'company_id': self.env.company.id, 'year': 2026, 'month': '09'}).flush_recordset()

    def test_reset_clears_lines_and_returns_to_draft(self):
        self.purchase()
        report = self.report()
        report.action_build()
        self.assertEqual(report.state, 'built')
        report.action_reset()
        self.assertEqual(report.state, 'draft')
        self.assertEqual(report.compra_count, 0)

    def test_authorization_field_only_applies_to_purchase_invoices(self):
        move = self.sale()
        with self.assertRaises(ValidationError):
            move.write({'ec_purchase_sri_authorization': '123'})

    def test_invalid_header_removes_previous_download_and_reports_reason(self):
        self.purchase()
        report = self.report()
        report.action_build()
        self.assertTrue(report.xml_preview)
        self.env.company.name = 'Empresa & datos no admitidos'
        report.action_build()
        self.assertFalse(report.xml_preview)
        self.assertFalse(report.xml_filename)
        self.assertIn('El XML de ensayo no se generó', report.build_notice)
        self.assertEqual(report.compra_count, 1)

    def test_negative_sale_does_not_offer_schema_invalid_xml(self):
        from unittest.mock import patch
        move = self.sale()
        self.authorize_native(move)
        report = self.report()
        first, following = __import__('datetime').date(2026, 9, 1), __import__('datetime').date(2026, 10, 1)
        rows, missing = report._gather_ventas(first, following)
        rows[0]['base_imp_grav'] = -10.0
        with patch.object(type(report), '_gather_ventas', return_value=(rows, missing)):
            report.action_build()
        self.assertFalse(report.xml_preview)
        self.assertIn('El XML de ensayo no se generó', report.build_notice)
        self.assertEqual(report.venta_ids.base_imp_grav, -10.0)
