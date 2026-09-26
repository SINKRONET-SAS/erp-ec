"""Liquidación y pago de décimos acumulados (DI26-C.2, hallazgo DI26-05).

El motor de nómina provisiona cada mes el décimo tercero y el décimo cuarto no mensualizados (resultado
'thirteenth'/'fourteenth' de cada línea contabilizada, contra la cuenta de crédito del mapeo de la política). Esta
liquidación toma lo provisionado en el período legal, traslada el pasivo a nómina por pagar por empleado con la fecha
límite legal como vencimiento y deja registrar el pago; nada se incluye dos veces.

Base legal verificada el 25-09-2026 (base legal publicada por el Ministerio del Trabajo): art. 111 del Código del
Trabajo, décimo tercero hasta el 24 de diciembre, doceava parte de lo percibido durante el año calendario; décimo
cuarto hasta el 15 de marzo (Costa e Insular) y el 15 de agosto (Sierra y Amazonía). El corte propuesto para el décimo
tercero (1 de diciembre al 30 de noviembre) es la práctica del Ministerio del Trabajo y de los instructivos del
Ministerio de Economía y Finanzas, no un texto legal: por eso las fechas del período son editables antes de calcular."""
import calendar
import json
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.erpec_payroll.fourteenth_regime import FOURTEENTH_REGIMES

_TOKEN = object()
KINDS = [('thirteenth', 'Décimo tercero'), ('fourteenth', 'Décimo cuarto')]


def require_payroll_manager(env):
    if not env.su and not env.user.has_group('erpec_payroll.group_payroll_manager'):
        raise AccessError('Se requiere el permiso de responsable de nómina.')


def legal_window(kind, regime, year):
    """(inicio, corte, fecha límite de pago) del período legal que se paga en `year`."""
    if kind == 'thirteenth':
        return date(year - 1, 12, 1), date(year, 11, 30), date(year, 12, 24)
    if regime == 'sierra_amazonia':
        return date(year - 1, 8, 1), date(year, 7, 31), date(year, 8, 15)
    if regime == 'costa_insular':
        return date(year - 1, 3, 1), date(year, 2, calendar.monthrange(year, 2)[1]), date(year, 3, 15)
    return False, False, False


