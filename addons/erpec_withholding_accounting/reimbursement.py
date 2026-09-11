"""Conciliación de sustentos con las líneas y tributos calculados por Odoo."""
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Support(models.Model):
    _inherit = 'erpec.reimbursement.support'

    invoice_line_id = fields.Many2one('account.move.line',string='Línea contable de reembolso',check_company=True,ondelete='restrict')

    @api.constrains('invoice_line_id','move_id')
    def _check_linked_line(self):
        for support in self:
            if support.invoice_line_id and (support.invoice_line_id.move_id != support.move_id or support.invoice_line_id.display_type != 'product'):
                raise ValidationError('El sustento debe vincularse a una línea de producto de la misma factura.')


class MoveLine(models.Model):
    _inherit = 'account.move.line'

    ec_reimbursement = fields.Boolean('Reembolso de gastos')


class Move(models.Model):
    _inherit = 'account.move'

    def _validate_reimbursements(self):
        for move in self:
            lines=move.invoice_line_ids.filtered('ec_reimbursement')
            supports=move.ec_reimbursement_ids
            if not lines and not supports:
                continue
            if move.move_type != 'in_invoice':
                raise ValidationError('La conciliación de sustentos se aplica a facturas de compra.')
            if any(not support.invoice_line_id or support.invoice_line_id not in lines for support in supports):
                raise ValidationError('Vincula cada sustento a una línea marcada como reembolso de esta factura.')
            for line in lines:
                linked=supports.filtered(lambda support:support.invoice_line_id==line)
                if not linked:
                    raise ValidationError('Cada línea de reembolso requiere comprobantes de sustento.')
                subtotal=sum(linked.mapped('untaxed_amount'))
                taxes=sum(linked.mapped('tax_amount'))
                if move.currency_id.compare_amounts(subtotal,line.price_subtotal) or move.currency_id.compare_amounts(taxes,line.price_total-line.price_subtotal):
                    raise ValidationError('Los subtotales e impuestos de los sustentos deben coincidir con la línea de reembolso. Odoo calcula el impuesto contable; no se crea un segundo asiento.')

    def _post(self,soft=True):
        self._validate_reimbursements()
        return super()._post(soft=soft)
