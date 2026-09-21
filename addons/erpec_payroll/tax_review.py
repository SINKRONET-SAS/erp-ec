"""Ensayos sintéticos para revisión externa; no alteran nóminas ni anexos."""
import json
from decimal import Decimal, ROUND_DOWN
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from .engine import annual_income_tax, money, number, personal_expense_cap
from .models import manager
from .parameters_ec2026 import PARAMS
from .tax_review_cases import BASE_INPUTS, CASES

INPUTS = ('current_income', 'current_iess', 'current_withheld', 'other_income',
          'other_iess', 'other_withheld', 'personal_expenses', 'dependents', 'remaining_months',
          'exempt_thirteenth', 'exempt_fourteenth', 'exempt_reserve')

RESULTS = ('exempt_income', 'total_informed', 'combined_income', 'combined_iess', 'annual_base', 'tax_caused',
           'expense_cap', 'rebate', 'annual_tax', 'without_other_tax', 'tax_increase',
           'total_withheld', 'pending_tax', 'excess_withheld', 'monthly_estimate', 'last_estimate')


def review_calculation(data, parameters):
    """Consolida una sola vez los importes anuales y reutiliza la tarifa común."""
    values = {key: number(data[key]) for key in INPUTS}
    region = data.get('galapagos', 'NO')
    special = data.get('special_condition', 'none')
    if special not in ('none', 'holder', 'dependent'):
        raise ValueError('Selecciona un supuesto especial válido para el ensayo.')
    if special == 'dependent' and values['dependents'] < 1:
        raise ValueError('El supuesto de una carga familiar requiere al menos una carga.')
    special_expense = special != 'none'
    if region not in ('NO', 'SI'):
        raise ValueError('Selecciona Continente o Galápagos para el ensayo.')
    if any(value < 0 for value in values.values()):
        raise ValueError('Los importes, cargas y meses no pueden ser negativos.')
    if not 1 <= values['remaining_months'] <= 12 or values['remaining_months'] % 1:
        raise ValueError('Indica entre 1 y 12 meses pendientes, incluyendo el mes del ajuste.')
    if values['dependents'] % 1:
        raise ValueError('Las cargas familiares deben ser un número entero.')
    for prefix in ('current', 'other'):
        if values[prefix+'_iess'] > values[prefix+'_income']:
            raise ValueError('El IESS personal no puede superar el ingreso gravado del mismo empleador.')
    income = money(values['current_income'] + values['other_income'])
    iess = money(values['current_iess'] + values['other_iess'])
    base = money(income - iess)
    caused, rebate, annual = annual_income_tax(base, values['personal_expenses'], parameters, int(values['dependents']), region, special_expense=special_expense)
    _, _, without = annual_income_tax(money(values['current_income'] - values['current_iess']),
                                      values['personal_expenses'], parameters, int(values['dependents']), region, special_expense=special_expense)
    annual, without = money(annual), money(without)
    withheld = money(values['current_withheld'] + values['other_withheld'])
    pending, excess = max(Decimal(0), annual - withheld), max(Decimal(0), withheld - annual)
    # Redondeo descendente en cuotas preliminares para que la última nunca sea negativa.
    months = int(values['remaining_months'])
    monthly = (pending / months).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    exempt = money(sum(values[key] for key in ('exempt_thirteenth', 'exempt_fourteenth', 'exempt_reserve')))
    return dict(exempt_income=exempt, total_informed=money(income+exempt),
                combined_income=income, combined_iess=iess, annual_base=base,
                tax_caused=money(caused), expense_cap=money(personal_expense_cap(parameters['expense_limit'], int(values['dependents']), region, special_expense=special_expense)),
                rebate=money(rebate), annual_tax=annual, without_other_tax=without,
                tax_increase=money(annual-without), total_withheld=withheld,
                pending_tax=money(pending), excess_withheld=money(excess),
                monthly_estimate=monthly, last_estimate=money(pending-monthly*(months-1)))