class BonusSettlement(models.Model):
    _name = 'erpec.payroll.bonus.settlement'
    _description = 'Liquidación de décimos acumulados'
    _order = 'year desc, id desc'

    name = fields.Char('Liquidación', compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', string='Empresa', required=True, default=lambda self: self.env.company)
    kind = fields.Selection(KINDS, string='Décimo', required=True)
    regime = fields.Selection(FOURTEENTH_REGIMES, string='Régimen del décimo cuarto')
    year = fields.Integer('Año de pago', required=True, default=lambda self: fields.Date.context_today(self).year)
    date_from = fields.Date('Inicio del período', compute='_compute_window', store=True, readonly=False)
    date_to = fields.Date('Corte del período', compute='_compute_window', store=True, readonly=False)
    deadline = fields.Date('Fecha límite legal de pago', compute='_compute_window', store=True, readonly=False)
    state = fields.Selection([('draft', 'Borrador'), ('computed', 'Calculada'), ('posted', 'Contabilizada'), ('reversed', 'Revertida')],
                             string='Estado', default='draft', required=True, readonly=True)
    line_ids = fields.One2many('erpec.payroll.bonus.settlement.line', 'settlement_id', string='Empleados', readonly=True)
    total = fields.Float('Total a pagar', compute='_compute_total', store=True, digits=(16, 2))
    move_id = fields.Many2one('account.move', string='Asiento de liquidación', readonly=True, ondelete='restrict')
    reversal_id = fields.Many2one('account.move', string='Reversión', readonly=True, ondelete='restrict')
    legal_notice = fields.Text('Base legal', readonly=True, default=(
        'Décimo tercero: hasta el 24 de diciembre (art. 111 CT). Décimo cuarto: hasta el 15 de marzo en Costa e Insular y '
        'hasta el 15 de agosto en Sierra y Amazonía. El corte del período es editable: revísalo con el responsable '
        'laboral antes de calcular.'))

    @api.depends('kind', 'regime', 'year', 'company_id')
    def _compute_name(self):
        labels = dict(KINDS)
        for settlement in self:
            settlement.name = '%s %s — %s' % (labels.get(settlement.kind, ''), settlement.year or '', settlement.company_id.name or '')

    @api.depends('kind', 'regime', 'year')
    def _compute_window(self):
        for settlement in self:
            start, end, deadline = legal_window(settlement.kind, settlement.regime, settlement.year) if settlement.year else (False,) * 3
            settlement.date_from, settlement.date_to, settlement.deadline = start, end, deadline

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for settlement in self:
            settlement.total = sum(settlement.line_ids.mapped('amount'))

    @api.constrains('kind', 'regime')
    def _check_regime(self):
        for settlement in self:
            if settlement.kind == 'fourteenth' and not settlement.regime:
                raise ValidationError('Elige el régimen del décimo cuarto (Sierra y Amazonía, o Costa e Insular).')

    def _set(self, values):
        return self.with_context(_erpec_bonus_token=_TOKEN).write(values)

    def write(self, values):
        protected = set(values) - {'date_from', 'date_to', 'deadline', 'regime', 'year', 'kind', 'company_id'}
        if self.env.context.get('_erpec_bonus_token') is not _TOKEN:
            if protected or any(settlement.state not in ('draft', 'computed') for settlement in self):
                raise AccessError('La liquidación solo cambia por sus acciones; una liquidación contabilizada se revierte.')
        return super().write(values)

    def unlink(self):
        if any(settlement.state not in ('draft', 'computed') for settlement in self):
            raise ValidationError('Una liquidación contabilizada se revierte; no se elimina.')
        self.line_ids.with_context(_erpec_bonus_token=_TOKEN).unlink()
        return super().unlink()

    def _already_settled(self):
        return self.env['erpec.payroll.bonus.settlement.line'].search([
            ('settlement_id.kind', '=', self.kind), ('settlement_id.state', '=', 'posted'),
            ('settlement_id.company_id', '=', self.company_id.id), ('settlement_id', '!=', self.id)]).payroll_line_ids

    def action_compute(self):
        self.ensure_one()
        require_payroll_manager(self.env)
        if self.state not in ('draft', 'computed'):
            raise ValidationError('Solo se calcula una liquidación en borrador.')
        if not (self.date_from and self.date_to) or self.date_from > self.date_to:
            raise ValidationError('Revisa el inicio y el corte del período.')
        periods = self.env['erpec.payroll.period'].search([('company_id', '=', self.company_id.id), ('state', '=', 'posted')])
        first = self.date_from.replace(day=1)
        periods = periods.filtered(lambda p: first <= date(p.year, p.month, 1) <= self.date_to)
        settled = self._already_settled()
        per_employee, missing_regime = {}, set()
        for line in periods.line_ids - settled:
            if self.kind == 'fourteenth' and line.employee_id.ec_fourteenth_regime != self.regime:
                if not line.employee_id.ec_fourteenth_regime:
                    missing_regime.add(line.employee_id.name)
                continue
            amount = line._result_value(self.kind)
            if not amount:
                continue
            entry = per_employee.setdefault(line.employee_id.id, {'partner_id': line.partner_id.id, 'amount': 0.0, 'lines': []})
            entry['amount'] += amount
            entry['lines'].append(line.id)
        if missing_regime:
            raise ValidationError('Declara el régimen del décimo cuarto de: %s.' % ', '.join(sorted(missing_regime)))
        self.line_ids.with_context(_erpec_bonus_token=_TOKEN).unlink()
        self.env['erpec.payroll.bonus.settlement.line'].with_context(_erpec_bonus_token=_TOKEN).create([
            {'settlement_id': self.id, 'employee_id': employee_id, 'partner_id': values['partner_id'],
             'amount': round(values['amount'], 2), 'payroll_line_ids': [(6, 0, values['lines'])]}
            for employee_id, values in per_employee.items()])
        self._set({'state': 'computed'})
        return True

    def action_post(self):
        self.ensure_one()
        require_payroll_manager(self.env)
        if self.state != 'computed' or not self.line_ids:
            raise ValidationError('Calcula la liquidación y revisa sus empleados antes de contabilizar.')
        overlap = self.line_ids.payroll_line_ids & self._already_settled()
        if overlap:
            raise ValidationError('Hay nóminas ya incluidas en otra liquidación contabilizada; vuelve a calcular.')
        payable = self.company_id.erpec_payroll_payable_id
        if not payable or payable.account_type != 'liability_payable' or not payable.reconcile:
            raise ValidationError('Configura una cuenta conciliable de nómina por pagar para esta empresa.')
        label = dict(KINDS)[self.kind]
        move_lines, journal = [], False
        for item in self.line_ids:
            for payroll in item.payroll_line_ids:
                policy = payroll.period_id.policy_id
                mapping = policy.mapping_ids.filtered(lambda m: m.concept == self.kind)
                if len(mapping) != 1 or not mapping.credit_id:
                    raise ValidationError('La política %s no tiene la cuenta de provisión del %s.' % (policy.name, label.lower()))
                journal = journal or policy.journal_id
                amount = payroll._result_value(self.kind)
                move_lines.append((0, 0, {'name': '%s provisionado · %s' % (label, item.employee_id.name), 'account_id': mapping.credit_id.id,
                                          'partner_id': item.partner_id.id, 'debit': amount}))
                move_lines.append((0, 0, {'name': '%s por pagar · %s' % (label, item.employee_id.name), 'account_id': payable.id,
                                          'partner_id': item.partner_id.id, 'credit': amount, 'date_maturity': self.deadline}))
        move = self.env['account.move'].create({'move_type': 'entry', 'company_id': self.company_id.id, 'journal_id': journal.id,
                                                'date': fields.Date.context_today(self), 'ref': 'Liquidación ' + self.name, 'line_ids': move_lines})
        move.action_post()
        self._set({'move_id': move.id, 'state': 'posted'})
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'res_id': move.id, 'view_mode': 'form'}

    def action_reverse(self):
        self.ensure_one()
        require_payroll_manager(self.env)
        if self.state != 'posted':
            raise ValidationError('Solo se revierte una liquidación contabilizada.')
        if self.move_id.line_ids.filtered(lambda l: l.reconciled or l.matched_debit_ids or l.matched_credit_ids):
            raise ValidationError('Revierte primero los pagos registrados de esta liquidación.')
        reverse = self.move_id._reverse_moves([{'date': fields.Date.context_today(self), 'ref': 'Reversión ' + self.name}], cancel=True)
        self._set({'reversal_id': reverse.id, 'state': 'reversed'})
        return True


