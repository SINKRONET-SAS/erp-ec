"""Períodos, parámetros versionados y asiento nativo; sin llamadas a SKNOMINA."""
import hashlib
import json
import uuid
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from .engine import calculate, validate_parameters

_INTERNAL = object()
CONCEPTS = [('gross','Ingresos brutos'), ('net','Neto por pagar'), ('personal_iess','IESS personal'), ('tax','Renta por pagar'), ('advances','Anticipos'), ('loans','Préstamos'), ('other_deductions','Otros descuentos'), ('employer_iess','IESS patronal'), ('employer_other','Contribución IECE/SECAP'), ('thirteenth','Décimo tercero acumulado'), ('fourteenth','Décimo cuarto acumulado'), ('vacation','Vacaciones'), ('reserve_iess','Fondo de reserva IESS')]
# Campos tipados de erpec.payroll.policy que reemplazan la edición manual del JSON de
# `parameters` (adaptado del patrón de nuevo_nomina: legal_parameter_versions con columnas
# propias en vez de un blob de texto). `parameters` se conserva sin cambios como formato de
# intercambio para engine.calculate()/validate_parameters() y para compatibilidad con
# demo_parameters.py y las pruebas existentes -- ver Policy._apply_parameters_json/_sync_parameters_json.
STRUCTURED_PARAMETER_FIELDS = ['minimum_salary', 'monthly_hours', 'personal_rate', 'employer_rate',
    'employer_other_rate', 'reserve_rate', 'reserve_months', 'thirteenth_rate', 'fourteenth_rate',
    'vacation_rate', 'expense_limit', 'rebate_rate', 'overtime_50', 'overtime_100', 'night_rate']


def manager(env):
    if not env.su and not env.user.has_group('erpec_payroll.group_payroll_manager'):
        raise AccessError('Se requiere el permiso de responsable de nómina.')


