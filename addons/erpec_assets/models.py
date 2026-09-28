"""Activos y depreciación contable lineal; no determina deducibilidad tributaria."""
import calendar
import logging
import math
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, Command
from odoo.exceptions import AccessError, ValidationError

_INTERNAL = object()
_logger = logging.getLogger(__name__)


def internal(record):
    return record.with_context(_erpec_asset_token=_INTERNAL)


def privileged(env):
    if not env.user.has_group('account.group_account_manager'):
        raise AccessError('Solo el responsable contable puede operar activos fijos.')


class Category(models.Model):
    _name = 'erpec.asset.category'
    _description = 'Categoría de activos fijos'
    _check_company_auto = True
    name = fields.Char('Nombre', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string='Empresa')
    journal_id = fields.Many2one('account.journal', required=True, check_company=True, domain="[('type','=','general')]", string='Diario')
    asset_account_id = fields.Many2one('account.account', required=True, check_company=True, string='Cuenta del activo')
    accumulated_account_id = fields.Many2one('account.account', required=True, check_company=True, string='Depreciación acumulada')
    expense_account_id = fields.Many2one('account.account', required=True, check_company=True, string='Gasto de depreciación')
    clearing_account_id = fields.Many2one('account.account', required=True, check_company=True, string='Contrapartida de altas manuales')
    loss_account_id = fields.Many2one('account.account', required=True, check_company=True, string='Pérdida en baja')
    gain_account_id = fields.Many2one('account.account', required=True, check_company=True, string='Ganancia en venta')
    months = fields.Integer('Vida útil en meses', default=60, required=True)

    @api.constrains('months', 'journal_id', 'asset_account_id', 'accumulated_account_id', 'expense_account_id', 'clearing_account_id', 'loss_account_id', 'gain_account_id')
    def _validate_category(self):
        for record in self:
            if not 1 <= record.months <= 1200 or record.journal_id.type != 'general':
                raise ValidationError('Usa diario general y vida útil entre 1 y 1200 meses.')
            accounts = [record.asset_account_id, record.accumulated_account_id, record.expense_account_id, record.clearing_account_id, record.loss_account_id, record.gain_account_id]
            if len(set(a.id for a in accounts[:4])) != 4 or any(a.deprecated or a.account_type in ('asset_receivable','liability_payable') for a in accounts):
                raise ValidationError('Configura cuentas vigentes, distintas para activo, acumulación, gasto y contrapartida, sin cuentas por cobrar/pagar.')

    def write(self, values):
        if set(values) - {'name'} and self.env['erpec.asset'].search_count([('category_id','in',self.ids)]):
            raise ValidationError('La categoría ya tiene activos; crea otra para cambiar su configuración.')
        return super().write(values)


