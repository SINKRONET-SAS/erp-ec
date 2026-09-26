"""Preparación documental local; no emite ni autoriza comprobantes fiscales."""
import re
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Move(models.Model):
    _inherit = 'account.move'

    ec_sale_order_ids = fields.Many2many('sale.order', compute='_compute_ec_sources', string='Ventas vinculadas')
    ec_purchase_order_ids = fields.Many2many('purchase.order', compute='_compute_ec_sources', string='Compras vinculadas')
    ec_withholding_ids = fields.One2many('erpec.purchase.withholding','move_id',string='Preparación de retenciones',copy=False)
    ec_reimbursement_ids = fields.One2many('erpec.reimbursement.support','move_id',string='Comprobantes de reembolso',copy=False)
    ec_fiscal_notice = fields.Text(compute='_compute_ec_sources',string='Alcance fiscal')

    @api.depends('invoice_line_ids.sale_line_ids.order_id','invoice_line_ids.purchase_line_id.order_id')
    def _compute_ec_sources(self):
        for move in self:
            move.ec_sale_order_ids = move.invoice_line_ids.sale_line_ids.order_id
            move.ec_purchase_order_ids = move.invoice_line_ids.purchase_line_id.order_id
            move.ec_fiscal_notice = 'Preparación documental local. No se ha integrado el envío ni la verificación fiscal. Las retenciones de esta pestaña son borradores: no generan asiento, pago, XML ni autorización. Los reembolsos de gastos no son devoluciones ni notas de crédito.'

    def write(self, values):
        for move in self:
            for field in ('company_id','currency_id','partner_id','move_type'):
                if field in values:
                    current = move[field].id if field.endswith('_id') else move[field]
                    if current != values[field] and (move.ec_withholding_ids or move.ec_reimbursement_ids):
                        raise ValidationError('Retira o revisa los documentos Ecuador antes de cambiar la empresa, proveedor, moneda o tipo de factura.')
        return super().write(values)


class PurchaseDocument(models.AbstractModel):
    _name = 'erpec.purchase.document.mixin'
    _description = 'Validación de documentos de compra'
    _check_company_auto = True

    move_id = fields.Many2one('account.move', string='Factura de proveedor',required=True,ondelete='restrict',check_company=True,index=True)
    company_id = fields.Many2one(related='move_id.company_id',store=True,index=True, string='Empresa')
    currency_id = fields.Many2one(related='move_id.currency_id', string='Moneda')

    def _check_parent(self):
        for document in self:
            document.move_id.check_access('write')
            if document.move_id.move_type != 'in_invoice' or document.move_id.company_id.country_id.code != 'EC':
                raise ValidationError('Este documento requiere una factura de proveedor de una empresa de Ecuador.')
            if document.move_id.state == 'cancel':
                raise ValidationError('No se pueden preparar documentos sobre una factura cancelada.')
            if document.currency_id.name != 'USD':
                raise ValidationError('Este incremento admite comprobantes de compra en USD. La conversión de moneda requiere un flujo específico.')

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'company_id' in values or 'currency_id' in values:
                raise ValidationError('La empresa y moneda se obtienen de la factura vinculada.')
        records = super().create(values_list)
        records._check_parent()
        return records

    def write(self, values):
        self._check_parent()
        if 'company_id' in values or 'currency_id' in values:
            raise ValidationError('La empresa y moneda se obtienen de la factura vinculada.')
        result = super().write(values)
        self._check_parent()
        return result

    def unlink(self):
        self._check_parent()
        return super().unlink()


