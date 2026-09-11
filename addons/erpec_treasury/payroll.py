"""Preparación de cuentas por pagar y pagos nativos de nómina por empleado."""
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


def require_manager(env):
    if not env.su and not env.user.has_group('erpec_payroll.group_payroll_manager'):
        raise AccessError('Se requiere el permiso de responsable de nómina.')


class Company(models.Model):
    _inherit = 'res.company'
    erpec_payroll_bank_journal_id = fields.Many2one('account.journal','Banco para pagos de nómina',
        domain="[('type','=','bank')]")
    erpec_payroll_payable_id = fields.Many2one('account.account','Nómina por pagar conciliable',
        domain="[('account_type','=','liability_payable'),('reconcile','=',True)]")


class PayrollPayment(models.Model):
    _name = 'erpec.payroll.disbursement'
    _description = 'Nómina por pagar por empleado'
    _rec_name = 'employee_id'
    line_id = fields.Many2one('erpec.payroll.line','Línea de nómina',required=True,ondelete='restrict')
    period_id = fields.Many2one('erpec.payroll.period',string='Período',related='line_id.period_id',store=True)
    employee_id = fields.Many2one('hr.employee',string='Empleado',related='line_id.employee_id',store=True)
    partner_id = fields.Many2one(related='line_id.partner_id',store=True)
    company_id = fields.Many2one(related='line_id.company_id',store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    move_id = fields.Many2one('account.move','Cuenta por pagar',readonly=True,ondelete='restrict')
    reversal_id = fields.Many2one('account.move','Reversión de preparación',readonly=True,ondelete='restrict')
    amount = fields.Monetary('Neto',compute='_compute_residual')
    residual = fields.Monetary('Saldo por pagar',compute='_compute_residual')
    status = fields.Selection([('open','Pendiente de pago'),('partial','Pago parcial'),
        ('settled','Cuenta por pagar liquidada'),('reversed','Preparación revertida')],
        string='Estado',compute='_compute_residual')
    _sql_constraints = [('line_unique','unique(line_id)','Ya existe la preparación de este empleado y período.')]

    @api.depends('move_id.line_ids.amount_residual','reversal_id','line_id.result')
    def _compute_residual(self):
        for record in self:
            record.amount = record.line_id.net
            record.residual = abs(sum(record.move_id.line_ids.filtered(
                lambda l:l.account_type=='liability_payable').mapped('amount_residual')))
            record.status = ('reversed' if record.reversal_id else 'settled' if record.currency_id.is_zero(record.residual)
                             else 'partial' if record.residual < record.amount else 'open')

    def action_pay(self):
        self.ensure_one(); require_manager(self.env); self.check_access('read')
        if self.reversal_id or self.currency_id.is_zero(self.residual):
            raise ValidationError('No queda saldo pagable en esta preparación.')
        bank = self.company_id.erpec_payroll_bank_journal_id
        if not bank or bank.company_id!=self.company_id or bank.type!='bank' or not bank.outbound_payment_method_line_ids.filtered(lambda m:m.payment_account_id.reconcile):
            raise ValidationError('Configura el banco de nómina con una cuenta conciliable de pagos pendientes en la empresa.')
        lines = self.move_id.line_ids.filtered(lambda l:l.account_type=='liability_payable' and not l.reconciled)
        return {'type':'ir.actions.act_window','name':'Registrar pago de nómina',
            'res_model':'account.payment.register','view_mode':'form','target':'new',
            'context':{'active_model':'account.move.line','active_ids':lines.ids,'default_journal_id':bank.id}}

    def action_reverse(self):
        self.ensure_one(); require_manager(self.env); self.check_access('write')
        self.env.cr.execute('SELECT id FROM erpec_payroll_disbursement WHERE id=%s FOR UPDATE',[self.id])
        self.invalidate_recordset()
        if self.reversal_id:
            return True
        if any(l.reconciled or l.matched_debit_ids or l.matched_credit_ids for l in self.move_id.line_ids):
            raise ValidationError('Desconcilia y revierte los pagos antes de revertir esta preparación.')
        reverse = self.move_id.with_context(_erpec_disbursement_token=_TOKEN)._reverse_moves([{'date':fields.Date.today(),
            'ref':'Reversión de preparación nómina '+self.period_id.name}],cancel=True)
        self.with_context(_erpec_disbursement_token=_TOKEN).write({'reversal_id':reverse.id})
        return True

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_disbursement_token') is not _TOKEN:
            raise AccessError('Prepara los pagos desde el período de nómina.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_erpec_disbursement_token') is not _TOKEN:
            raise AccessError('La preparación es inmutable; utiliza pago o reversión.')
        return super().write(values)

    def unlink(self):
        raise ValidationError('Conserva la trazabilidad de la preparación de nómina.')


_TOKEN = object()


class Period(models.Model):
    _inherit = 'erpec.payroll.period'
    disbursement_ids = fields.One2many('erpec.payroll.disbursement','period_id','Pagos por empleado')

    def action_prepare_payments(self):
        self.ensure_one(); require_manager(self.env); self._lock()
        if self.state != 'posted':
            raise ValidationError('Contabiliza el período antes de preparar sus pagos.')
        payable = self.company_id.erpec_payroll_payable_id
        if not payable or payable.account_type!='liability_payable' or not payable.reconcile or payable.deprecated or self.company_id not in payable.company_ids:
            raise ValidationError('Configura una cuenta conciliable de nómina por pagar para esta empresa.')
        for line in self.line_ids:
            existing = self.env['erpec.payroll.disbursement'].search([('line_id','=',line.id)],limit=1)
            if existing:
                continue
            mapping = self.policy_id.mapping_ids.filtered(lambda m:m.concept=='net')
            if len(mapping)!=1 or not mapping.credit_id or mapping.credit_id==payable:
                raise ValidationError('La preparación requiere la cuenta original de netos separada de nómina por pagar.')
            source = self.move_id.line_ids.filtered(lambda l:l.account_id==mapping.credit_id
                and l.partner_id==line.partner_id and l.name=='Neto por pagar · '+line.employee_id.name)
            if len(source)!=1 or not self.company_id.currency_id.is_zero(-source.balance-line.net) or line.net<=0:
                raise ValidationError('No se encontró una partida neta única y positiva para el empleado.')
            move = self.env['account.move'].create({'move_type':'entry','journal_id':self.policy_id.journal_id.id,
                'company_id':self.company_id.id,'date':fields.Date.today(),'ref':'Pago de nómina '+self.name+' · '+line.employee_id.name,
                'line_ids':[(0,0,{'name':'Traslado del neto','account_id':source.account_id.id,
                    'partner_id':line.partner_id.id,'debit':line.net}),
                    (0,0,{'name':'Nómina por pagar','account_id':payable.id,'partner_id':line.partner_id.id,
                          'credit':line.net,'date_maturity':fields.Date.today()})]})
            move.action_post()
            self.env['erpec.payroll.disbursement'].with_context(_erpec_disbursement_token=_TOKEN).create({
                'line_id':line.id,'move_id':move.id})
        return {'type':'ir.actions.act_window','name':'Pagos de nómina','res_model':'erpec.payroll.disbursement',
                'view_mode':'list,form','domain':[('period_id','=',self.id)]}

    def action_reverse(self):
        if any(not item.reversal_id for item in self.disbursement_ids):
            raise ValidationError('Revierte primero las preparaciones y pagos por empleado.')
        return super().action_reverse()

class PreparedMove(models.Model):
    _inherit = 'account.move'
    erpec_disbursement_ids = fields.One2many('erpec.payroll.disbursement','move_id')

    def _check_disbursement_edit(self):
        # Solo consulta la existencia del vínculo para protegerlo; no expone datos de nómina.
        if self.env.context.get('_erpec_disbursement_token') is not _TOKEN and self.sudo().erpec_disbursement_ids:
            raise ValidationError('Administra la cuenta por pagar desde la preparación de nómina.')

    def write(self, values):
        if set(values)&{'line_ids','journal_id','date','state','company_id','partner_id'}:
            self._check_disbursement_edit()
        return super().write(values)

    def button_draft(self):
        self._check_disbursement_edit()
        return super().button_draft()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        self._check_disbursement_edit()
        return super()._reverse_moves(default_values_list=default_values_list,cancel=cancel)

    def unlink(self):
        self._check_disbursement_edit()
        return super().unlink()


class PreparedMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, values_list):
        self.env['account.move'].browse([v['move_id'] for v in values_list if v.get('move_id')])._check_disbursement_edit()
        return super().create(values_list)

    def write(self, values):
        if set(values)&{'debit','credit','balance','amount_currency','currency_id','account_id','partner_id','move_id'}:
            self.move_id._check_disbursement_edit()
            if values.get('move_id'):
                self.env['account.move'].browse(values['move_id'])._check_disbursement_edit()
        return super().write(values)

    def unlink(self):
        self.move_id._check_disbursement_edit()
        return super().unlink()
