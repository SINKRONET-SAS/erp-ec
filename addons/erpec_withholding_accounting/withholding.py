"""Asientos de retención y conciliación nativa, separados de la autorización fiscal."""
import uuid
from odoo import api, fields, models, Command
from odoo.exceptions import ValidationError, UserError

_INTERNAL = object()


class Withholding(models.Model):
    _name = 'erpec.withholding'
    _description = 'Retención contable Ecuador'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _rec_name = 'reference'

    reference = fields.Char('Referencia del comprobante', required=True, tracking=True)
    correlation_id = fields.Char(default=lambda self: uuid.uuid4().hex, readonly=True, copy=False)
    invoice_id = fields.Many2one('account.move', required=True, check_company=True, ondelete='restrict', string='Factura')
    company_id = fields.Many2one(related='invoice_id.company_id', store=True, index=True)
    partner_id = fields.Many2one(related='invoice_id.partner_id', store=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    direction = fields.Selection([('issued','Emitida a proveedor'),('received','Recibida de cliente')], compute='_compute_direction', store=True, string='Dirección')
    date = fields.Date('Fecha contable', required=True, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', required=True, check_company=True, string='Diario de retenciones')
    line_ids = fields.One2many('erpec.withholding.line','withholding_id',string='Conceptos',copy=True)
    amount = fields.Monetary(compute='_compute_amount',string='Total retenido')
    state = fields.Selection([('draft','Borrador'),('posted','Contabilizada'),('reversed','Revertida')],default='draft',readonly=True,copy=False,tracking=True,string='Estado contable')
    entry_id = fields.Many2one('account.move',readonly=True,copy=False,ondelete='restrict',string='Asiento')
    reversal_id = fields.Many2one('account.move',readonly=True,copy=False,ondelete='restrict',string='Asiento de reversión')
    reversal_date = fields.Date('Fecha de reversión')
    reversal_reason = fields.Text('Motivo de reversión')
    fiscal_notice = fields.Char(default='La contabilización no acredita autorización fiscal. El conector debe verificar el comprobante y su estado en el SRI.',readonly=True)
    _sql_constraints = [('reference_unique','unique(company_id,partner_id,direction,reference)','Ya existe esta referencia de retención para el tercero y dirección indicados.')]

    @api.depends('invoice_id.move_type')
    def _compute_direction(self):
        for record in self:
            record.direction = 'issued' if record.invoice_id.move_type == 'in_invoice' else 'received'

    @api.depends('line_ids.amount')
    def _compute_amount(self):
        for record in self:
            record.amount = sum(record.line_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if any(key in values for key in ('state','entry_id','reversal_id','company_id','partner_id','correlation_id','fiscal_notice')):
                raise ValidationError('Los estados, asientos e identificadores son administrados por el flujo contable.')
        records = super().create(values_list)
        records._validate_invoice()
        return records

    def write(self, values):
        if any(key in values for key in ('state','entry_id','reversal_id','company_id','partner_id','correlation_id','fiscal_notice')):
            raise ValidationError('Utiliza las acciones de contabilización o reversión.')
        if any(record.state != 'draft' for record in self) and set(values) - {'reversal_date','reversal_reason'}:
            raise ValidationError('La retención contabilizada es inmutable; utiliza su reversión.')
        result = super().write(values)
        self._validate_invoice()
        return result

    def unlink(self):
        if any(record.state != 'draft' for record in self):
            raise ValidationError('No se eliminan retenciones contabilizadas o revertidas.')
        return super().unlink()

    def _validate_invoice(self):
        for record in self:
            record.invoice_id.check_access('write')
            if record.invoice_id.move_type not in ('in_invoice','out_invoice') or record.company_id.country_id.code != 'EC':
                raise ValidationError('Selecciona una factura de venta o compra de una empresa de Ecuador.')
            if record.currency_id.name != 'USD' or record.company_id.currency_id != record.currency_id:
                raise ValidationError('Este flujo requiere factura y contabilidad en USD.')
            if record.journal_id.type != 'general':
                raise ValidationError('Utiliza un diario de operaciones diversas para las retenciones.')

    def _lock(self):
        self.ensure_one()
        self.check_access('write')
        self.flush_recordset()
        self.env.cr.execute('SELECT id FROM erpec_withholding WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        self.env.cr.execute('SELECT id FROM account_move WHERE id = %s FOR UPDATE', [self.invoice_id.id])
        self.invoice_id.invalidate_recordset()
        self.invoice_id.line_ids.invalidate_recordset()

    def action_post(self):
        self.ensure_one()
        self._lock()
        if self.state == 'posted':
            return self.action_open_entry()
        if self.state != 'draft':
            raise ValidationError('Una retención revertida no se vuelve a contabilizar.')
        self._validate_invoice()
        self.line_ids._validate_values()
        if self.invoice_id.state != 'posted' or not self.line_ids or self.amount <= 0:
            raise ValidationError('La factura debe estar contabilizada y la retención debe tener conceptos positivos.')
        if self.currency_id.compare_amounts(self.amount,self.invoice_id.amount_residual) > 0:
            raise ValidationError('La retención supera el saldo pendiente de la factura.')
        kind = 'liability_payable' if self.direction == 'issued' else 'asset_receivable'
        trade = self.invoice_id.line_ids.filtered(lambda line: line.account_id.account_type == kind and not line.reconciled)
        if not trade or len(trade.account_id) != 1:
            raise ValidationError('La factura requiere una única cuenta conciliable de cliente o proveedor.')
        sign = 1 if self.direction == 'issued' else -1
        lines = [Command.create({'name':self.reference,'account_id':trade.account_id.id,'partner_id':self.partner_id.id,'debit':self.amount if sign > 0 else 0,'credit':self.amount if sign < 0 else 0})]
        for line in self.line_ids:
            lines.append(Command.create({'name':line.name,'account_id':line.account_id.id,'partner_id':self.partner_id.id,'debit':line.amount if sign < 0 else 0,'credit':line.amount if sign > 0 else 0}))
        entry = self.env['account.move'].with_context(_erpec_token=_INTERNAL).create({'move_type':'entry','journal_id':self.journal_id.id,'date':self.date,'ref':self.reference,'ec_retention_id':self.id,'line_ids':lines})
        entry.action_post()
        (trade + entry.line_ids.filtered(lambda line: line.account_id == trade.account_id)).with_context(_erpec_token=_INTERNAL).reconcile()
        super(Withholding,self).write({'state':'posted','entry_id':entry.id})
        self.message_post(body='Retención contabilizada y conciliada. Correlación: '+self.correlation_id)
        return self.action_open_entry()

    def action_reverse(self):
        self.ensure_one()
        self._lock()
        if self.state == 'reversed':
            return {'type':'ir.actions.act_window','res_model':'account.move','res_id':self.reversal_id.id,'view_mode':'form'}
        if self.state != 'posted' or not self.reversal_date or not (self.reversal_reason or '').strip():
            raise ValidationError('Indica fecha y motivo para revertir una retención contabilizada.')
        if self.reversal_date < self.date:
            raise ValidationError('La reversión no puede tener fecha anterior a la retención.')
        reversal = self.entry_id.with_context(_erpec_token=_INTERNAL)._reverse_moves([{'date':self.reversal_date,'ref':'Reversión: '+self.reference}],cancel=True)
        reversal.write({'ec_retention_id':self.id})
        super(Withholding,self).write({'state':'reversed','reversal_id':reversal.id})
        self.message_post(body='Reversión contable: '+self.reversal_reason+'. Correlación: '+self.correlation_id)
        return {'type':'ir.actions.act_window','res_model':'account.move','res_id':reversal.id,'view_mode':'form'}

    def action_open_entry(self):
        self.ensure_one()
        self.check_access('read')
        if not self.entry_id:
            raise UserError('Todavía no existe asiento de esta retención.')
        return {'type':'ir.actions.act_window','res_model':'account.move','res_id':self.entry_id.id,'view_mode':'form'}


class WithholdingLine(models.Model):
    _name = 'erpec.withholding.line'
    _description = 'Concepto contable de retención'
    _check_company_auto = True

    withholding_id = fields.Many2one('erpec.withholding',required=True,ondelete='cascade',check_company=True)
    company_id = fields.Many2one(related='withholding_id.company_id',store=True)
    currency_id = fields.Many2one(related='withholding_id.currency_id')
    name = fields.Char('Concepto y código SRI',required=True)
    kind = fields.Selection([('income','Renta'),('vat','IVA')],required=True,string='Impuesto')
    base = fields.Monetary('Base',required=True)
    rate = fields.Float('Porcentaje verificado',required=True,digits=(16,6))
    amount = fields.Monetary('Retención',compute='_compute_amount',store=True)
    account_id = fields.Many2one('account.account',required=True,check_company=True,ondelete='restrict',string='Cuenta tributaria')

    @api.depends('base','rate','currency_id')
    def _compute_amount(self):
        for line in self:
            line.amount = line.currency_id.round(line.base*line.rate/100) if line.currency_id else 0

    @api.constrains('base','rate','account_id','withholding_id')
    def _validate_values(self):
        for line in self:
            if line.base <= 0 or not 0 < line.rate <= 100 or line.amount <= 0:
                raise ValidationError('La base y el importe deben ser positivos y la tarifa no puede superar 100%.')
            expected = 'liability_current' if line.withholding_id.direction == 'issued' else 'asset_current'
            if line.account_id.account_type != expected or line.account_id.deprecated:
                raise ValidationError('Utiliza una cuenta tributaria de pasivo corriente para emitidas o activo corriente para recibidas.')

    def _check_draft(self):
        for parent in self.withholding_id.sorted('id'):
            parent._lock()
        for line in self:
            line.withholding_id.check_access('write')
            if line.withholding_id.state != 'draft':
                raise ValidationError('Los conceptos de una retención contabilizada no se modifican.')

    @api.model_create_multi
    def create(self, values_list):
        if any('company_id' in values or 'currency_id' in values for values in values_list):
            raise ValidationError('Empresa y moneda se obtienen del documento.')
        records = super().create(values_list)
        records._check_draft()
        return records

    def write(self, values):
        self._check_draft()
        if any(key in values for key in ('company_id','currency_id')):
            raise ValidationError('Empresa y moneda se obtienen del documento.')
        result = super().write(values)
        self._check_draft()
        return result

    def unlink(self):
        self._check_draft()
        return super().unlink()


class AccountMove(models.Model):
    _inherit = 'account.move'

    ec_retention_id = fields.Many2one('erpec.withholding',readonly=True,copy=False,ondelete='restrict')
    ec_accounting_withholding_ids = fields.One2many('erpec.withholding','invoice_id',string='Retenciones contables',copy=False)

    def _check_retention_entry(self):
        if self.env.context.get('_erpec_token') is not _INTERNAL and any(self.mapped('ec_retention_id')):
            raise ValidationError('Administra este asiento desde el documento de retención y su reversión.')

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_token') is not _INTERNAL and any(values.get('ec_retention_id') for values in values_list):
            raise ValidationError('El vínculo del asiento se genera desde la retención.')
        return super().create(values_list)

    def write(self, values):
        if 'ec_retention_id' in values and self.env.context.get('_erpec_token') is not _INTERNAL:
            raise ValidationError('El vínculo del asiento es inmutable.')
        if set(values) & {'line_ids','journal_id','date','state','company_id','partner_id'}:
            self._check_retention_entry()
        return super().write(values)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        self._check_retention_entry()
        return super()._reverse_moves(default_values_list=default_values_list,cancel=cancel)

    def button_draft(self):
        self._check_retention_entry()
        if any(record.ec_accounting_withholding_ids.filtered(lambda retention: retention.state == 'posted') for record in self):
            raise ValidationError('Revierte las retenciones antes de devolver la factura a borrador.')
        return super().button_draft()

    def button_cancel(self):
        self._check_retention_entry()
        return super().button_cancel()

    def unlink(self):
        self._check_retention_entry()
        return super().unlink()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, values_list):
        moves = self.env['account.move'].browse([values['move_id'] for values in values_list if values.get('move_id')])
        moves._check_retention_entry()
        return super().create(values_list)

    def write(self, values):
        if set(values) & {'debit','credit','balance','amount_currency','account_id','partner_id','move_id','currency_id'}:
            self.move_id._check_retention_entry()
        return super().write(values)

    def unlink(self):
        self.move_id._check_retention_entry()
        return super().unlink()

    def remove_move_reconcile(self):
        self.move_id._check_retention_entry()
        linked = self.matched_debit_ids.debit_move_id.move_id | self.matched_credit_ids.credit_move_id.move_id
        linked._check_retention_entry()
        return super().remove_move_reconcile()


class PartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, values_list):
        ids=[values[key] for values in values_list for key in ('debit_move_id','credit_move_id') if values.get(key)]
        self.env['account.move.line'].browse(ids).move_id._check_retention_entry()
        return super().create(values_list)

    def unlink(self):
        (self.debit_move_id.move_id | self.credit_move_id.move_id)._check_retention_entry()
        return super().unlink()
