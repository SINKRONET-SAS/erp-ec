"""Pruebas de erpec.fiscal.emission para nota de crédito: firma real (certificado sintético) y
transmisión SOAP simulada (mismo patrón que test_emission.py para factura). La nota de crédito
se crea con el mecanismo nativo de Odoo (account.move._reverse_moves), no a mano."""
import base64
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC, P12_PASSWORD, _build_certificate
from .. import sri_client


@tagged('post_install', '-at_install')
class NotaCreditoEmissionCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.env.company._onchange_country_id()
        self.env.company.with_context(no_vat_validation=True).write({
            'vat': ISSUER_RUC, 'street': 'Matriz de ensayo', 'ec_native_ordinary': True, 'ec_native_accounting': 'SI'})
        self.partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Cliente de ensayo NC', 'vat': ISSUER_RUC, 'street': 'Dirección de ensayo',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ec.ec_ruc').id})
        group = self.env['account.tax.group'].create({'name': 'IVA de ensayo NC', 'l10n_ec_type': 'vat15'})
        self.tax = self.env['account.tax'].create({'name': 'IVA 15 ensayo NC', 'amount_type': 'percent', 'amount': 15,
                                                     'type_tax_use': 'sale', 'tax_group_id': group.id})
        self.journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1)
        self.journal.l10n_latam_use_documents = True
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'journal_id': self.journal.id, 'partner_id': self.partner.id,
            'invoice_date': '2026-09-01', 'date': '2026-09-01', 'ec_fiscal_payment_code': '20',
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_01').id,
            'invoice_line_ids': [(0, 0, {'name': 'Servicio de ensayo', 'quantity': 1, 'price_unit': 100, 'tax_ids': [(6, 0, self.tax.ids)]})]})
        self.invoice.l10n_latam_document_number = '001-001-000000005'
        self.invoice.action_post()
        credit_notes = self.invoice._reverse_moves([{
            'ref': 'Devolución de ensayo', 'invoice_date': '2026-09-18',
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_04').id,
        }], cancel=False)
        self.credit_note = credit_notes
        self.credit_note.l10n_latam_document_number = '001-001-000000012'
        self.credit_note.action_post()
        p12, _key, _cert, _now = _build_certificate()
        self.certificate = self.env['erpec.fiscal.certificate'].sudo().create({
            'company_id': self.env.company.id, 'p12_file': base64.b64encode(p12), 'p12_password': P12_PASSWORD.decode()})
        self.certificate.action_verify()

    def test_credit_note_requires_reversed_entry(self):
        standalone = self.env['account.move'].create({
            'move_type': 'out_refund', 'journal_id': self.journal.id, 'partner_id': self.partner.id,
            'invoice_date': '2026-09-18', 'date': '2026-09-18',
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_04').id,
            'invoice_line_ids': [(0, 0, {'name': 'Sin origen', 'quantity': 1, 'price_unit': 50, 'tax_ids': [(6, 0, self.tax.ids)]})]})
        standalone.l10n_latam_document_number = '001-001-000000099'
        standalone.action_post()
        with self.assertRaisesRegex(ValidationError, 'Añadir nota de crédito'):
            standalone.action_native_emit()

    def test_emit_signs_credit_note_and_creates_emission(self):
        result = self.credit_note.action_native_emit()
        emission = self.env['erpec.fiscal.emission'].browse(result['res_id'])
        self.assertEqual(emission.state, 'signed')
        self.assertEqual(emission.access_key[8:10], '04')
        self.assertTrue(emission.xml_signed)
        xml_bytes = base64.b64decode(emission.xml_unsigned)
        self.assertIn(b'<numDocModificado>001-001-000000005</numDocModificado>', xml_bytes)
        self.assertIn('Devolución de ensayo'.encode('utf-8'), xml_bytes)

    def _authorized_response(self, access_key):
        nota = ('<notaCredito id="comprobante" version="1.1.0"><infoTributaria><claveAcceso>' + access_key +
                '</claveAcceso></infoTributaria><infoNotaCredito><razonSocialComprador>Cliente de ensayo NC</razonSocialComprador>'
                '<identificacionComprador>' + ISSUER_RUC + '</identificacionComprador>'
                '<fechaEmision>18/09/2026</fechaEmision><totalSinImpuestos>100.00</totalSinImpuestos>'
                '<valorModificacion>115.00</valorModificacion><numDocModificado>001-001-000000005</numDocModificado>'
                '<codDocModificado>01</codDocModificado><fechaEmisionDocSustento>01/09/2026</fechaEmisionDocSustento>'
                '<motivo>Devolución de ensayo</motivo><totalConImpuestos/></infoNotaCredito><detalles/></notaCredito>')
        return {'comprobante': nota.encode('utf-8'), 'numero': '9876543210', 'fecha': '2026-09-18T10:00:00-05:00'}

    def test_full_flow_to_authorized_builds_credit_note_ride(self):
        emission = self.env['erpec.fiscal.emission'].browse(self.credit_note.action_native_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('RECIBIDA', [])):
            emission.action_process()
        emission._save(next_attempt=False)
        with patch.object(sri_client, 'consultar_autorizacion',
                           return_value=('AUTORIZADO', self._authorized_response(emission.access_key), [])):
            emission.action_process()
        self.assertEqual(emission.state, 'authorized')
        self.assertTrue(emission.ride_pdf)
        self.assertTrue(base64.b64decode(emission.ride_pdf).startswith(b'%PDF'))

    def test_invoice_and_credit_note_are_independent_emissions(self):
        invoice_emission = self.env['erpec.fiscal.emission'].browse(self.invoice.action_native_emit()['res_id'])
        credit_emission = self.env['erpec.fiscal.emission'].browse(self.credit_note.action_native_emit()['res_id'])
        self.assertNotEqual(invoice_emission, credit_emission)
        self.assertEqual(invoice_emission.access_key[8:10], '01')
        self.assertEqual(credit_emission.access_key[8:10], '04')

    def _debit_note(self):
        note = self.invoice.with_context(include_business_fields=True).copy(default={
            'ref': 'Intereses de mora', 'date': '2026-09-18', 'invoice_date': '2026-09-18',
            'debit_origin_id': self.invoice.id, 'invoice_payment_term_id': None,
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_05').id})
        note.l10n_latam_document_number = '001-001-000000021'
        note.action_post()
        return note

    def test_debit_note_is_signed_with_cod_doc_05(self):
        emission = self.env['erpec.fiscal.emission'].browse(self._debit_note().action_native_emit()['res_id'])
        self.assertEqual(emission.state, 'signed')
        self.assertEqual(emission.access_key[8:10], '05')
        xml_bytes = base64.b64decode(emission.xml_unsigned)
        self.assertIn(b'<notaDebito', xml_bytes)
        self.assertIn(b'<numDocModificado>001-001-000000005</numDocModificado>', xml_bytes)

    def test_debit_note_full_flow_builds_debit_note_ride(self):
        note = self._debit_note()
        emission = self.env['erpec.fiscal.emission'].browse(note.action_native_emit()['res_id'])
        with patch.object(sri_client, 'enviar_recepcion', return_value=('RECIBIDA', [])):
            emission.action_process()
        emission._save(next_attempt=False)
        comprobante = ('<notaDebito id="comprobante" version="1.0.0"><infoTributaria><claveAcceso>' + emission.access_key +
                       '</claveAcceso><estab>001</estab><ptoEmi>001</ptoEmi><secuencial>000000021</secuencial></infoTributaria>'
                       '<infoNotaDebito><razonSocialComprador>Cliente</razonSocialComprador><identificacionComprador>1</identificacionComprador>'
                       '<fechaEmision>18/09/2026</fechaEmision><codDocModificado>01</codDocModificado>'
                       '<numDocModificado>001-001-000000005</numDocModificado><fechaEmisionDocSustento>01/09/2026</fechaEmisionDocSustento>'
                       '<totalSinImpuestos>100.00</totalSinImpuestos><impuestos><impuesto><codigo>2</codigo><codigoPorcentaje>4</codigoPorcentaje>'
                       '<valor>15.00</valor></impuesto></impuestos><valorTotal>115.00</valorTotal></infoNotaDebito>'
                       '<motivos><motivo><razon>Intereses de mora</razon><valor>100.00</valor></motivo></motivos></notaDebito>')
        answer = {'comprobante': comprobante.encode('utf-8'), 'numero': '1234567890', 'fecha': '2026-09-18T10:00:00-05:00'}
        with patch.object(sri_client, 'consultar_autorizacion', return_value=('AUTORIZADO', answer, [])):
            emission.action_process()
        self.assertEqual(emission.state, 'authorized')
        self.assertTrue(base64.b64decode(emission.ride_pdf).startswith(b'%PDF'))
