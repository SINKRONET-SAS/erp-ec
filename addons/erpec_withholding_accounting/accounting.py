"""Balance de comprobación calculado desde apuntes publicados de Community."""
from odoo import api, fields, models, Command
from odoo.exceptions import ValidationError


class TrialBalance(models.TransientModel):
    _name = 'erpec.trial.balance'
    _description = 'Contabilidad ERP EC y balance de comprobación'
    _check_company_auto = True

    company_id = fields.Many2one('res.company',required=True,default=lambda self:self.env.company,string='Empresa')
    currency_id = fields.Many2one(related='company_id.currency_id', string='Moneda')
    date_from = fields.Date('Desde',required=True,default=lambda self:fields.Date.context_today(self).replace(month=1,day=1))
    date_to = fields.Date('Hasta',required=True,default=fields.Date.context_today)
    line_ids = fields.One2many('erpec.trial.balance.line','report_id',readonly=True,string='Balance de comprobación')
    total_debit = fields.Monetary(compute='_totals',string='Total debe')
    total_credit = fields.Monetary(compute='_totals',string='Total haber')
    total_balance = fields.Monetary(compute='_totals',string='Diferencia de saldos')

    @api.depends('line_ids.debit','line_ids.credit','line_ids.closing')
    def _totals(self):
        for report in self:
            report.total_debit=report.currency_id.round(sum(report.line_ids.mapped('debit')))
            report.total_credit=report.currency_id.round(sum(report.line_ids.mapped('credit')))
            report.total_balance=report.currency_id.round(sum(report.line_ids.mapped('closing')))

    @api.onchange('company_id','date_from','date_to')
    def _clear_previous_result(self):
        self.line_ids=[Command.clear()]

    def action_generate(self):
        self.ensure_one()
        self.check_access('write')
        if self.company_id not in self.env.companies:
            raise ValidationError('Selecciona una empresa a la que tengas acceso.')
        if self.date_from > self.date_to:
            raise ValidationError('La fecha inicial no puede superar la final.')
        model=self.env['account.move.line']
        base=[('company_id','=',self.company_id.id),('parent_state','=','posted')]
        opening=model._read_group(base+[('date','<',self.date_from)],['account_id'],['balance:sum'])
        period=model._read_group(base+[('date','>=',self.date_from),('date','<=',self.date_to)],['account_id'],['debit:sum','credit:sum'])
        rows={account.id:{'account_id':account.id,'opening':amount,'debit':0,'credit':0} for account,amount in opening}
        for account,debit,credit in period:
            row=rows.setdefault(account.id,{'account_id':account.id,'opening':0})
            row.update(debit=debit,credit=credit)
        values=[Command.clear()]
        for row in rows.values():
            row['closing']=row['opening']+row['debit']-row['credit']
            values.append(Command.create(row))
        self.line_ids=values
        return {'type':'ir.actions.act_window','res_model':self._name,'res_id':self.id,'view_mode':'form'}


class TrialBalanceLine(models.TransientModel):
    _name = 'erpec.trial.balance.line'
    _description = 'Cuenta del balance de comprobación'
    _order = 'account_id'

    report_id = fields.Many2one('erpec.trial.balance',required=True,ondelete='cascade', string='Reporte')
    account_id = fields.Many2one('account.account',required=True,string='Cuenta')
    currency_id = fields.Many2one(related='report_id.currency_id', string='Moneda')
    opening = fields.Monetary('Saldo inicial')
    debit = fields.Monetary('Debe')
    credit = fields.Monetary('Haber')
    closing = fields.Monetary('Saldo final')

    def action_ledger(self):
        self.ensure_one()
        self.check_access('read')
        if self.report_id.company_id not in self.env.companies:
            raise ValidationError('La empresa del informe no está permitida.')
        action=self.env['ir.actions.actions']._for_xml_id('account.action_account_moves_all')
        action['domain']=[('company_id','=',self.report_id.company_id.id),('account_id','=',self.account_id.id),('date','<=',self.report_id.date_to),('parent_state','=','posted')]
        action['context']={'allowed_company_ids':[self.report_id.company_id.id]}
        return action
