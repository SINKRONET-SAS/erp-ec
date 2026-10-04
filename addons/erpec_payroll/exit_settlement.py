"""Salida de empleados y acta de finiquito (plan NM27).

Dos modalidades explícitas, tomadas de la referencia SKNOMINA (RSF26):
- `rol_primero`: el rol del mes de salida incluye al empleado prorrateado hasta `end_date` y el finiquito no
  repite el sueldo; exige ese rol aprobado (cierre) antes de emitir el acta.
- `con_finiquito`: el mes de salida no tiene rol; el finiquito paga el sueldo pendiente.
Un solo pago del último mes: cualquier rol que contradiga la modalidad bloquea el cálculo y la emisión.
No contabiliza el finiquito ni retiene impuesto a la renta; no archiva al empleado ni transmite pagos.
"""
import hashlib
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .fourteenth_regime import FOURTEENTH_REGIMES
from .models import _INTERNAL, manager
from .settlement import CAUSE_CHOICES, MODALITIES, settle

RESULT_FIELDS = {
    'pending_salary': 'amount_pending_salary', 'thirteenth': 'amount_thirteenth', 'fourteenth': 'amount_fourteenth',
    'vacation': 'amount_vacation', 'reserve': 'amount_reserve', 'dismissal': 'amount_dismissal',
    'desahucio': 'amount_desahucio', 'gross': 'amount_gross', 'personal_iess': 'amount_personal_iess',
    'other_deductions': 'amount_other_deductions', 'net': 'amount_net',
}
SETTLED_STATES = ('closed', 'posted')


