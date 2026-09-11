"""Conciliación exacta de pagos con extractos nativos en moneda de la empresa."""
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class BankMatch(models.TransientModel):
    _name = 'erpec.bank.match'
    _description = 'Conciliar un movimiento bancario con un pago'
    statement_line_id = fields.Many2one('account.bank.statement.line','Movimiento del extracto',required=True)
    payment_id = fields.Many2one('account.payment','Pago registrado',required=True)

    def action_match(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError('Se requiere el permiso de responsable de contabilidad.')
        statement, payment = self.statement_line_id, self.payment_id
        statement.check_access('write'); payment.check_access('write')
        self.env.flush_all()
        self.env.cr.execute('SELECT id FROM account_move WHERE id IN %s ORDER BY id FOR UPDATE',
                            [tuple((statement.move_id | payment.move_id).ids)])
        (statement.move_id | payment.move_id).invalidate_recordset()
        statement.invalidate_recordset(); payment.invalidate_recordset()
        (statement.move_id | payment.move_id).line_ids.invalidate_recordset()
        if statement.company_id != payment.company_id or statement.journal_id != payment.journal_id:
            raise ValidationError('El movimiento y el pago deben pertenecer a la misma empresa y banco.')
        currency = statement.company_id.currency_id
        if statement.foreign_currency_id or statement.currency_id != currency or payment.currency_id != currency:
            raise ValidationError('Este cotejo exacto requiere la moneda de la empresa. Revisa diferencias de cambio por separado.')
        if statement.move_id.state != 'posted' or payment.move_id.state != 'posted':
            raise ValidationError('Registra el movimiento y el asiento del pago antes de conciliar.')
        if statement.partner_id and statement.partner_id.commercial_partner_id != payment.partner_id.commercial_partner_id:
            raise ValidationError('El tercero del extracto no corresponde al pago.')
        liquidity, suspense, other = statement._seek_for_lines()
        pay_liquidity, _counterpart, _writeoff = payment._seek_for_lines()
        if len(pay_liquidity) != 1 or not pay_liquidity.account_id.reconcile:
            raise ValidationError('Configura una cuenta conciliable de pagos o cobros pendientes.')
        matched = pay_liquidity.matched_debit_ids | pay_liquidity.matched_credit_ids
        linked_lines = matched.debit_move_id | matched.credit_move_id
        if not suspense and pay_liquidity.reconciled and statement.move_id in linked_lines.move_id:
            return {'type':'ir.actions.act_window_close'}
        if len(suspense) != 1 or len(liquidity) != 1 or other or statement.is_reconciled or matched:
            raise ValidationError('El movimiento o el pago ya está conciliado, parcialmente aplicado o requiere revisión manual.')
        if not currency.is_zero(statement.amount - pay_liquidity.balance):
            raise ValidationError('El importe y el sentido del extracto deben coincidir exactamente con el pago.')
        suspense.with_context(skip_account_move_synchronization=True).write({
            'account_id':pay_liquidity.account_id.id,'partner_id':payment.partner_id.id})
        (suspense | pay_liquidity).reconcile()
        statement.move_id.checked = True
        if not statement.is_reconciled or not pay_liquidity.reconciled:
            raise ValidationError('La conciliación no quedó completa; se revierte la operación.')
        return {'type':'ir.actions.act_window_close'}


class StatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_erpec_match(self):
        self.ensure_one(); self.check_access('write')
        return {'type':'ir.actions.act_window','name':'Conciliar pago registrado',
                'res_model':'erpec.bank.match','view_mode':'form','target':'new',
                'context':{'default_statement_line_id':self.id}}