class TaxReview(models.Model):
    _name = 'erpec.payroll.tax.review'
    _description = 'Ensayo tributario de renta'
    _check_company_auto = True
    _order = 'name, id'

    name = fields.Char('Caso de revisión', required=True, default='Ensayo de renta · persona ficticia')
    company_id = fields.Many2one('res.company', string='Empresa demo', required=True, default=lambda self: self.env.company)
    policy_id = fields.Many2one('erpec.payroll.policy', string='Política 2026', required=True, check_company=True,
                               domain="[('company_id', '=', company_id), ('year', '=', 2026), ('synthetic', '=', True)]")
    year = fields.Integer(related='policy_id.year', string='Año')
    parameter_summary = fields.Text(related='policy_id.parameter_summary', string='Tabla y parámetros aplicados')
    scenario = fields.Selection([(key, case[0]) for key, case in CASES.items()], string='Referencia a cargar', required=True, default='previous')
    current_income = fields.Float('Ingreso gravado anual · empleador actual', digits=(16, 2), default=18000,
                                  help='Total anual proyectado de este empleador. No incluye al empleador anterior ni ingresos exentos.')
    current_iess = fields.Float('IESS personal anual · empleador actual', digits=(16, 2), default=1701,
                                help='Aporte personal a cargo del trabajador sobre los ingresos indicados.')
    current_withheld = fields.Float('IR ya retenido · empleador actual', digits=(16, 2), default=50)
    other_income = fields.Float('Ingreso gravado · otro empleador', digits=(16, 2), default=6000,
                                help='Acumulado anual del comprobante anterior; se agrega una sola vez, no se multiplica por doce.')
    other_iess = fields.Float('IESS personal · otro empleador', digits=(16, 2), default=567)
    other_withheld = fields.Float('IR retenido · otro empleador', digits=(16, 2), default=150,
                                  help='Crédito contra el impuesto, no deducción de la base imponible.')
    personal_expenses = fields.Float('Gastos personales anuales', digits=(16, 2), default=1000)
    dependents = fields.Integer('Cargas familiares', default=0)
    remaining_months = fields.Integer('Meses pendientes del ajuste', default=3)
    galapagos = fields.Selection([('NO', 'Continente'), ('SI', 'Galápagos · elegibilidad por revisar')], string='Región del ensayo', default='NO', required=True)
    special_condition = fields.Selection([
        ('none', 'General · según cargas'),
        ('holder', '100 canastas · titular ficticio'),
        ('dependent', '100 canastas · carga familiar ficticia')],
        string='Supuesto de rebaja', default='none', required=True,
        help='Discapacidad o enfermedad catastrófica, rara o huérfana. Selección sintética; no acredita elegibilidad ni calcula exenciones de la base.')
    exempt_thirteenth = fields.Float('Décimo tercero informado (exento)', digits=(16, 2))
    exempt_fourteenth = fields.Float('Décimo cuarto informado (exento)', digits=(16, 2))
    exempt_reserve = fields.Float('Fondo de reserva informado (exento)', digits=(16, 2))
    exempt_income = fields.Float('Décimos y reserva excluidos de la base', compute='_compute_review', digits=(16, 2))
    total_informed = fields.Float('Total informado, incluidos exentos', compute='_compute_review', digits=(16, 2))
    reviewer_notes = fields.Text('Observaciones del experto', help='Registrar el caso, cambio, resultado esperado y conclusión. No activa aceptación legal.')
    validation_error = fields.Text('Revisión de entradas', compute='_compute_review')
    reference_note = fields.Text('Cálculo independiente de referencia', compute='_compute_review')
    reference_status = fields.Char('Comparación con referencia', compute='_compute_review')
    combined_income = fields.Float('Ingresos gravados sumados', compute='_compute_review', digits=(16, 2))
    combined_iess = fields.Float('IESS personal sumado', compute='_compute_review', digits=(16, 2))
    annual_base = fields.Float('Base imponible anual', compute='_compute_review', digits=(16, 2))
    tax_caused = fields.Float('IR causado según tabla', compute='_compute_review', digits=(16, 2))
    expense_cap = fields.Float('Tope de gastos del supuesto', compute='_compute_review', digits=(16, 2))
    rebate = fields.Float('Rebaja calculada por gastos', compute='_compute_review', digits=(16, 2))
    annual_tax = fields.Float('IR anual después de rebaja', compute='_compute_review', digits=(16, 2))
    without_other_tax = fields.Float('IR anual sin otro empleador', compute='_compute_review', digits=(16, 2))
    tax_increase = fields.Float('Incremento de IR al incluirlo', compute='_compute_review', digits=(16, 2))
    total_withheld = fields.Float('Retenciones ya realizadas', compute='_compute_review', digits=(16, 2))
    pending_tax = fields.Float('Saldo de IR pendiente', compute='_compute_review', digits=(16, 2))
    excess_withheld = fields.Float('Retenciones superiores al IR', compute='_compute_review', digits=(16, 2))
    monthly_estimate = fields.Float('Cuota orientativa por mes previo al último', compute='_compute_review', digits=(16, 2))
    last_estimate = fields.Float('Última cuota con ajuste de centavos', compute='_compute_review', digits=(16, 2))

    def _review_values(self):
        self.ensure_one()
        if (self.company_id.vat or 'DEMO' not in self.company_id.name.upper()
                or self.policy_id.company_id != self.company_id
                or self.policy_id.year != 2026 or not self.policy_id.synthetic):
            raise ValueError('Utiliza una empresa DEMO sin RUC y una política sintética 2026 de la misma empresa.')
        parameters = json.loads(self.policy_id.parameters or '{}')
        data = {key: self[key] for key in (*INPUTS, 'galapagos', 'special_condition')}
        return data, parameters, review_calculation(data, parameters)

    @api.depends(*INPUTS, 'galapagos', 'special_condition', 'scenario', 'policy_id.parameters', 'policy_id.synthetic', 'policy_id.year',
                 'policy_id.company_id', 'company_id', 'company_id.name', 'company_id.vat')
    def _compute_review(self):
        for record in self:
            for key in RESULTS:
                record[key] = 0
            record.validation_error = False
            case = CASES[record.scenario or 'previous']
            record.reference_note = case[6] + ' Referencia aritmética, pendiente de aceptación externa.'
            record.reference_status = 'Entradas modificadas: revisar el nuevo resultado con el experto.'
            try:
                data, parameters, result = record._review_values()
            except (ValueError, TypeError, KeyError) as error:
                record.validation_error = 'No se puede calcular: '+str(error)
                record.reference_status = 'Corrige las entradas para calcular.'
            else:
                for key, value in result.items():
                    record[key] = float(value)
                expected_inputs = dict(BASE_INPUTS, **case[1])
                tax_keys = ('tax_brackets', 'expense_limit', 'rebate_rate')
                if data == expected_inputs and all(parameters.get(key) == PARAMS[key] for key in tax_keys):
                    actual = tuple(money(result[key]) for key in ('annual_base', 'tax_caused', 'annual_tax', 'pending_tax'))
                    record.reference_status = ('Coincide con la referencia aritmética; aceptación externa pendiente.'
                                               if actual == tuple(money(value) for value in case[2:6])
                                               else 'Diferencia con la referencia: requiere revisión.')

    @api.constrains(*INPUTS, 'galapagos', 'special_condition', 'policy_id', 'company_id')
    def _check_review(self):
        for record in self:
            try:
                record._review_values()
            except (ValueError, TypeError, KeyError) as error:
                raise ValidationError(str(error)) from None

    def action_load_reference(self):
        manager(self.env)
        self.check_access('write')
        self.ensure_one()
        case = CASES[self.scenario]
        self.write(dict(BASE_INPUTS, **case[1]))
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'current'}