class PayrollExit(models.Model):
    _name = 'erpec.payroll.exit'
    _description = 'Salida de empleado y acta de finiquito'
    _inherit = ['mail.thread']
    _order = 'end_date desc, id desc'

    name = fields.Char('Acta', readonly=True, copy=False, default='Nuevo')
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    policy_id = fields.Many2one('erpec.payroll.policy', 'Versión y autoridad', required=True, domain="[('company_id','=',company_id),('state','=','active')]")
    employee_id = fields.Many2one('hr.employee', 'Empleado', required=True, check_company=True)
    start_date = fields.Date('Ingreso', required=True)
    end_date = fields.Date('Fecha de salida', required=True)
    wage = fields.Float('Último sueldo mensual', required=True)
    cause = fields.Selection(CAUSE_CHOICES, 'Causal de terminación', required=True)
    modality = fields.Selection(MODALITIES, 'Pago del último mes', required=True, default='rol_primero',
        help='Rol primero: el rol del mes de salida paga el sueldo proporcional hasta la fecha de salida y el finiquito no lo repite. '
             'Con finiquito: el mes de salida no tiene rol y el acta paga el sueldo pendiente.')
    fourteenth_regime = fields.Selection(FOURTEENTH_REGIMES, 'Régimen del décimo cuarto', related='employee_id.ec_fourteenth_regime', readonly=True)
    vacation_days_taken = fields.Float('Días de vacaciones ya gozados', help='Días tomados durante toda la relación laboral; se descuentan de los devengados.')
    other_deductions = fields.Float('Otros descuentos (préstamos, anticipos, equipos)', help='Conciliación manual: el finiquito no consulta el libro de anticipos.')
    notes = fields.Text('Observaciones')
    state = fields.Selection([('draft', 'Borrador'), ('calculated', 'Calculado'), ('approved', 'Acta emitida'), ('paid', 'Pagado'), ('cancelled', 'Anulado')], default='draft', readonly=True, copy=False, string='Estado', tracking=True)
    result = fields.Text('Desglose calculado', readonly=True, copy=False)
    input_hash = fields.Char('Huella de cálculo', readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', 'Emitida por', readonly=True, copy=False)
    approved_date = fields.Datetime('Emitida el', readonly=True, copy=False)
    paid_date = fields.Date('Fecha de pago', copy=False)
    payment_reference = fields.Char('Referencia del pago', copy=False, help='Referencia informada por el responsable; este módulo no transmite pagos ni archivos bancarios.')
    payroll_line_id = fields.Many2one('erpec.payroll.line', 'Rol del mes de salida', compute='_compute_payroll_line')
    amount_pending_salary = fields.Float('Sueldo pendiente del mes', compute='_compute_amounts')
    amount_thirteenth = fields.Float('Décimo tercero proporcional', compute='_compute_amounts')
    amount_fourteenth = fields.Float('Décimo cuarto proporcional', compute='_compute_amounts')
    amount_vacation = fields.Float('Vacaciones no gozadas', compute='_compute_amounts')
    amount_reserve = fields.Float('Fondo de reserva pendiente', compute='_compute_amounts')
    amount_dismissal = fields.Float('Indemnización por despido intempestivo', compute='_compute_amounts')
    amount_desahucio = fields.Float('Bonificación por desahucio', compute='_compute_amounts')
    amount_gross = fields.Float('Total de haberes', compute='_compute_amounts')
    amount_personal_iess = fields.Float('Aporte personal IESS sobre sueldo pendiente', compute='_compute_amounts')
    amount_other_deductions = fields.Float('Otros descuentos', compute='_compute_amounts')
    amount_net = fields.Float('Neto a pagar', compute='_compute_amounts')
    detail_text = fields.Text('Bases del cálculo', compute='_compute_amounts')
    next_step = fields.Char('Siguiente paso', compute='_compute_next_step')

    def _update(self, values):
        return self.with_context(_erpec_payroll_token=_INTERNAL).write(values)

    @api.model_create_multi
    def create(self, values_list):
        if any(set(values) & {'state', 'result', 'input_hash', 'approved_by', 'approved_date'} for values in values_list) and self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            raise ValidationError('Los resultados se generan mediante las acciones del finiquito.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            manager(self.env)
            if set(values) & {'state', 'result', 'input_hash', 'approved_by', 'approved_date', 'name'}:
                raise ValidationError('Los resultados se generan mediante las acciones del finiquito.')
            if set(values) & {'paid_date', 'payment_reference'} and any(item.state in ('paid', 'cancelled') for item in self):
                raise ValidationError('El pago de un finiquito registrado o anulado no se modifica.')
            locked = {'company_id', 'policy_id', 'employee_id', 'start_date', 'end_date', 'wage', 'cause', 'modality', 'vacation_days_taken', 'other_deductions'}
            if set(values) & locked and any(item.state != 'draft' and item.state != 'calculated' for item in self):
                raise ValidationError('Un acta emitida, pagada o anulada no se modifica; anula la salida y registra una nueva.')
            if set(values) & locked:
                values = dict(values, result=False, input_hash=False)
                self.filtered(lambda item: item.state == 'calculated')._update({'state': 'draft'})
        return super().write(values)

    @api.constrains('company_id', 'policy_id', 'employee_id', 'start_date', 'end_date')
    def _check_exit(self):
        for item in self:
            policy = item.policy_id
            if policy.company_id != item.company_id or policy.authority != 'native' or policy.year != item.end_date.year:
                raise ValidationError('La versión debe ser nativa, de la misma empresa y del año de la fecha de salida.')
            if item.end_date < item.start_date:
                raise ValidationError('La fecha de salida no puede ser anterior al ingreso.')
            duplicate = self.search_count([('id', '!=', item.id), ('employee_id', '=', item.employee_id.id), ('state', 'not in', ('cancelled',))])
            if duplicate:
                raise ValidationError('El empleado ya tiene una salida registrada; anúlala antes de crear otra.')

    @api.onchange('employee_id')
    def _onchange_employee(self):
        line = self.env['erpec.payroll.line'].search([('employee_id', '=', self.employee_id.id), ('period_id.state', '!=', 'reversed')], order='id desc', limit=1) if self.employee_id else False
        if line:
            self.start_date, self.wage = line.start_date, line.wage

    def _exit_key(self):
        return self.end_date.year, self.end_date.month

    @api.depends('employee_id', 'end_date', 'state')
    def _compute_payroll_line(self):
        for item in self:
            item.payroll_line_id = item._lines().filtered(lambda line: (line.period_id.year, line.period_id.month) == item._exit_key())[:1] if item.employee_id and item.end_date else False

    def _lines(self):
        """Líneas vigentes del empleado en cierres no revertidos."""
        self.ensure_one()
        return self.env['erpec.payroll.line'].search([('employee_id', '=', self.employee_id.id), ('company_id', '=', self.company_id.id), ('period_id.state', '!=', 'reversed')])

    def _line_conflict(self, line):
        """Motivo por el que un rol contradice esta salida, o False. Autoridad única de la regla de doble pago."""
        self.ensure_one()
        key = (line.period_id.year, line.period_id.month)
        if key > self._exit_key():
            return 'El empleado tiene una salida el %s; no se puede incluir en un período posterior.' % self.end_date
        if key == self._exit_key():
            if self.modality == 'con_finiquito':
                return 'La salida se paga con el finiquito: incluirlo en el rol del mes de salida pagaría el sueldo dos veces.'
            if line.end_date != self.end_date:
                return 'El rol del mes de salida debe prorratearse hasta la fecha de salida (%s).' % self.end_date
        return False

    def _check_payroll_lines(self, require_settled=False):
        self.ensure_one()
        for line in self._lines():
            reason = self._line_conflict(line)
            if reason:
                raise ValidationError(reason)
        if require_settled and self.modality == 'rol_primero':
            line = self.payroll_line_id
            if not line:
                raise ValidationError('Genera primero el rol de pagos del mes de salida; después podrás emitir el acta.')
            if line.period_id.state not in SETTLED_STATES:
                raise ValidationError('Aprueba el cierre del rol del mes de salida antes de emitir el acta.')

    def _paid_by_payroll(self):
        """Lo ya pagado o acreditado por los roles del empleado, para no pagarlo de nuevo en el acta."""
        self.ensure_one()
        from .settlement import fourteenth_window, thirteenth_window
        windows = {'thirteenth': thirteenth_window(self.end_date), 'fourteenth': fourteenth_window(self.end_date, self.fourteenth_regime), 'reserve': self.end_date.replace(month=1, day=1)}
        totals = {'thirteenth_paid': 0.0, 'fourteenth_paid': 0.0, 'reserve_paid': 0.0, 'reserve_covered': 0.0}
        for line in self._lines().filtered(lambda item: item.period_id.state in SETTLED_STATES):
            result = json.loads(line.result or '{}')
            month = (line.period_id.year, line.period_id.month)
            for kind, begin in windows.items():
                if (begin.year, begin.month) <= month <= self._exit_key():
                    if kind == 'reserve':
                        totals['reserve_paid'] += result.get('reserve_paid', 0)
                        totals['reserve_covered'] += result.get('reserve_iess', 0)
                    else:
                        totals[kind + '_paid'] += result.get(kind + '_paid', 0)
        return totals

    def _inputs(self):
        self.ensure_one()
        data = {'cause': self.cause, 'modality': self.modality, 'start_date': self.start_date, 'end_date': self.end_date, 'wage': self.wage,
                'fourteenth_regime': self.fourteenth_regime, 'vacation_days_taken': self.vacation_days_taken, 'other_deductions': self.other_deductions}
        data.update(self._paid_by_payroll())
        return data

    def action_calculate(self):
        for item in self:
            manager(self.env)
            item.check_access('write')
            if item.state not in ('draft', 'calculated'):
                raise ValidationError('El acta ya fue emitida, pagada o anulada; no se recalcula.')
            policy, company = item.policy_id, item.company_id
            if policy.state != 'active' or not policy.synthetic or company.vat or 'DEMO' not in company.name:
                raise ValidationError('Este incremento admite únicamente una empresa DEMO sin RUC y una versión activa de demostración.')
            item._check_payroll_lines()
            data = item._inputs()
            try:
                result = settle(data, json.loads(policy.parameters))
            except (ValueError, KeyError, TypeError) as error:
                raise ValidationError('Revisa los datos de la salida: ' + str(error)) from None
            digest = hashlib.sha256((json.dumps(data, sort_keys=True, default=str) + policy.parameters).encode()).hexdigest()
            item._update({'result': json.dumps(result, sort_keys=True), 'input_hash': digest, 'state': 'calculated'})
        return True

    def action_approve(self):
        for item in self:
            manager(self.env)
            item.check_access('write')
            if item.state != 'calculated':
                raise ValidationError('Calcula el finiquito antes de emitir el acta.')
            item._check_payroll_lines(require_settled=True)
            digest = hashlib.sha256((json.dumps(item._inputs(), sort_keys=True, default=str) + item.policy_id.parameters).encode()).hexdigest()
            if digest != item.input_hash:
                raise ValidationError('Los roles o datos cambiaron desde el cálculo; recalcula el finiquito antes de emitir el acta.')
            number = self.env['ir.sequence'].with_company(item.company_id).next_by_code('erpec.payroll.exit') or 'FIN-%s' % item.id
            item._update({'state': 'approved', 'name': number, 'approved_by': self.env.user.id, 'approved_date': fields.Datetime.now()})
        return True

    def action_mark_paid(self):
        for item in self:
            manager(self.env)
            item.check_access('write')
            if item.state != 'approved' or not item.payment_reference or not item.paid_date:
                raise ValidationError('Emite el acta e indica la fecha y la referencia del pago para registrarlo.')
            item._update({'state': 'paid'})
        return True

    def action_cancel(self):
        for item in self:
            manager(self.env)
            item.check_access('write')
            if item.state == 'paid':
                raise ValidationError('Un finiquito pagado no se anula desde aquí.')
            item._update({'state': 'cancelled'})
        return True

    @api.depends('result')
    def _compute_amounts(self):
        for item in self:
            result = json.loads(item.result or '{}')
            for key, field_name in RESULT_FIELDS.items():
                item[field_name] = result.get(key, 0)
            detail = result.get('detail', {})
            item.detail_text = '\n'.join('%s: %s' % (key, value) for key, value in detail.items()) if detail else False

    @api.depends('state', 'modality', 'payroll_line_id', 'payroll_line_id.period_id.state')
    def _compute_next_step(self):
        for item in self:
            if item.state == 'draft':
                item.next_step = 'Calcula el finiquito.'
            elif item.state == 'calculated':
                if item.modality == 'rol_primero' and (not item.payroll_line_id or item.payroll_line_id.period_id.state not in SETTLED_STATES):
                    item.next_step = 'Genera, calcula y cierra el rol del mes de salida (con la fecha de salida en la línea); luego emite el acta.'
                else:
                    item.next_step = 'Emite el acta de finiquito.'
            elif item.state == 'approved':
                item.next_step = 'Imprime el acta y registra el pago con su referencia.'
            else:
                item.next_step = False