class Asset(models.Model):
    _name = 'erpec.asset'
    _description = 'Activo fijo'
    _check_company_auto = True
    _order = 'acquisition_date desc, id desc'
    name = fields.Char('Activo', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string='Empresa')
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    category_id = fields.Many2one('erpec.asset.category', required=True, check_company=True, string='Categoría')
    source_line_id = fields.Many2one('account.move.line', check_company=True, ondelete='restrict', string='Línea de compra', copy=False)
    acquisition_date = fields.Date('Adquisición', required=True, default=fields.Date.today)
    service_date = fields.Date('Puesta en uso', required=True, default=fields.Date.today)
    cost = fields.Monetary('Costo capitalizado', required=True)
    residual = fields.Monetary('Valor residual')
    months = fields.Integer('Vida útil en meses', default=60, required=True)
    state = fields.Selection([('draft','Borrador'),('running','En uso'),('disposed','Baja / venta'),('reversed','Revertido')], default='draft', required=True, readonly=True, copy=False, string='Estado')
    line_ids = fields.One2many('erpec.asset.line','asset_id', string='Calendario', copy=False)
    move_ids = fields.One2many('account.move','erpec_asset_id', string='Asientos', copy=False)
    revision_ids = fields.One2many('erpec.asset.revision','asset_id', string='Cambios de estimación', copy=False)
    sale_line_id = fields.Many2one('account.move.line', check_company=True, ondelete='restrict', string='Línea de venta', readonly=True, copy=False)
    disposal_date = fields.Date('Fecha de baja', readonly=True, copy=False)
    accumulated = fields.Monetary('Depreciación contabilizada', compute='_compute_balances', store=True)
    book_value = fields.Monetary('Valor en libros', compute='_compute_balances', store=True)
    ledger_cost = fields.Monetary('Costo vigente en mayor', compute='_compute_balances', store=True)
    ledger_accumulated = fields.Monetary('Depreciación vigente en mayor', compute='_compute_balances', store=True)
    notes = fields.Text('Notas')

    @api.depends('cost','state','line_ids.amount','line_ids.move_id.state','line_ids.reversal_id.state')
    def _compute_balances(self):
        for record in self:
            record.accumulated = sum(record.line_ids.filtered(lambda x: x.move_id.state == 'posted' and x.reversal_id.state != 'posted').mapped('amount'))
            active = record.state == 'running'
            record.ledger_cost = record.cost if active else 0
            record.ledger_accumulated = record.accumulated if active else 0
            record.book_value = record.cost-record.accumulated if active else 0

    @api.onchange('category_id')
    def _onchange_category(self):
        if self.category_id:
            self.months = self.category_id.months

    @api.model_create_multi
    def create(self, values_list):
        privileged(self.env)
        forbidden = {'state','move_ids','line_ids','revision_ids','sale_line_id','disposal_date'}
        if any(set(v) & forbidden for v in values_list):
            raise AccessError('Usa las acciones del activo para generar su historial.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL:
            privileged(self.env)
            if set(values) & {'state','move_ids','line_ids','revision_ids','sale_line_id','disposal_date'}:
                raise AccessError('El historial se modifica mediante acciones contables.')
            if any(x.state != 'draft' for x in self) and set(values)-{'name','notes'}:
                raise ValidationError('Usa el cambio de estimación o la reversión; no modifiques el costo contabilizado.')
        return super().write(values)

    def unlink(self):
        if any(x.state != 'draft' for x in self):
            raise ValidationError('Conserva el historial: revierte el activo en vez de eliminarlo.')
        return super().unlink()

    @api.constrains('cost','residual','months','service_date','acquisition_date','source_line_id','company_id','category_id')
    def _validate_asset(self):
        for record in self:
            if not all(math.isfinite(v) for v in [record.cost,record.residual]) or record.cost <= 0 or not 0 <= record.residual <= record.cost:
                raise ValidationError('El costo debe ser positivo y el residual debe estar entre cero y el costo.')
            if not 1 <= record.months <= 1200 or record.service_date < record.acquisition_date:
                raise ValidationError('Revisa vida útil y fechas de adquisición/puesta en uso.')
            record._validate_source()

    def _validate_source(self):
        self.ensure_one()
        line = self.source_line_id
        if line:
            line.check_access('read')
            self.env.cr.execute('UPDATE account_move_line SET write_date=write_date WHERE id=%s RETURNING id',[line.id])
            line.invalidate_recordset()
            if line.move_id.state != 'posted' or line.move_id.move_type != 'in_invoice' or line.display_type != 'product' or line.balance <= 0 or line.company_id != self.company_id:
                raise ValidationError('Selecciona una línea positiva de compra contabilizada de esta empresa.')
            if self.acquisition_date < line.move_id.date:
                raise ValidationError('La adquisición no puede preceder a la compra contabilizada.')
            allocated = sum(self.search([('source_line_id','=',line.id),('state','!=','reversed')]).mapped('cost'))
            if self.currency_id.compare_amounts(allocated,line.balance) > 0:
                raise ValidationError('La capitalización acumulada supera el importe de la línea de compra en moneda de la empresa.')

    def _authorize(self):
        self.ensure_one()
        privileged(self.env)
        self.check_access('write')
        if self.company_id not in self.env.companies:
            raise AccessError('La empresa del activo no está autorizada.')
        self.env.cr.execute('SELECT id FROM erpec_asset WHERE id=%s FOR UPDATE',[self.id])
        self.invalidate_recordset()

    def _check_date(self, date):
        date = fields.Date.to_date(date)
        if self.company_id._get_violated_lock_dates(date, False, self.category_id.journal_id):
            raise ValidationError('La fecha pertenece a un periodo contable cerrado.')
        return date

    def _entry(self, date, kind, balances):
        date = self._check_date(date)
        lines = []
        for account, balance in balances:
            amount = self.currency_id.round(balance)
            if not self.currency_id.is_zero(amount):
                lines.append(Command.create({'name':self.name,'account_id':account.id,'debit':max(amount,0),'credit':max(-amount,0)}))
        if not lines:
            raise ValidationError('El asiento no tiene importe que contabilizar.')
        move = internal(self.env['account.move']).with_company(self.company_id).create({
            'move_type':'entry','date':date,'journal_id':self.category_id.journal_id.id,
            'company_id':self.company_id.id,'ref':self.name,'erpec_asset_id':self.id,'erpec_asset_kind':kind,'line_ids':lines})
        move.action_post()
        return move

    def _schedule(self, start, months, amount):
        start = fields.Date.to_date(start)
        per_month = amount / months
        remaining = self.currency_id.round(amount)
        partial = start.day != 1
        count = months + int(partial)
        values = []
        for index in range(count):
            current = start.replace(day=1) + relativedelta(months=index)
            days = calendar.monthrange(current.year,current.month)[1]
            value = remaining if index == count-1 else self.currency_id.round(per_month * ((days-start.day+1)/days if index == 0 and partial else 1))
            value = min(value,remaining)
            if not self.currency_id.is_zero(value):
                values.append({'asset_id':self.id,'date':current.replace(day=days),'amount':value})
            remaining = self.currency_id.round(remaining-value)
        internal(self.env['erpec.asset.line']).create(values)

    def action_confirm(self):
        for record in self:
            record._authorize()
            if record.state != 'draft':
                _logger.info('Alta repetida sin nuevo asiento correlationId=asset-%s userId=%s',record.id,self.env.uid)
                continue
            record._validate_source()
            category = record.category_id
            counterpart = record.source_line_id.account_id or category.clearing_account_id
            if counterpart != category.asset_account_id:
                record._entry(record.acquisition_date,'acquisition',[(category.asset_account_id,record.cost),(counterpart,-record.cost)])
            record._schedule(record.service_date,record.months,record.cost-record.residual)
            internal(record).write({'state':'running'})
        return True

    def action_depreciate(self):
        for record in self:
            record._authorize()
            if record.state != 'running':
                raise ValidationError('Solo se deprecian activos en uso.')
            for line in record.line_ids.filtered(lambda x: x.date <= fields.Date.today() and not x.move_id).sorted('date'):
                line._post()
        return True

    def _open_wizard(self, model, defaults=None):
        self.ensure_one()
        return {'type':'ir.actions.act_window','res_model':model,'view_mode':'form','target':'new',
                'context':dict(default_asset_id=self.id,**(defaults or {}))}

    def action_open_adjustment(self):
        return self._open_wizard('erpec.asset.adjustment',{'default_months':self.months,'default_residual':self.residual})

    def action_open_disposal(self):
        return self._open_wizard('erpec.asset.disposal')

    def action_open_reversal(self):
        return self._open_wizard('erpec.asset.reversal')

    def _dispose(self, date, sale_line=None):
        self._authorize()
        date = self._check_date(date)
        if self.state != 'running' or date < self.service_date:
            raise ValidationError('La baja requiere un activo en uso y fecha posterior a la puesta en uso.')
        if any(l.move_id and l.date > date for l in self.line_ids):
            raise ValidationError('Existen depreciaciones posteriores a la baja; revísalas antes de continuar.')
        for line in self.line_ids.filtered(lambda x: x.date <= date and not x.move_id).sorted('date'):
            line._post()
        self.invalidate_recordset()
        category = self.category_id
        balances = [(category.asset_account_id,-self.cost),(category.accumulated_account_id,self.accumulated)]
        proceeds = 0
        if sale_line:
            sale_line.check_access('read')
            self.env.cr.execute('UPDATE account_move_line SET write_date=write_date WHERE id=%s RETURNING id',[sale_line.id])
            if sale_line.company_id != self.company_id or sale_line.move_id.state != 'posted' or sale_line.move_id.move_type != 'out_invoice' or sale_line.balance >= 0 or sale_line.display_type != 'product':
                raise ValidationError('Selecciona una línea de venta contabilizada de la misma empresa.')
            if self.search_count([('sale_line_id','=',sale_line.id),('state','!=','reversed')]):
                raise ValidationError('La línea de venta ya se aplicó a otro activo.')
            proceeds = -sale_line.balance
            balances.append((sale_line.account_id,proceeds))
        result = self.cost-self.accumulated-proceeds
        balances.append((category.loss_account_id if result >= 0 else category.gain_account_id,result))
        self._entry(date,'disposal',balances)
        internal(self).write({'state':'disposed','sale_line_id':sale_line.id if sale_line else False,'disposal_date':date})

    def _reverse(self, date):
        self._authorize()
        date = self._check_date(date)
        if self.state not in ('running','disposed'):
            raise ValidationError('El activo no tiene movimientos pendientes de reversión.')
        moves = self.move_ids.filtered(lambda m: m.state=='posted' and not m.reversed_entry_id)
        if moves and date < max(moves.mapped('date')):
            raise ValidationError('La reversión no puede preceder al último asiento del activo.')
        for move in moves.sorted(lambda m:(m.date,m.id),reverse=True):
            if move.reversal_move_ids.filtered(lambda m:m.state=='posted'):
                raise ValidationError('Existe una reversión previa; revisa el historial.')
            reversal = internal(move)._reverse_moves([{'date':date,'ref':'Reversión: '+self.name,'erpec_asset_id':self.id,'erpec_asset_kind':'reversal'}])
            internal(reversal).action_post()
            line=self.line_ids.filtered(lambda l:l.move_id==move)
            if line:
                internal(line).write({'reversal_id':reversal.id})
        internal(self).write({'state':'reversed'})


class Depreciation(models.Model):
    _name = 'erpec.asset.line'
    _description = 'Cuota de depreciación'
    _order = 'date,id'
    asset_id = fields.Many2one('erpec.asset',required=True,ondelete='cascade',string='Activo')
    company_id = fields.Many2one(related='asset_id.company_id',store=True)
    currency_id = fields.Many2one(related='asset_id.currency_id')
    date = fields.Date('Fecha',required=True)
    amount = fields.Monetary('Depreciación',required=True)
    move_id = fields.Many2one('account.move',readonly=True,ondelete='restrict',string='Asiento')
    reversal_id = fields.Many2one('account.move',readonly=True,ondelete='restrict',string='Reversión')
    _sql_constraints = [('asset_date_unique','unique(asset_id,date)','Ya existe una cuota para esta fecha.')]

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL:
            raise AccessError('El calendario se genera desde el activo.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL:
            raise AccessError('Usa las acciones del activo para modificar cuotas.')
        return super().write(values)

    def unlink(self):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL or any(self.mapped('move_id')):
            raise AccessError('No se eliminan cuotas contabilizadas ni se altera directamente el calendario.')
        return super().unlink()

    def _post(self):
        self.ensure_one()
        asset=self.asset_id
        asset._authorize()
        self.invalidate_recordset()
        if self.move_id:
            _logger.info('Cuota ya contabilizada correlationId=asset-%s userId=%s',asset.id,self.env.uid)
            return self.move_id
        if asset.state != 'running':
            raise ValidationError('El activo no está en uso.')
        category=asset.category_id
        move=asset._entry(self.date,'depreciation',[(category.expense_account_id,self.amount),(category.accumulated_account_id,-self.amount)])
        internal(self).write({'move_id':move.id})
        return move


class Revision(models.Model):
    _name = 'erpec.asset.revision'
    _description = 'Historial de cambios de estimación'
    asset_id = fields.Many2one('erpec.asset',required=True,ondelete='restrict')
    company_id = fields.Many2one(related='asset_id.company_id',store=True)
    effective_date = fields.Date('Vigencia',required=True)
    previous_months = fields.Integer('Meses anteriores')
    months = fields.Integer('Meses restantes')
    previous_residual = fields.Float('Residual anterior')
    residual = fields.Float('Residual nuevo')
    reason = fields.Text('Justificación',required=True)

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL:
            raise AccessError('Usa el asistente de cambio de estimación.')
        return super().create(values_list)

    def write(self, values):
        raise AccessError('El historial de estimaciones es inmutable.')

    def unlink(self):
        raise AccessError('El historial de estimaciones se conserva.')


class AccountMove(models.Model):
    _inherit = 'account.move'
    erpec_asset_id = fields.Many2one('erpec.asset',readonly=True,copy=False,ondelete='restrict',string='Activo fijo')
    erpec_asset_kind = fields.Selection([('acquisition','Alta'),('depreciation','Depreciación'),('disposal','Baja'),('reversal','Reversión')],readonly=True,copy=False,string='Operación de activo')

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL and any(v.get('erpec_asset_id') or v.get('erpec_asset_kind') for v in values_list):
            raise AccessError('Los asientos de activos se generan desde su ficha.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL and (set(values)&{'erpec_asset_id','erpec_asset_kind'} or (any(self.mapped('erpec_asset_id')) and set(values)&{'state','line_ids','date','journal_id','company_id'})):
            raise AccessError('Usa la reversión del activo para corregir su contabilidad.')
        return super().write(values)

    def _check_asset_source(self):
        if self.env['erpec.asset'].sudo().search_count(['|',('source_line_id','in',self.line_ids.ids),('sale_line_id','in',self.line_ids.ids),('state','!=','reversed')]):
            raise ValidationError('Este comprobante está vinculado a activos; revierte primero esos activos.')

    def button_draft(self):
        self._check_asset_source()
        return super().button_draft()

    def button_cancel(self):
        self._check_asset_source()
        return super().button_cancel()

    def unlink(self):
        if any(self.mapped('erpec_asset_id')):
            raise AccessError('Conserva los asientos de activos y sus reversiones.')
        self._check_asset_source()
        return super().unlink()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _protect_asset_lines(self):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL:
            if any(self.mapped('move_id.erpec_asset_id')):
                raise AccessError('Las líneas contables del activo son inmutables fuera de sus acciones.')
            if self.env['erpec.asset'].sudo().search_count(['|',('source_line_id','in',self.ids),('sale_line_id','in',self.ids),('state','!=','reversed')]):
                raise ValidationError('La línea ya está vinculada a un activo; revísalo antes de modificarla.')

    def write(self, values):
        if set(values)&{'debit','credit','balance','amount_currency','currency_id','account_id','move_id','price_unit','quantity','tax_ids'}:
            self._protect_asset_lines()
        return super().write(values)

    def unlink(self):
        self._protect_asset_lines()
        return super().unlink()

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_asset_token') is not _INTERNAL:
            moves=self.env['account.move'].browse([v['move_id'] for v in values_list if v.get('move_id')])
            if any(moves.mapped('erpec_asset_id')):
                raise AccessError('No se agregan líneas directas a asientos de activos.')
        return super().create(values_list)

    def action_create_erpec_asset(self):
        self.ensure_one()
        privileged(self.env)
        self.check_access('read')
        if self.move_id.state!='posted' or self.move_id.move_type!='in_invoice' or self.balance<=0:
            raise ValidationError('Selecciona una línea de compra contabilizada positiva.')
        used=sum(self.env['erpec.asset'].search([('source_line_id','=',self.id),('state','!=','reversed')]).mapped('cost'))
        return {'type':'ir.actions.act_window','res_model':'erpec.asset','view_mode':'form','target':'current',
                'context':{'default_source_line_id':self.id,'default_company_id':self.company_id.id,'default_cost':max(self.balance-used,0),
                           'default_name':self.name,'default_acquisition_date':str(self.move_id.date)}}