class BonusSettlementLine(models.Model):
    _name = 'erpec.payroll.bonus.settlement.line'
    _description = 'Empleado de una liquidación de décimos'
    settlement_id = fields.Many2one('erpec.payroll.bonus.settlement', string='Liquidación', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='settlement_id.company_id', string='Empresa', store=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    partner_id = fields.Many2one('res.partner', string='Tercero para pago', required=True)
    amount = fields.Float('Monto', digits=(16, 2), required=True)
    months = fields.Integer('Meses incluidos', compute='_compute_months')
    payroll_line_ids = fields.Many2many('erpec.payroll.line', string='Nóminas incluidas')
    residual = fields.Float('Saldo por pagar', compute='_compute_residual', digits=(16, 2))

    def _compute_months(self):
        for line in self:
            line.months = len(line.payroll_line_ids)

    def _payable_lines(self):
        self.ensure_one()
        move = self.settlement_id.move_id
        return move.line_ids.filtered(lambda l: l.account_type == 'liability_payable' and l.partner_id == self.partner_id)

    def _compute_residual(self):
        for line in self:
            line.residual = abs(sum(line._payable_lines().mapped('amount_residual'))) if line.settlement_id.move_id else line.amount

    def write(self, values):
        if self.env.context.get('_erpec_bonus_token') is not _TOKEN:
            raise AccessError('Las líneas de la liquidación se generan al calcular.')
        return super().write(values)

    def unlink(self):
        if self.env.context.get('_erpec_bonus_token') is not _TOKEN:
            raise AccessError('Las líneas de la liquidación se generan al calcular.')
        return super().unlink()

    def action_pay(self):
        self.ensure_one()
        require_payroll_manager(self.env)
        if self.settlement_id.state != 'posted':
            raise ValidationError('Contabiliza la liquidación antes de registrar pagos.')
        pending = self._payable_lines().filtered(lambda l: not l.reconciled)
        if not pending:
            raise ValidationError('No queda saldo por pagar a este empleado.')
        bank = self.settlement_id.company_id.erpec_payroll_bank_journal_id
        if not bank:
            raise ValidationError('Configura el banco de pagos de nómina de la empresa.')
        return {'type': 'ir.actions.act_window', 'name': 'Registrar pago de décimo', 'res_model': 'account.payment.register',
                'view_mode': 'form', 'target': 'new', 'context': {'active_model': 'account.move.line', 'active_ids': pending.ids,
                                                                   'default_journal_id': bank.id}}


class PayrollLine(models.Model):
    _inherit = 'erpec.payroll.line'

    def _result_value(self, key):
        """Valor contabilizado de un concepto en el resultado inmutable de la línea."""
        self.ensure_one()
        return float(json.loads(self.result or '{}').get(key, 0.0))
