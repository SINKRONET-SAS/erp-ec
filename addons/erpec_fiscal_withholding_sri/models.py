"""Comprobante de retención electrónico (codDoc 07): firma XAdES y transmisión al SRI de las
retenciones emitidas a proveedores. `erpec.withholding` sigue siendo el registro contable; este
módulo añade los datos SRI estructurados y la emisión nativa reutilizando erpec.fiscal.emission."""
import base64
import re
import secrets

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.erpec_fiscal_native import retencion_engine, retention_catalog, xades
from odoo.addons.erpec_fiscal_native.ats_catalog import SUPPORT_CODES
from odoo.addons.erpec_fiscal_sri.models import _INTERNAL as _SRI_INTERNAL

SEQUENCE_CODE = 'erpec.fiscal.withholding.sri'
SRI_FIELDS = {'sri_sustento_code', 'sri_related_party', 'sri_payment_code', 'sri_support_authorization'}


class Company(models.Model):
    _inherit = 'res.company'

    ec_withholding_entity = fields.Char('Establecimiento de retenciones', size=3, default='001')
    ec_withholding_emission = fields.Char('Punto de emisión de retenciones', size=3, default='001')
    ec_agent_resolution = fields.Char('Resolución de agente de retención', size=8,
                                      help='Solo dígitos (hasta 8), tal como consta en el RUC; se imprime en infoTributaria/agenteRetencion.')

    @api.constrains('ec_withholding_entity', 'ec_withholding_emission', 'ec_agent_resolution')
    def _check_withholding_sri(self):
        for company in self:
            for value in (company.ec_withholding_entity, company.ec_withholding_emission):
                if value and not re.fullmatch(r'[0-9]{3}', value):
                    raise ValidationError('Establecimiento y punto de emisión requieren tres dígitos.')
            if company.ec_agent_resolution and not re.fullmatch(r'[0-9]{1,8}', company.ec_agent_resolution):
                raise ValidationError('La resolución de agente de retención solo admite dígitos (máximo 8).')