class Policy(models.Model):
    _name = 'erpec.payroll.policy'
    _description = 'Versión de parámetros y autoridad de nómina'
    _inherit = ['mail.thread']
    name = fields.Char('Versión', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    year = fields.Integer('Año', required=True)
    authority = fields.Selection([('native','ERP EC nativo'), ('sknomina','SKNOMINA externo')], required=True, default='native', string='Autoridad del cálculo')
    authorization = fields.Text('Decisión y alcance de migración', required=True)
    parameters = fields.Text('Configuración técnica revisada')
    parameter_summary = fields.Text('Valores aplicados',compute='_compute_parameter_summary')

    minimum_salary = fields.Float('Salario básico unificado (SBU)')
    monthly_hours = fields.Float('Divisor salarial (horas/mes)')
    personal_rate = fields.Float('Aporte IESS personal')
    employer_rate = fields.Float('Aporte IESS patronal')
    employer_other_rate = fields.Float('Contribución IECE/SECAP')
    reserve_rate = fields.Float('Fondo de reserva (tasa)')
    reserve_months = fields.Integer('Meses de espera del fondo de reserva')
    thirteenth_rate = fields.Float('Décimo tercero (fracción anual)')
    fourteenth_rate = fields.Float('Décimo cuarto (fracción anual)')
    vacation_rate = fields.Float('Vacaciones (fracción anual)')
    expense_limit = fields.Float('Límite de gastos personales sin cargas (USD)')
    rebate_rate = fields.Float('Rebaja tercera edad/discapacidad')
    overtime_50 = fields.Float('Recargo hora suplementaria (50%)')
    overtime_100 = fields.Float('Recargo hora extraordinaria (100%)')
    night_rate = fields.Float('Recargo nocturno')
    tax_bracket_ids = fields.One2many('erpec.payroll.tax.bracket', 'policy_id', 'Tabla de impuesto a la renta')

    def _build_parameters_dict(self):
        self.ensure_one()
        brackets = [{'from': bracket.income_from, 'to': (None if bracket.open_ended else bracket.income_to),
                      'base': bracket.base_tax, 'rate': bracket.rate}
                    for bracket in self.tax_bracket_ids.sorted('sequence')]
        values = {key: self[key] for key in STRUCTURED_PARAMETER_FIELDS}
        values['tax_brackets'] = brackets
        return values

    def _sync_parameters_json(self):
        """Recalcula `parameters` (el JSON que consume engine.calculate()) a partir de los
        campos tipados. Se llama después de escribir cualquier campo tipado o la tabla de
        impuesto, nunca desde el propio write() de `parameters` (evita recursión)."""
        for policy in self:
            policy.with_context(_erpec_payroll_token=_INTERNAL).write(
                {'parameters': json.dumps(policy._build_parameters_dict(), sort_keys=True)})

    def _apply_parameters_json(self, json_text):
        """Dirección inversa: si `parameters` se escribe directamente (compatibilidad con
        demo_parameters.py y pruebas existentes que crean la versión solo con el JSON), puebla
        los campos tipados a partir de él para que el formulario los muestre correctamente."""
        for policy in self:
            try:
                params = json.loads(json_text or '{}')
            except (ValueError, TypeError):
                continue
            if not isinstance(params, dict):
                continue
            values = {key: params[key] for key in STRUCTURED_PARAMETER_FIELDS if key in params}
            if 'tax_brackets' in params:
                policy.tax_bracket_ids.with_context(_erpec_payroll_token=_INTERNAL).unlink()
                values['tax_bracket_ids'] = [(0, 0, {
                    'sequence': index, 'income_from': bracket.get('from', 0),
                    'income_to': bracket.get('to') or 0, 'open_ended': bracket.get('to') is None,
                    'base_tax': bracket.get('base', 0), 'rate': bracket.get('rate', 0),
                }) for index, bracket in enumerate(params.get('tax_brackets', []))]
            if values:
                policy.with_context(_erpec_payroll_token=_INTERNAL).write(values)

    @api.depends('parameters')
    def _compute_parameter_summary(self):
        for policy in self:
            try:
                params=json.loads(policy.parameters or '{}')
                policy.parameter_summary='\n'.join([f"Salario básico: USD {params.get('minimum_salary',0):.2f}",f"IESS personal: {params.get('personal_rate',0)*100:.2f}%",f"IESS patronal: {params.get('employer_rate',0)*100:.2f}%",f"Fondo de reserva: {params.get('reserve_rate',0)*100:.2f}%",f"Contribución IECE/SECAP: {params.get('employer_other_rate',0)*100:.2f}%",f"Divisor salarial: {params.get('monthly_hours',0)}",f"Límite gastos personales sin cargas: USD {params.get('expense_limit',0):.2f}",f"Rebaja: {params.get('rebate_rate',0)*100:.0f}%"]+[f"Renta anual desde {item['from']} hasta {item['to'] if item['to'] is not None else 'en adelante'}: base {item['base']}, exceso {item['rate']*100:.0f}%" for item in params.get('tax_brackets',[])])
            except (ValueError,TypeError,KeyError):
                policy.parameter_summary='Configuración incompleta; revisar antes de activar.'

    source_reference = fields.Text('Fuentes y revisión normativa', required=True)
    synthetic = fields.Boolean('Empleados y operaciones de demostración', default=True)
    state = fields.Selection([('draft','En revisión'), ('active','Versión activa')], default='draft', readonly=True, string='Estado')
    mapping_ids = fields.One2many('erpec.payroll.mapping','policy_id','Mapeo contable')
    # No required=True aquí a propósito: la siembra automática de parámetros nacionales
    # (hooks.post_init_hook) crea la versión antes de que exista necesariamente un diario
    # de nómina, para no depender del orden de carga del plan de cuentas de la empresa (ver
    # hooks.py). action_activate() ya exige un diario válido de la misma empresa antes de
    # activar, así que la falta de diario en un borrador recién sembrado no permite calcular
    # nómina real -- solo evita repetir la captura de los parámetros legales en cada cliente.
    journal_id = fields.Many2one('account.journal','Diario de nómina')
    _sql_constraints = [('version_unique','unique(company_id,name)','La versión ya existe en esta empresa.')]

    def action_reload_from_json(self):
        """Rellena los campos tipados a partir del `parameters` ya guardado. Necesario para
        versiones creadas antes de que existieran los campos tipados (una actualización de
        módulo agrega columnas nuevas con su valor por defecto en cero; no reescribe registros
        existentes) -- bug real encontrado por el titular en una versión activa del 11-09-2026
        que mostraba ceros en "Parámetros legales" pese a tener un JSON correcto. Funciona
        también sobre una versión ya activa (usa el token interno dentro de
        _apply_parameters_json), porque no cambia ningún valor: solo hace visibles como campos
        los mismos datos que ya estaban en el JSON."""
        self.check_access('write')
        for policy in self:
            policy._apply_parameters_json(policy.parameters)
        return True

    def action_activate(self):
        self.ensure_one(); manager(self.env);self.check_access('write')
        self.env.cr.execute('UPDATE erpec_payroll_policy SET write_date=NOW() WHERE id=%s',[self.id]);self.invalidate_recordset()
        if not self.synthetic:
            raise ValidationError('La migración productiva está pendiente de equivalencia integral y revisión laboral. Utiliza la demo sintética mientras se completan los casos pendientes.')
        try:
            params = json.loads(self.parameters)
        except (ValueError, TypeError):
            raise ValidationError('Los parámetros deben ser un objeto JSON válido.') from None
        try:
            validate_parameters(params)
        except (ValueError, TypeError, KeyError) as error:
            raise ValidationError(str(error)) from None
        self.env.cr.execute('UPDATE res_company SET write_date=NOW() WHERE id=%s', [self.company_id.id])
        if not isinstance(params, dict) or not self.authorization.strip() or self.journal_id.company_id != self.company_id:
            raise ValidationError('Revisa parámetros, autorización y diario de la misma empresa.')
        if self.search_count([('company_id','=',self.company_id.id),('year','=',self.year),('state','=','active'),('id','!=',self.id)]):
            raise ValidationError('Ya existe una autoridad activa para esta empresa y año. Planifica un cambio de versión sin solapar cálculos.')
        self.with_context(_erpec_payroll_token=_INTERNAL).write({'state':'active'})
        return True

    def write(self, values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and (any(policy.state == 'active' for policy in self) or 'state' in values):
            raise ValidationError('La versión activa es inmutable; prepara una nueva versión para la migración.')
        has_structured = bool(set(values) & (set(STRUCTURED_PARAMETER_FIELDS) | {'tax_bracket_ids'}))
        has_json = 'parameters' in values
        result = super().write(values)
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            if has_structured:
                self._sync_parameters_json()
            elif has_json:
                self._apply_parameters_json(values['parameters'])
        return result

    @api.model_create_multi
    def create(self, values_list):
        if any(values.get('state','draft') != 'draft' for values in values_list):
            raise ValidationError('Activa los parámetros desde su acción de revisión.')
        records = super().create(values_list)
        for record, values in zip(records, values_list):
            has_structured = bool(set(values) & (set(STRUCTURED_PARAMETER_FIELDS) | {'tax_bracket_ids'}))
            has_json = 'parameters' in values
            if has_structured:
                record._sync_parameters_json()
            elif has_json:
                record._apply_parameters_json(values['parameters'])
        return records


class TaxBracket(models.Model):
    _name = 'erpec.payroll.tax.bracket'
    _description = 'Tramo de la tabla de impuesto a la renta de una versión de nómina'
    _order = 'policy_id, sequence'
    policy_id = fields.Many2one('erpec.payroll.policy', required=True, ondelete='cascade')
    sequence = fields.Integer('Orden', required=True, default=0)
    income_from = fields.Float('Desde (base anual)', required=True)
    income_to = fields.Float('Hasta (base anual)')
    open_ended = fields.Boolean('Último tramo (sin límite superior)')
    base_tax = fields.Float('Impuesto de la fracción básica', required=True)
    rate = fields.Float('Porcentaje sobre el exceso', required=True)

    def _check_edit(self):
        if any(bracket.policy_id.state != 'draft' for bracket in self):
            raise ValidationError('La tabla de renta de una versión activa no puede modificarse.')

    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list)
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            records._check_edit()
            records.policy_id._sync_parameters_json()
        return records

    def write(self, values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            self._check_edit()
        result = super().write(values)
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            self.policy_id._sync_parameters_json()
        return result

    def unlink(self):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            self._check_edit()
        policies = self.policy_id
        result = super().unlink()
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            policies._sync_parameters_json()
        return result


class Mapping(models.Model):
    _name = 'erpec.payroll.mapping'
    _description = 'Mapeo contable versionado de nómina'
    policy_id = fields.Many2one('erpec.payroll.policy',required=True,ondelete='cascade')
    company_id = fields.Many2one(related='policy_id.company_id',store=True)
    concept = fields.Selection(CONCEPTS,required=True,string='Concepto')
    debit_id = fields.Many2one('account.account','Cuenta de débito')
    credit_id = fields.Many2one('account.account','Cuenta de crédito')
    _sql_constraints = [('concept_unique','unique(policy_id,concept)','El concepto ya tiene un mapeo en esta versión.')]

    def _check_edit(self):
        for policy in self.policy_id.sorted('id'):
            policy.check_access('write')
            self.env.cr.execute('UPDATE erpec_payroll_policy SET write_date=NOW() WHERE id=%s',[policy.id]);policy.invalidate_recordset()
        if any(record.policy_id.state != 'draft' for record in self):
            raise ValidationError('El mapeo de una versión activa no puede modificarse.')

    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list); records._check_edit(); return records

    def write(self, values):
        self._check_edit(); result=super().write(values); self._check_edit(); return result

    def unlink(self):
        self._check_edit(); return super().unlink()


class Period(models.Model):
    _name = 'erpec.payroll.period'
    _description = 'Período de nómina nativa'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char('Referencia del cierre', required=True, default=lambda self: uuid.uuid4().hex)
    company_id = fields.Many2one('res.company',required=True,default=lambda self:self.env.company)
    policy_id = fields.Many2one('erpec.payroll.policy','Versión y autoridad',required=True)
    month = fields.Integer('Mes',required=True)
    year = fields.Integer(related='policy_id.year',store=True)
    version = fields.Integer('Versión del cierre',required=True,default=1)
    state = fields.Selection([('draft','Novedades'),('calculated','Calculado'),('closed','Cierre aprobado'),('posted','Contabilizado'),('reversed','Revertido')],default='draft',readonly=True,string='Estado')
    line_ids = fields.One2many('erpec.payroll.line','period_id','Empleados y novedades')
    move_id = fields.Many2one('account.move','Asiento',readonly=True,copy=False)
    reversal_id = fields.Many2one('account.move','Asiento inverso',readonly=True,copy=False)
    correction_of_id = fields.Many2one('erpec.payroll.period','Corrección de',readonly=True,copy=False)
    last_error = fields.Text('Último error',readonly=True)
    next_action = fields.Text('Alcance',default='Empleados ficticios con parámetros reales Ecuador 2026 (privado general continental, sin cargas familiares ni exenciones especiales). Proyección mensual; no genera formularios ni pagos oficiales. La API de SKNOMINA existe y permanece disponible. La activación real del motor nativo requiere equivalencia integral, validación normativa y corte de autoridad por empresa.',readonly=True)
    _sql_constraints = [('period_version_unique','unique(company_id,year,month,version)','Este período y versión ya existen.')]

    def _lock(self):
        self.ensure_one(); manager(self.env); self.check_access('write')
        self.env.cr.execute('UPDATE erpec_payroll_period SET write_date=NOW() WHERE id=%s RETURNING id',[self.id]);self.invalidate_recordset()

    def _update(self, values):
        return self.with_context(_erpec_payroll_token=_INTERNAL).write(values)

    @api.model_create_multi
    def create(self, values_list):
        if any(set(values)&{'state','move_id','reversal_id','correction_of_id'} for values in values_list) and self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            raise ValidationError('Los resultados se generan mediante acciones de nómina.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            for period in self.sorted('id'):
                period._lock()
            if set(values)&{'state','move_id','reversal_id','correction_of_id','last_error'} or any(period.state!='draft' for period in self):
                raise ValidationError('Reabre las novedades o crea una corrección; no se sobrescriben cierres.')
        return super().write(values)

    @api.constrains('company_id','policy_id','month','version')
    def _check_period(self):
        for period in self:
            if period.company_id!=period.policy_id.company_id or not 1<=period.month<=12 or period.version<1:
                raise ValidationError('Revisa empresa, mes y versión del período.')

    def action_calculate(self):
        self._lock()
        if self.state not in ('draft','calculated'):
            raise ValidationError('El cierre no se recalcula; utiliza una corrección.')
        policy=self.policy_id
        if policy.state!='active' or policy.authority!='native' or policy.company_id!=self.company_id:
            raise ValidationError('La versión debe estar activa y asignar el cálculo nativo a esta empresa.')
        if not policy.synthetic or self.company_id.vat or 'DEMO' not in self.company_id.name or not self.line_ids or not 1<=self.month<=12:
            raise ValidationError('Este incremento admite únicamente una empresa DEMO sin RUC, un mes válido y empleados sintéticos.')
        self.line_ids._check_company_links()
        params=json.loads(policy.parameters)
        for line in self.line_ids:
            if line.employee_id.company_id!=self.company_id:
                raise ValidationError('El empleado pertenece a otra empresa.')
            try:
                data=line._inputs()
                result=calculate(data,params,self.year,self.month)
            except (ValueError,TypeError,KeyError) as error:
                raise ValidationError('Revisa las novedades del empleado: '+str(error)) from None
            line.with_context(_erpec_payroll_token=_INTERNAL).write({'result':json.dumps(result,sort_keys=True),'input_hash':hashlib.sha256((json.dumps(data,sort_keys=True)+policy.parameters).encode()).hexdigest()})
        self._update({'state':'calculated','last_error':False})
        return True

    def action_reopen(self):
        self._lock()
        if self.state!='calculated':
            raise ValidationError('Solo se reabre un cálculo que aún no está aprobado.')
        self._update({'state':'draft'})
        return True

    def action_close(self):
        self._lock()
        if self.state!='calculated' or any(not line.approved for line in self.line_ids):
            raise ValidationError('Calcula y aprueba las novedades de todos los empleados antes del cierre.')
        self._update({'state':'closed'})
        for line in self.line_ids:
            line._send_payslip()
        return True

    def action_post(self):
        self._lock()
        if self.move_id:
            return {'type':'ir.actions.act_window','res_model':'account.move','res_id':self.move_id.id,'view_mode':'form'}
        if self.state!='closed':
            raise ValidationError('Aprueba el cierre del período antes de contabilizar.')
        lines=[]
        for payroll in self.line_ids:
            result=json.loads(payroll.result)
            for concept,label in CONCEPTS:
                amount=result[concept]
                if not amount:
                    continue
                mapping=self.policy_id.mapping_ids.filtered(lambda item:item.concept==concept)
                if not mapping or (concept=='gross' and not mapping.debit_id) or (concept in ('net','personal_iess','tax','advances','loans','other_deductions') and not mapping.credit_id) or (concept not in ('gross','net','personal_iess','tax','advances','loans','other_deductions') and (not mapping.debit_id or not mapping.credit_id)):
                    raise ValidationError('Falta el mapeo contable de '+label)
                for account,side in [(mapping.debit_id,'debit'),(mapping.credit_id,'credit')]:
                    if account:
                        if account.deprecated or self.company_id not in account.company_ids:
                            raise ValidationError('El mapeo usa una cuenta ajena o deshabilitada.')
                        values={'name':label+' · '+payroll.employee_id.name,'account_id':account.id,side:amount,'partner_id':payroll.partner_id.id}
                        if side=='debit' and payroll.analytic_id:
                            values['analytic_distribution']={str(payroll.analytic_id.id):100}
                        lines.append((0,0,values))
        if abs(sum(item[2].get('debit',0)-item[2].get('credit',0) for item in lines))>self.company_id.currency_id.rounding/2:
            raise ValidationError('El mapeo produce un asiento desequilibrado; corrígelo antes de publicar.')
        move=self.env['account.move'].with_context(_erpec_payroll_token=_INTERNAL).create({'erpec_payroll_id':self.id,'move_type':'entry','company_id':self.company_id.id,'journal_id':self.policy_id.journal_id.id,'date':fields.Date.today(),'ref':'Nómina '+self.name,'line_ids':lines})
        move.action_post()
        self._update({'move_id':move.id,'state':'posted'})
        return {'type':'ir.actions.act_window','res_model':'account.move','res_id':move.id,'view_mode':'form'}

    def action_reverse(self):
        self._lock()
        if self.reversal_id:
            return True
        if self.state!='posted':
            raise ValidationError('Solo se revierte un cierre contabilizado.')
        if self.move_id.line_ids.filtered(lambda line:line.reconciled or line.matched_debit_ids or line.matched_credit_ids):
            raise ValidationError('Revisa y revierte los pagos conciliados antes de corregir la nómina.')
        reverse=self.move_id.with_context(_erpec_payroll_token=_INTERNAL)._reverse_moves([{'date':fields.Date.today(),'ref':'Reversión nómina '+self.name}],cancel=True)
        self._update({'reversal_id':reverse.id,'state':'reversed'})
        return True

    def action_correct(self):
        self._lock()
        if self.state!='reversed':
            raise ValidationError('Revierte el asiento antes de generar la corrección.')
        existing=self.search([('correction_of_id','=',self.id)],limit=1)
        if not existing:
            existing=self.with_context(_erpec_payroll_token=_INTERNAL).create({'name':self.name+' / corrección','company_id':self.company_id.id,'policy_id':self.policy_id.id,'month':self.month,'version':self.version+1,'correction_of_id':self.id,'line_ids':[(0,0,{'employee_id':line.employee_id.id,'partner_id':line.partner_id.id,'analytic_id':line.analytic_id.id,**line._copy_inputs()}) for line in self.line_ids]})
        return {'type':'ir.actions.act_window','res_model':self._name,'res_id':existing.id,'view_mode':'form'}


class Line(models.Model):
    _name='erpec.payroll.line'
    _description='Empleado y novedades de un período'
    period_id=fields.Many2one('erpec.payroll.period',required=True,ondelete='cascade')
    company_id=fields.Many2one(related='period_id.company_id',store=True)
    employee_id=fields.Many2one('hr.employee','Empleado sintético',required=True)
    partner_id=fields.Many2one('res.partner','Tercero para pago',required=True)
    analytic_id=fields.Many2one('account.analytic.account','Centro de costo')
    start_date=fields.Date('Ingreso',required=True)
    wage=fields.Float('Salario mensual',required=True)
    bonus=fields.Float('Bonificación')
    commission=fields.Float('Comisión')
    non_taxable_income=fields.Float('Ingreso no gravado')
    advances=fields.Float('Anticipos')
    loans=fields.Float('Préstamos')
    other_deductions=fields.Float('Otros descuentos')
    personal_expenses=fields.Float('Proyección de gastos personales')
    hours_50=fields.Float('Horas suplementarias')
    hours_100=fields.Float('Horas extraordinarias')
    night_hours=fields.Float('Horas nocturnas incluidas en el salario')
    monthly_thirteenth=fields.Boolean('Mensualizar décimo tercero')
    monthly_fourteenth=fields.Boolean('Mensualizar décimo cuarto')
    reserve_paid=fields.Boolean('Pagar reserva directamente')
    gross=fields.Float('Ingresos',compute='_compute_totals')
    net=fields.Float('Neto a recibir',compute='_compute_totals')
    deductions=fields.Float('Descuentos',compute='_compute_totals')
    cost=fields.Float('Costo de empresa',compute='_compute_totals')
    # Prefijo result_ para no chocar con los campos de novedades del mismo nombre (p. ej.
    # `advances`/`loans`/`other_deductions` ya existen como entrada; su valor en el resultado es
    # idéntico, así que el reporte de rol de pago (A2) los lee directamente de esos campos).
    result_salary=fields.Float(compute='_compute_totals')
    result_overtime=fields.Float(compute='_compute_totals')
    result_personal_iess=fields.Float(compute='_compute_totals')
    result_tax=fields.Float(compute='_compute_totals')
    result_thirteenth=fields.Float(compute='_compute_totals')
    result_fourteenth=fields.Float(compute='_compute_totals')
    result_vacation=fields.Float(compute='_compute_totals')
    result_reserve_iess=fields.Float(compute='_compute_totals')
    result_employer_iess=fields.Float(compute='_compute_totals')
    result_employer_other=fields.Float(compute='_compute_totals')

    _RESULT_FIELD_MAP = {
        'gross': 'gross', 'net': 'net', 'deductions': 'deductions', 'cost': 'cost',
        'salary': 'result_salary', 'overtime': 'result_overtime', 'personal_iess': 'result_personal_iess',
        'tax': 'result_tax', 'thirteenth': 'result_thirteenth', 'fourteenth': 'result_fourteenth',
        'vacation': 'result_vacation', 'reserve_iess': 'result_reserve_iess',
        'employer_iess': 'result_employer_iess', 'employer_other': 'result_employer_other',
    }

    @api.depends('result')
    def _compute_totals(self):
        for line in self:
            result=json.loads(line.result or '{}')
            for result_key,field_name in line._RESULT_FIELD_MAP.items():
                line[field_name]=result.get(result_key,0)

    @api.constrains('period_id','employee_id','partner_id','analytic_id')
    def _check_company_links(self):
        for line in self:
            if line.employee_id.company_id!=line.company_id or (line.partner_id.company_id and line.partner_id.company_id!=line.company_id) or (line.analytic_id.company_id and line.analytic_id.company_id!=line.company_id):
                raise ValidationError('Empleado, tercero y centro de costo deben pertenecer a la empresa del cierre.')

    def _copy_inputs(self):
        self.ensure_one()
        keys=('start_date','wage','bonus','commission','non_taxable_income','advances','loans','other_deductions','personal_expenses','hours_50','hours_100','night_hours','monthly_thirteenth','monthly_fourteenth','reserve_paid')
        return {key:self[key] for key in keys}

    def _inputs(self):
        data=self._copy_inputs()
        data['start_date']=fields.Date.to_string(data['start_date'])
        return data

    approved=fields.Boolean('Novedades aprobadas')
    result=fields.Text('Desglose calculado',readonly=True)
    input_hash=fields.Char('Huella de cálculo',readonly=True)
    payslip_mail_id=fields.Many2one('mail.mail','Correo del rol de pago',readonly=True,copy=False)
    payslip_sent_date=fields.Datetime('Rol de pago enviado el',readonly=True,copy=False)
    payslip_send_error=fields.Text('Error de envío del rol de pago',readonly=True,copy=False)
    _sql_constraints=[('employee_once','unique(period_id,employee_id)','El empleado ya pertenece a este período.')]

    def _send_payslip(self):
        """Encola (no envía de inmediato) el correo del rol de pago con el PDF adjunto vía la
        plantilla `erpec_payroll.payslip_email_template` (report_template_ids la adjunta sola).
        `force_send=False` dispara únicamente la cola de correo estándar de Odoo -- sin un
        servidor SMTP saliente real configurado por el titular, el correo queda en 'outgoing' y
        nunca se transmite; no se llama `.send()` de forma explícita en ningún punto de este
        módulo. Un empleado sin correo de trabajo, o un fallo de plantilla, no bloquea el envío
        de los demás -- se registra el motivo en `payslip_send_error` para revisión manual."""
        self.ensure_one()
        template=self.env.ref('erpec_payroll.payslip_email_template',raise_if_not_found=False)
        if not template:
            return
        if not self.employee_id.work_email:
            self.with_context(_erpec_payroll_token=_INTERNAL).write({'payslip_send_error':'El empleado no tiene correo electrónico de trabajo configurado.'})
            return
        try:
            mail_id=template.send_mail(self.id,force_send=False)
        except Exception as error:  # noqa: BLE001 - el render/envio de correo puede fallar de muchas formas; no debe bloquear el cierre de los demas empleados
            self.with_context(_erpec_payroll_token=_INTERNAL).write({'payslip_send_error':str(error)})
            return
        self.with_context(_erpec_payroll_token=_INTERNAL).write({'payslip_mail_id':mail_id,'payslip_sent_date':fields.Datetime.now(),'payslip_send_error':False})

    def action_resend_payslip(self):
        self.ensure_one();self.check_access('write')
        self._send_payslip()
        return True

    def _check_edit(self):
        for period in self.period_id.sorted('id'):
            period._lock()
        if any(line.period_id.state!='draft' for line in self):
            raise ValidationError('Reabre el cálculo antes de cambiar novedades o aprobaciones.')

    @api.model_create_multi
    def create(self,values_list):
        if any(set(values)&{'result','input_hash'} for values in values_list):
            raise ValidationError('El resultado solo lo genera el cálculo nativo.')
        for period in self.env['erpec.payroll.period'].browse(sorted({values['period_id'] for values in values_list})):
            period._lock()
        records=super().create(values_list);records._check_edit();return records

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            self._check_edit()
            if set(values)&{'result','input_hash'}:
                raise ValidationError('El resultado solo lo genera el cálculo nativo.')
        result=super().write(values)
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            self._check_edit()
        return result

    def unlink(self):
        self._check_edit();return super().unlink()


class PayrollMove(models.Model):
    _inherit='account.move'
    erpec_payroll_id=fields.Many2one('erpec.payroll.period','Cierre de nómina',readonly=True,copy=True,ondelete='restrict')

    @api.model_create_multi
    def create(self,values_list):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and any(values.get('erpec_payroll_id') for values in values_list):
            raise ValidationError('Genera el asiento desde el cierre de nómina.')
        return super().create(values_list)

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and ('erpec_payroll_id' in values or (self.erpec_payroll_id and set(values)&{'state','line_ids','date','journal_id','company_id'})):
            raise ValidationError('Corrige la nómina desde su cierre para conservar la trazabilidad.')
        return super().write(values)

    def unlink(self):
        if self.erpec_payroll_id:
            raise ValidationError('Conserva los asientos vinculados al cierre de nómina.')
        return super().unlink()


class PayrollMoveLine(models.Model):
    _inherit='account.move.line'

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and self.move_id.erpec_payroll_id and set(values)&{'debit','credit','balance','amount_currency','currency_id','account_id','partner_id','analytic_distribution','move_id'}:
            raise ValidationError('Corrige las partidas desde el cierre de nómina.')
        return super().write(values)

    @api.model_create_multi
    def create(self,values_list):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and self.env['account.move'].browse([value['move_id'] for value in values_list if value.get('move_id')]).erpec_payroll_id:
            raise ValidationError('No agregues partidas a un asiento de nómina cerrado.')
        return super().create(values_list)

    def unlink(self):
        if self.move_id.erpec_payroll_id:
            raise ValidationError('Conserva las partidas del cierre de nómina.')
        return super().unlink()