class Withholding(models.Model):
    _name = 'erpec.purchase.withholding'
    _inherit = 'erpec.purchase.document.mixin'
    _description = 'Preparación de retención de compra'
    _rec_name = 'tax_id'
    _check_company_auto = True

    tax_id = fields.Many2one('account.tax',string='Concepto de retención del catálogo',required=True,check_company=True,ondelete='restrict')
    tax_kind = fields.Selection([('income','Renta'),('vat','IVA')],compute='_compute_estimate',string='Tipo')
    base_amount = fields.Monetary('Base indicada por el responsable',required=True,currency_field='currency_id')
    rate = fields.Float('Porcentaje del catálogo',compute='_compute_estimate')
    estimated_amount = fields.Monetary('Importe preliminar',compute='_compute_estimate',currency_field='currency_id')
    notes = fields.Text('Justificación y revisión de vigencia')
    _sql_constraints = [('concept_once','unique(move_id,tax_id)','Agrupa la base del mismo concepto en una sola línea de preparación.')]

    @api.depends('base_amount','currency_id','tax_id.amount','tax_id.tax_group_id.l10n_ec_type')
    def _compute_estimate(self):
        for line in self:
            line.tax_kind = 'vat' if line.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat_purchase' else 'income'
            line.rate = abs(line.tax_id.amount)
            line.estimated_amount = line.currency_id.round(line.base_amount * line.rate / 100) if line.currency_id else 0

    @api.constrains('tax_id','base_amount','move_id')
    def _check_concept(self):
        for line in self:
            tax = line.tax_id
            if tax.tax_group_id.l10n_ec_type not in ('withhold_income_purchase','withhold_vat_purchase') or tax.amount_type != 'percent' or not -100 <= tax.amount < 0 or tax.price_include:
                raise ValidationError('Selecciona una retención de compra porcentual negativa, no incluida en precio. Otros métodos requieren validación específica.')
            if line.base_amount <= 0:
                raise ValidationError('La base de la retención debe ser mayor que cero.')


class Reimbursement(models.Model):
    _name = 'erpec.reimbursement.support'
    _inherit = 'erpec.purchase.document.mixin'
    _description = 'Comprobante de sustento de reembolso'
    _rec_name = 'document_number'
    _check_company_auto = True

    supplier_id = fields.Many2one('res.partner',string='Emisor del comprobante de sustento',required=True,check_company=True,ondelete='restrict')
    document_type_id = fields.Many2one('l10n_latam.document.type',string='Tipo de comprobante de sustento',required=True,ondelete='restrict')
    document_number = fields.Char('Número del comprobante',required=True)
    document_key = fields.Char(compute='_compute_document_key',store=True, string='Clave del documento')
    issue_date = fields.Date('Fecha de emisión',required=True)
    untaxed_amount = fields.Monetary('Subtotal de sustento',required=True,currency_field='currency_id')
    tax_amount = fields.Monetary('Impuestos del sustento',currency_field='currency_id')
    total_amount = fields.Monetary('Total de sustento',compute='_compute_total',currency_field='currency_id')
    notes = fields.Text('Referencia del respaldo y observaciones')
    _sql_constraints = [('support_once','unique(company_id,supplier_id,document_type_id,document_key)','Este comprobante ya está registrado como sustento de reembolso en la empresa.')]

    @api.depends('document_number')
    def _compute_document_key(self):
        for line in self:
            line.document_key = re.sub('[^A-Z0-9]','',(line.document_number or '').upper())

    @api.depends('untaxed_amount','tax_amount','currency_id')
    def _compute_total(self):
        for line in self:
            line.total_amount = line.currency_id.round(line.untaxed_amount+line.tax_amount) if line.currency_id else 0

    @api.constrains('untaxed_amount','tax_amount','document_number')
    def _check_amounts(self):
        for line in self:
            if not line.document_key or line.untaxed_amount < 0 or line.tax_amount < 0 or line.untaxed_amount+line.tax_amount <= 0:
                raise ValidationError('El sustento requiere un número válido e importes no negativos con total mayor que cero.')

    def write(self, values):
        if any(line.move_id.state != 'draft' for line in self):
            raise ValidationError('El sustento de una factura contabilizada no se modifica desde este registro.')
        result = super().write(values)
        if any(line.move_id.state != 'draft' for line in self):
            raise ValidationError('No se puede trasladar un sustento a una factura contabilizada.')
        return result

    def unlink(self):
        if any(line.move_id.state != 'draft' for line in self):
            raise ValidationError('El sustento de una factura contabilizada no se elimina desde este registro.')
        return super().unlink()

    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list)
        if any(line.move_id.state != 'draft' for line in records):
            raise ValidationError('Registra los sustentos del reembolso antes de contabilizar la factura.')
        return records