class Withholding(models.Model):
    _inherit = 'erpec.withholding'

    sri_number = fields.Char('Número SRI de la retención', readonly=True, copy=False)
    sri_sustento_code = fields.Selection([(code, '%s - %s' % (code, label)) for code, label in SUPPORT_CODES.items()],
                                         string='Sustento tributario (ATS)')
    sri_related_party = fields.Selection([('NO', 'No'), ('SI', 'Sí')], string='Parte relacionada', default='NO', required=True)
    sri_payment_code = fields.Selection([('01', '01 Sin utilización del sistema financiero'), ('20', '20 Otros con utilización del sistema financiero'),
                                         ('16', '16 Tarjeta de débito'), ('19', '19 Tarjeta de crédito'), ('17', '17 Dinero electrónico')],
                                        string='Forma de pago del sustento', default='20', required=True)
    sri_support_authorization = fields.Char('Autorización del comprobante de sustento (10 a 49 dígitos)')
    emission_ids = fields.One2many('erpec.fiscal.emission', 'withholding_id', string='Emisiones SRI', copy=False)

    def write(self, values):
        # Los datos SRI se completan DESPUÉS de contabilizar y antes de emitir; el resto del registro
        # contable sigue siendo inmutable (lo controla erpec_withholding_accounting).
        if values and set(values) <= SRI_FIELDS:
            if any(record.sri_number for record in self):
                raise ValidationError('La retención ya fue emitida al SRI; sus datos electrónicos no se modifican.')
            return models.Model.write(self, values)
        return super().write(values)

    def _sri_ambiente(self):
        return self.journal_id.ec_sri_ambiente or '1'

    def _sri_numbers(self):
        """Establecimiento y punto de emisión: los del punto SRI del diario de retenciones si existe,
        si no los predeterminados de la empresa."""
        point = self.journal_id.ec_point_id
        company = self.company_id
        if point:
            return point.establishment, point.emission
        return company.ec_withholding_entity or '001', company.ec_withholding_emission or '001'

    def _next_sri_number(self):
        # Un consecutivo por empresa Y por ambiente: pruebas y producción nunca comparten numeración.
        self.ensure_one()
        company = self.company_id
        entity, emission = self._sri_numbers()
        code = '%s.%s.%s.%s' % (SEQUENCE_CODE, self._sri_ambiente(), entity, emission)
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'Retenciones SRI %s-%s (%s)' % (entity, emission, 'pruebas' if self._sri_ambiente() == '1' else 'producción'),
                'code': code, 'company_id': company.id,
                'padding': 9, 'number_next': 1, 'implementation': 'no_gap'})
        return '%s-%s-%s' % (entity, emission, sequence.next_by_id())

    def _identification_code(self, partner):
        kinds = {self.env.ref('l10n_ec.ec_ruc'): '04', self.env.ref('l10n_ec.ec_dni'): '05', self.env.ref('l10n_ec.ec_passport'): '06'}
        return kinds.get(partner.l10n_latam_identification_type_id, '')

    def _gather_sri_data(self):
        self.ensure_one()
        company, invoice = self.company_id, self.invoice_id
        partner = invoice.partner_id.commercial_partner_id
        if self.direction != 'issued' or invoice.move_type != 'in_invoice':
            raise ValidationError('Solo se emiten electrónicamente las retenciones a proveedores (factura de compra).')
        if self.state != 'posted':
            raise ValidationError('Contabiliza la retención antes de emitirla electrónicamente.')
        if company.country_id.code != 'EC' or self.currency_id.name != 'USD':
            raise ValidationError('Se requiere una empresa de Ecuador y USD.')
        if not self.sri_sustento_code:
            raise ValidationError('Indica el sustento tributario (ATS) de la compra.')
        company._check_regime_supported()
        if not company.ec_native_ordinary or not company.ec_native_accounting:
            raise ValidationError('Completa el perfil fiscal de la empresa (perfil ordinario y obligación contable).')
        subject_type = self._identification_code(partner)
        taxes = []
        for line in invoice.invoice_line_ids.filtered(lambda row: row.display_type == 'product'):
            tax = line.tax_ids
            group = tax.tax_group_id.l10n_ec_type if len(tax) == 1 else ''
            if group not in ('vat15', 'zero_vat'):
                raise ValidationError('El sustento debe tener una tarifa de IVA 0 o 15 por línea.')
            entry = next((item for item in taxes if item['rate'] == tax.amount), None)
            if not entry:
                entry = {'code': '2', 'percent_code': '4' if tax.amount == 15 else '0', 'rate': tax.amount, 'base': 0, 'amount': 0}
                taxes.append(entry)
            entry['base'] += line.price_subtotal
            entry['amount'] += line.price_total - line.price_subtotal
        support = {
            'sustento_code': self.sri_sustento_code, 'doc_type': '01', 'doc_number': invoice.l10n_latam_document_number or '',
            'doc_date': str(invoice.invoice_date), 'accounting_date': str(invoice.date),
            'doc_authorization': self.sri_support_authorization or False,
            'untaxed': invoice.amount_untaxed, 'total': invoice.amount_total, 'payment': self.sri_payment_code, 'taxes': taxes}
        natural = subject_type == '05' or (subject_type == '04' and (partner.vat or '')[2:3] in '012345')
        return {
            'date': str(self.date), 'ambiente': self._sri_ambiente(),
            'establishment_address': self.journal_id.ec_point_id.establishment_address or False, 'issuer_vat': company.vat, 'issuer_name': company.name, 'issuer_address': company.street,
            'accounting': company.ec_native_accounting, 'agent_resolution': company.ec_agent_resolution or False,
            'subject_type': subject_type, 'subject_vat': partner.vat, 'subject_name': partner.name,
            'subject_kind': '01' if natural else '02', 'related_party': self.sri_related_party, 'support': support,
            'lines': [{'kind': line.kind, 'sri_code': line.sri_code, 'base': line.base, 'rate': line.rate, 'amount': line.amount}
                      for line in self.line_ids]}

    def action_sri_emit(self):
        self.ensure_one()
        self.check_access('write')
        if self.emission_ids:
            return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission', 'res_id': self.emission_ids[0].id, 'view_mode': 'form'}
        certificate = self.env['erpec.fiscal.certificate'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not certificate or not certificate.verified:
            raise ValidationError('Configura y verifica primero el certificado de firma electrónica de esta empresa.')
        self.journal_id._sri_check_ambiente()
        data = self._gather_sri_data()
        number = self.sri_number or self._next_sri_number()
        data['number'] = number
        data['numeric'] = str(secrets.randbelow(10**8)).zfill(8)
        try:
            access_key, xml_unsigned = retencion_engine.generate(data)
            xml_signed = xades.sign(xml_unsigned, *certificate._signing_material(), self.company_id.vat)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        emission = self.env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=_SRI_INTERNAL).create({
            'withholding_id': self.id, 'access_key': access_key, 'ambiente': data['ambiente'],
            'xml_unsigned': base64.b64encode(xml_unsigned), 'xml_signed': base64.b64encode(xml_signed),
            'state': 'signed', 'message': 'Firmada. Procesar la cola para transmitir al SRI.'})
        # Solo se fija el número tras crear la emisión: el consecutivo ya consumido no se reutiliza.
        self.env.cr.execute('UPDATE erpec_withholding SET sri_number=%s WHERE id=%s', [number, self.id])
        self.invalidate_recordset(['sri_number'])
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission', 'res_id': emission.id, 'view_mode': 'form'}


class WithholdingLine(models.Model):
    _inherit = 'erpec.withholding.line'

    sri_code = fields.Char('Código SRI de retención', size=5,
                           help='Renta: código del catálogo ATS vigente (p. ej. 312 = 2%). IVA: 9=10%, 10=20%, 1=30%, 11=50%, 2=70%, 3=100%, 7=0% (Tabla 20 de la Ficha Técnica).')
    sri_code_label = fields.Char('Concepto del catálogo', compute='_compute_sri_code_label')

    @api.depends('sri_code', 'kind')
    def _compute_sri_code_label(self):
        for line in self:
            line.sri_code_label = retention_catalog.income_label(line.sri_code) if line.kind == 'income' else ''

    @api.onchange('sri_code', 'kind')
    def _onchange_sri_code(self):
        # Sugerencia desde el catálogo vigente: si el código tiene una sola tarifa, se propone.
        if self.kind == 'income' and self.sri_code:
            rates = retention_catalog.income_rates(self.sri_code)
            if len(rates) == 1:
                self.rate = rates[0]
            if not self.name or self.name == 'Concepto':
                self.name = retention_catalog.income_label(self.sri_code) or self.name


class Emission(models.Model):
    _inherit = 'erpec.fiscal.emission'

    withholding_id = fields.Many2one('erpec.withholding', string='Retención', check_company=True, ondelete='restrict')
    _sql_constraints = [('one_withholding', 'unique(withholding_id)', 'La retención ya tiene una emisión nativa.')]

    @api.depends('withholding_id.company_id')
    def _compute_company_id(self):
        super()._compute_company_id()
        for emission in self:
            if not emission.company_id and emission.withholding_id:
                emission.company_id = emission.withholding_id.company_id

    def _has_source(self):
        return super()._has_source() or bool(self.withholding_id)
