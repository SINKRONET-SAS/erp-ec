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
    rebate_rate = fields.Float('Rebaja por gastos personales (tasa)')
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
    opening_balance_account_id = fields.Many2one('account.account','Contrapartida de saldos iniciales',help='Cuenta puente/suspenso contra la que se registran los saldos iniciales migrados (A4); no es una cuenta de gasto -- el gasto ya se reconoció en el sistema de origen.')
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
            line._sync_advance_deductions()
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
            existing=self.with_context(_erpec_payroll_token=_INTERNAL).create({'name':self.name+' / corrección','company_id':self.company_id.id,'policy_id':self.policy_id.id,'month':self.month,'version':self.version+1,'correction_of_id':self.id,'line_ids':[(0,0,{'employee_id':line.employee_id.id,'partner_id':line.partner_id.id,'analytic_id':line.analytic_id.id,**line._copy_inputs(),'benefit_line_ids':[(0,0,{'benefit_type_id':benefit.benefit_type_id.id,'amount':benefit.amount,'note':benefit.note}) for benefit in line.benefit_line_ids]}) for line in self.line_ids]})
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
    vacation_payout=fields.Float('Liquidación de vacaciones no gozadas',
        help='Caso 3 (DI25-03): pago en dinero de vacaciones acumuladas y no tomadas. Grava impuesto '
             'a la renta pero no IESS (catálogo RDEP vigente, campo sobSuelComRemu); distinto del '
             'devengo mensual de vacaciones tomadas, que ya está incluido en el salario.')
    # Caso 8 (DI25-03): ausencias, verificadas contra el Oficio PGE No. 10097 (17-02-2025) y el
    # art. 152 del Código del Trabajo (reforma 2023). Días de calendario, no laborables; el motor
    # los descuenta de los días normales del período (engine.calculate).
    sick_days=fields.Float('Días de enfermedad (con certificado IESS)',
        help='Los primeros 3 días los paga el empleador al 100 %, sin aporte a IESS (grava impuesto '
             'a la renta). Desde el día 4 el empleador no paga nada: el subsidio lo desembolsa el '
             'IESS directamente; repórtelo como novedad "Subsidiado" en la plataforma del IESS, no '
             'se calcula aquí.')
    maternity_days=fields.Float('Días de licencia de maternidad',
        help='El empleador paga el 25 % de todos los días de licencia; ese 25 % sí aporta a IESS '
             '(continuidad de aportación). El 75 % restante lo paga el IESS directamente.')
    paternity_days=fields.Float('Días de licencia de paternidad',
        help='El empleador paga el 100 % y aporta IESS normalmente (art. 152 Código del Trabajo): '
             'no cambia ningún cálculo frente a un día trabajado. Se registra solo para control de '
             'asistencia y para el expediente laboral.')
    unpaid_leave_days=fields.Float('Días de permiso no pagado',
        help='0 % de pago; no genera base imponible de impuesto a la renta ni aporte a IESS. '
             'Repórtelo como novedad al IESS para suspender la proporcionalidad de días de '
             'aportación del mes.')
    unexcused_absence_days=fields.Float('Días de falta injustificada',
        help='0 % de pago; reduce la base de aportación al IESS y la base gravable de impuesto a '
             'la renta, igual que un permiso no pagado. Se mantiene como campo separado por su '
             'distinto efecto disciplinario/laboral, no por un cálculo distinto.')
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
    # result_advances/result_loans: el total REAL descontado (lo escrito a mano en advances/loans
    # más lo resuelto automáticamente desde el libro de anticipos y préstamos, ver
    # _resolve_advance_entries) puede ser mayor que el campo advances/loans de la línea, que solo
    # guarda la parte manual. El rol de pago (A2, reports.xml) debe mostrar este total, no el
    # campo manual -- de lo contrario subestimaría el descuento real que ya afecta gross/net/cost.
    result_advances=fields.Float(compute='_compute_totals')
    result_loans=fields.Float(compute='_compute_totals')

    benefit_line_ids=fields.One2many('erpec.payroll.benefit.line','line_id','Beneficios del período')
    advance_deduction_ids=fields.One2many('erpec.payroll.advance.deduction','line_id','Cuotas de anticipos/préstamos aplicadas',readonly=True)

    _RESULT_FIELD_MAP = {
        'gross': 'gross', 'net': 'net', 'deductions': 'deductions', 'cost': 'cost',
        'salary': 'result_salary', 'overtime': 'result_overtime', 'personal_iess': 'result_personal_iess',
        'tax': 'result_tax', 'thirteenth': 'result_thirteenth', 'fourteenth': 'result_fourteenth',
        'vacation': 'result_vacation', 'reserve_iess': 'result_reserve_iess',
        'employer_iess': 'result_employer_iess', 'employer_other': 'result_employer_other',
        'advances': 'result_advances', 'loans': 'result_loans',
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
        keys=('start_date','wage','bonus','commission','non_taxable_income','vacation_payout','sick_days','maternity_days','paternity_days','unpaid_leave_days','unexcused_absence_days','advances','loans','other_deductions','personal_expenses','hours_50','hours_100','night_hours','monthly_thirteenth','monthly_fourteenth','reserve_paid')
        return {key:self[key] for key in keys}

    def _inputs(self):
        data=self._copy_inputs()
        data['start_date']=fields.Date.to_string(data['start_date'])
        _entries,totals=self._resolve_advance_entries()
        data['advances']=data.get('advances',0)+totals['advances']
        data['loans']=data.get('loans',0)+totals['loans']
        # Caso 3 (DI25-03): un beneficio propio que grava impuesto a la renta puede o no aportar a
        # IESS (campo iess_contributable, decisión de la empresa, art. 14 Ley de Seguridad Social).
        # El que sí aporta se suma como bonus (grava IESS e IR, igual que antes). El que no aporta
        # sigue el mismo tratamiento que vacation_payout: grava IR, no IESS, una sola vez al año.
        taxable_iess=sum(self.benefit_line_ids.filtered(
            lambda item:item.benefit_type_id.taxable and item.benefit_type_id.iess_contributable=='SI').mapped('amount'))
        taxable_no_iess=sum(self.benefit_line_ids.filtered(
            lambda item:item.benefit_type_id.taxable and item.benefit_type_id.iess_contributable=='NO').mapped('amount'))
        non_taxable=sum(self.benefit_line_ids.filtered(lambda item:not item.benefit_type_id.taxable).mapped('amount'))
        data['bonus']=data.get('bonus',0)+taxable_iess
        data['vacation_payout']=data.get('vacation_payout',0)+taxable_no_iess
        data['non_taxable_income']=data.get('non_taxable_income',0)+non_taxable
        return data

    def _resolve_advance_entries(self):
        """Calcula cuánto de cada anticipo/préstamo APROBADO del empleado corresponde
        descontar en este período (min(saldo, cuota mensual)), a partir de la fecha de inicio
        configurada en cada uno. Función pura (no escribe nada): se usa tanto para alimentar
        _inputs() como para persistir el detalle real en action_calculate() (ver
        _sync_advance_deductions), siempre con el mismo resultado mientras no cambien los datos
        en medio. Excluye la propia cuota que esta línea ya hubiera registrado antes, para que
        recalcular un período no se autodescuente dos veces."""
        self.ensure_one()
        if not self.employee_id or not self.period_id:
            return [],{'advances':0.0,'loans':0.0}
        candidates=self.env['erpec.payroll.advance'].search([
            ('employee_id','=',self.employee_id.id),('state','=','approved')])
        period_key=(self.period_id.year,self.period_id.month)
        entries=[]
        totals={'advances':0.0,'loans':0.0}
        for advance in candidates:
            if (advance.start_year,advance.start_month)>period_key:
                continue
            already=advance.deduction_ids.filtered(lambda item,line=self:item.line_id.id==line.id)
            balance_excluding_self=advance.balance+sum(already.mapped('amount'))
            amount=min(balance_excluding_self,advance.installment_amount)
            if amount<=0:
                continue
            entries.append((advance,amount))
            totals['advances' if advance.advance_type=='anticipo' else 'loans']+=amount
        return entries,totals

    def _sync_advance_deductions(self):
        self.ensure_one()
        token={'_erpec_payroll_token':_INTERNAL}
        self.env['erpec.payroll.advance.deduction'].with_context(**token).search(
            [('line_id','=',self.id)]).unlink()
        entries,_totals=self._resolve_advance_entries()
        for advance,amount in entries:
            self.env['erpec.payroll.advance.deduction'].with_context(**token).create(
                {'advance_id':advance.id,'line_id':self.id,'amount':amount})

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
    # copy=False: copiar o revertir un asiento (nota de crédito, duplicar factura) no debe heredar el vínculo con la nómina.
    erpec_payroll_id=fields.Many2one('erpec.payroll.period','Cierre de nómina',readonly=True,copy=False,ondelete='restrict')
    erpec_payroll_opening_balance_id=fields.Many2one('erpec.payroll.opening.balance','Carga de saldos iniciales',readonly=True,copy=False,ondelete='restrict')

    @api.model_create_multi
    def create(self,values_list):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and any(values.get('erpec_payroll_id') or values.get('erpec_payroll_opening_balance_id') for values in values_list):
            raise ValidationError('Genera el asiento desde el cierre de nómina o la carga de saldos iniciales.')
        return super().create(values_list)

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and (set(values)&{'erpec_payroll_id','erpec_payroll_opening_balance_id'} or ((self.erpec_payroll_id or self.erpec_payroll_opening_balance_id) and set(values)&{'state','line_ids','date','journal_id','company_id'})):
            raise ValidationError('Corrige la nómina o el saldo inicial desde su propio origen para conservar la trazabilidad.')
        return super().write(values)

    def unlink(self):
        if self.erpec_payroll_id or self.erpec_payroll_opening_balance_id:
            raise ValidationError('Conserva los asientos vinculados al cierre de nómina o al saldo inicial.')
        return super().unlink()


class PayrollMoveLine(models.Model):
    _inherit='account.move.line'

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and (self.move_id.erpec_payroll_id or self.move_id.erpec_payroll_opening_balance_id) and set(values)&{'debit','credit','balance','amount_currency','currency_id','account_id','partner_id','analytic_distribution','move_id'}:
            raise ValidationError('Corrige las partidas desde el cierre de nómina o el saldo inicial.')
        return super().write(values)

    @api.model_create_multi
    def create(self,values_list):
        moves=self.env['account.move'].browse([value['move_id'] for value in values_list if value.get('move_id')])
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and (moves.erpec_payroll_id or moves.erpec_payroll_opening_balance_id):
            raise ValidationError('No agregues partidas a un asiento de nómina o saldo inicial ya cerrado.')
        return super().create(values_list)

    def unlink(self):
        if self.move_id.erpec_payroll_id or self.move_id.erpec_payroll_opening_balance_id:
            raise ValidationError('Conserva las partidas del cierre de nómina o del saldo inicial.')
        return super().unlink()


class OpeningBalance(models.Model):
    _name='erpec.payroll.opening.balance'
    _description='Carga de saldos iniciales de nómina (migración desde otro sistema)'
    _inherit=['mail.thread']
    company_id=fields.Many2one('res.company','Empresa',required=True,default=lambda self:self.env.company)
    policy_id=fields.Many2one('erpec.payroll.policy','Versión y autoridad',required=True)
    employee_id=fields.Many2one('hr.employee','Empleado',required=True)
    partner_id=fields.Many2one('res.partner','Tercero para préstamos/anticipos',required=True)
    as_of_date=fields.Date('Fecha de corte',required=True)
    thirteenth_accrued=fields.Float('Décimo tercero acumulado no pagado')
    fourteenth_accrued=fields.Float('Décimo cuarto acumulado no pagado')
    vacation_accrued=fields.Float('Vacaciones acumuladas (valor)')
    reserve_accrued=fields.Float('Fondo de reserva acumulado no pagado')
    loan_balance=fields.Float('Saldo de préstamos pendiente')
    advance_balance=fields.Float('Saldo de anticipos pendiente')
    source_reference=fields.Text('Origen de los datos',required=True,help='De dónde provienen estos valores: sistema anterior, libros manuales, planilla del contador, etc.')
    source_hash=fields.Char('Huella del origen',readonly=True,copy=False)
    state=fields.Selection([('draft','Borrador'),('dry_run','Previsualizado'),('committed','Cargado'),('reverted','Revertido')],default='draft',readonly=True,string='Estado')
    preview_summary=fields.Text('Vista previa (dry-run)',readonly=True)
    move_id=fields.Many2one('account.move','Asiento',readonly=True,copy=False)
    reversal_id=fields.Many2one('account.move','Asiento inverso',readonly=True,copy=False)
    _sql_constraints=[('employee_once_per_policy','unique(policy_id,employee_id)','Este empleado ya tiene una carga de saldos iniciales en esta versión.')]

    def _lock(self):
        self.ensure_one();manager(self.env);self.check_access('write')
        self.env.cr.execute('UPDATE erpec_payroll_opening_balance SET write_date=NOW() WHERE id=%s',[self.id]);self.invalidate_recordset()

    @api.constrains('company_id','policy_id','employee_id','partner_id')
    def _check_company_links(self):
        for record in self:
            if record.policy_id.company_id!=record.company_id or record.employee_id.company_id!=record.company_id or (record.partner_id.company_id and record.partner_id.company_id!=record.company_id):
                raise ValidationError('Empleado, tercero y versión deben pertenecer a la misma empresa.')

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            for record in self.sorted('id'):
                record._lock()
            if any(record.state=='committed' for record in self):
                raise ValidationError('Una carga ya contabilizada es inmutable; revierte antes de corregir sus valores.')
        return super().write(values)

    def unlink(self):
        if any(record.state=='committed' for record in self):
            raise ValidationError('No se elimina una carga ya contabilizada; revierte primero.')
        return super().unlink()

    def _amounts(self):
        self.ensure_one()
        return [('thirteenth',self.thirteenth_accrued,'benefit'),('fourteenth',self.fourteenth_accrued,'benefit'),
                ('vacation',self.vacation_accrued,'benefit'),('reserve_iess',self.reserve_accrued,'benefit'),
                ('loans',self.loan_balance,'receivable'),('advances',self.advance_balance,'receivable')]

    def _compute_source_hash(self):
        self.ensure_one()
        payload=json.dumps({'employee_id':self.employee_id.id,'as_of_date':fields.Date.to_string(self.as_of_date),
            'thirteenth_accrued':self.thirteenth_accrued,'fourteenth_accrued':self.fourteenth_accrued,
            'vacation_accrued':self.vacation_accrued,'reserve_accrued':self.reserve_accrued,
            'loan_balance':self.loan_balance,'advance_balance':self.advance_balance,
            'source_reference':self.source_reference},sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _build_lines(self):
        self.ensure_one()
        policy=self.policy_id
        if policy.state!='active':
            raise ValidationError('La versión de parámetros debe estar activa.')
        if not policy.opening_balance_account_id:
            raise ValidationError('La versión no tiene configurada la cuenta de contrapartida de saldos iniciales.')
        labels=dict(CONCEPTS)
        lines=[]
        for concept,amount,kind in self._amounts():
            if not amount:
                continue
            mapping=policy.mapping_ids.filtered(lambda item,concept=concept:item.concept==concept)
            if not mapping or not mapping.credit_id:
                raise ValidationError('Falta el mapeo contable de '+labels.get(concept,concept)+' en la versión seleccionada.')
            account=mapping.credit_id
            if account.deprecated or self.company_id not in account.company_ids:
                raise ValidationError('El mapeo usa una cuenta ajena o deshabilitada.')
            name='Saldo inicial '+labels.get(concept,concept)+' · '+self.employee_id.name
            if kind=='benefit':
                lines.append({'name':name,'account_id':policy.opening_balance_account_id.id,'debit':amount,'credit':0,'partner_id':self.partner_id.id})
                lines.append({'name':name,'account_id':account.id,'debit':0,'credit':amount,'partner_id':self.partner_id.id})
            else:
                lines.append({'name':name,'account_id':account.id,'debit':amount,'credit':0,'partner_id':self.partner_id.id})
                lines.append({'name':name,'account_id':policy.opening_balance_account_id.id,'debit':0,'credit':amount,'partner_id':self.partner_id.id})
        if not lines:
            raise ValidationError('No hay ningún saldo distinto de cero para cargar.')
        return lines

    def action_dry_run(self):
        self.ensure_one();self._lock()
        if self.state=='committed':
            raise ValidationError('Ya está contabilizada; revierte antes de previsualizar de nuevo.')
        lines=self._build_lines()
        summary='\n'.join('%s: %s %.2f'%(line['name'],'debe' if line['debit'] else 'haber',line['debit'] or line['credit']) for line in lines)
        self.with_context(_erpec_payroll_token=_INTERNAL).write({'preview_summary':summary,'source_hash':self._compute_source_hash(),'state':'dry_run'})
        return True

    def action_commit(self):
        self.ensure_one();self._lock()
        if self.state!='dry_run':
            raise ValidationError('Genera primero la vista previa (dry-run) antes de contabilizar.')
        current_hash=self._compute_source_hash()
        if current_hash!=self.source_hash:
            raise ValidationError('Los datos cambiaron desde la vista previa; genera una nueva antes de contabilizar.')
        if self.search_count([('id','!=',self.id),('company_id','=',self.company_id.id),('source_hash','=',current_hash),('state','=','committed')]):
            raise ValidationError('Este origen ya se cargó antes; evita duplicar el saldo inicial.')
        move_lines=[(0,0,line) for line in self._build_lines()]
        move=self.env['account.move'].with_context(_erpec_payroll_token=_INTERNAL).create({'erpec_payroll_opening_balance_id':self.id,'move_type':'entry','company_id':self.company_id.id,'journal_id':self.policy_id.journal_id.id,'date':self.as_of_date,'ref':'Saldo inicial nómina · '+self.employee_id.name,'line_ids':move_lines})
        move.action_post()
        self.with_context(_erpec_payroll_token=_INTERNAL).write({'move_id':move.id,'state':'committed'})
        return True

    def action_revert(self):
        self.ensure_one();self._lock()
        if self.state!='committed':
            raise ValidationError('Solo se revierte una carga ya contabilizada.')
        if self.move_id.line_ids.filtered(lambda line:line.reconciled or line.matched_debit_ids or line.matched_credit_ids):
            raise ValidationError('Revisa y revierte los pagos conciliados antes de corregir el saldo inicial.')
        reverse=self.move_id.with_context(_erpec_payroll_token=_INTERNAL)._reverse_moves([{'date':fields.Date.today(),'ref':'Reversión saldo inicial · '+self.employee_id.name}],cancel=True)
        self.with_context(_erpec_payroll_token=_INTERNAL).write({'reversal_id':reverse.id,'state':'reverted'})
        return True


BENEFIT_CATEGORIES=[('bono','Bono'),('comision','Comisión'),('alimentacion','Alimentación'),
    ('transporte','Transporte'),('vivienda','Vivienda'),('seguro','Seguro privado'),('otro','Otro')]


class BenefitType(models.Model):
    _name='erpec.payroll.benefit.type'
    _description='Beneficio propio de nómina configurado por la empresa (no un parámetro legal)'
    _check_company_auto=True
    name=fields.Char('Nombre',required=True)
    company_id=fields.Many2one('res.company','Empresa',required=True,default=lambda self:self.env.company)
    category=fields.Selection(BENEFIT_CATEGORIES,'Categoría',required=True,default='otro')
    # taxable decide si el beneficio grava impuesto a la renta (se suma a `base`/`gross` según
    # corresponda) o no grava nada (igual que non_taxable_income). iess_contributable decide,
    # solo cuando taxable=True, si además grava IESS (entra a `base`, igual que bonus/commission)
    # o si grava renta pero no IESS (caso 3, DI25-03: mismo tratamiento que vacation_payout;
    # catálogo RDEP, campo sobSuelComRemu, "materia NO gravada de seguridad social"). Ya no hace
    # falta tratar "IESS sí/no" como indistinguible del impuesto a la renta: el motor separa
    # ambos desde que existe vacation_payout.
    taxable=fields.Boolean('Grava impuesto a la renta',default=True,
        help='Activado: el beneficio se suma a la base gravable de impuesto a la renta. '
             'Desactivado: se suma solo al ingreso bruto, sin gravar nada (igual que un ingreso no gravado). '
             'Este campo ya no decide el aporte a IESS por sí solo: ver "Aportable a IESS".')
    iess_contributable=fields.Selection([('SI','Sí'),('NO','No')],'Aportable a IESS',default='SI',required=True,
        help='Solo tiene efecto si el beneficio grava impuesto a la renta. Por defecto SÍ (aporta, '
             'igual que una bonificación). Elegir NO es una decisión de la empresa, no una verificación '
             'del sistema: se registra como referencia el art. 14 de la Ley de Seguridad Social (Ley 55, '
             'Registro Oficial Suplemento 465, 30-11-2001), que exonera de materia gravada IESS conceptos '
             'como alimentación, atención médica, seguros de vida/accidentes, ropa/herramientas de trabajo '
             'y beneficios de orden social sin privilegio (tope conjunto del 20 % de la retribución '
             'monetaria gravada) — no cualquier beneficio califica.')
    active=fields.Boolean('Activo',default=True)
    note=fields.Text('Descripción y justificación')
    _sql_constraints=[('name_unique','unique(company_id,name)','Ya existe un beneficio con ese nombre en esta empresa.')]

    def write(self, values):
        if 'taxable' in values or 'iess_contributable' in values:
            used = self.env['erpec.payroll.benefit.line'].search_count([
                ('benefit_type_id', 'in', self.ids), ('line_id.period_id.state', '!=', 'draft')])
            if used and any(
                    ('taxable' in values and item.taxable != values['taxable'])
                    or ('iess_contributable' in values and item.iess_contributable != values['iess_contributable'])
                    for item in self):
                raise ValidationError('El tratamiento de un beneficio calculado es inmutable; crea otra versión para períodos futuros.')
        return super().write(values)


class BenefitLine(models.Model):
    _name='erpec.payroll.benefit.line'
    _description='Beneficio asignado a un empleado en un período de nómina'
    _check_company_auto=True
    line_id=fields.Many2one('erpec.payroll.line','Línea de nómina',required=True,ondelete='cascade')
    company_id=fields.Many2one(related='line_id.company_id',store=True)
    benefit_type_id=fields.Many2one('erpec.payroll.benefit.type','Beneficio',required=True,check_company=True)
    amount=fields.Float('Monto',required=True)
    note=fields.Text('Nota')

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount<=0:
                raise ValidationError('El monto del beneficio debe ser positivo.')

    def _check_edit(self):
        for benefit in self:
            benefit.line_id.period_id._lock()
        if any(benefit.line_id.period_id.state!='draft' for benefit in self):
            raise ValidationError('Reabre el cálculo antes de cambiar los beneficios del período.')

    @api.model_create_multi
    def create(self,values_list):
        records=super().create(values_list);records._check_edit();return records

    def write(self,values):
        self._check_edit();result=super().write(values);self._check_edit();return result

    def unlink(self):
        self._check_edit();return super().unlink()


class Advance(models.Model):
    _name='erpec.payroll.advance'
    _description='Anticipo o préstamo de un empleado, con cuota fija hasta saldarse'
    _inherit=['mail.thread']
    _check_company_auto=True
    employee_id=fields.Many2one('hr.employee','Empleado',required=True,check_company=True)
    company_id=fields.Many2one('res.company','Empresa',required=True,default=lambda self:self.env.company)
    advance_type=fields.Selection([('anticipo','Anticipo'),('prestamo','Préstamo')],'Tipo',required=True,default='anticipo')
    amount_total=fields.Float('Monto total',required=True)
    installment_amount=fields.Float('Cuota mensual',required=True)
    # start_year/start_month: primer período de nómina en el que empieza a descontarse; no
    # necesariamente el período en que se entregó el dinero (p. ej. un anticipo entregado a
    # mitad de mes puede empezar a descontarse el mes siguiente).
    start_year=fields.Integer('Año de inicio de descuento',required=True)
    start_month=fields.Integer('Mes de inicio de descuento',required=True)
    state=fields.Selection([('draft','Borrador'),('approved','Aprobado'),('cancelled','Cancelado')],
        default='draft',required=True,readonly=True,string='Estado')
    reason=fields.Text('Motivo',required=True)
    approved_by=fields.Many2one('res.users','Aprobado por',readonly=True,copy=False)
    approved_at=fields.Datetime('Aprobado el',readonly=True,copy=False)
    deduction_ids=fields.One2many('erpec.payroll.advance.deduction','advance_id','Cuotas aplicadas',readonly=True)
    balance=fields.Float('Saldo pendiente',compute='_compute_balance',store=True)
    settled=fields.Boolean('Saldado',compute='_compute_balance',store=True)

    @api.depends('amount_total','deduction_ids.amount','deduction_ids.line_id.period_id.state')
    def _compute_balance(self):
        for advance in self:
            advance.balance=advance.amount_total-sum(advance.deduction_ids.filtered(lambda item:item.line_id.period_id.state!='reversed').mapped('amount'))
            advance.settled=advance.balance<=0

    @api.constrains('amount_total','installment_amount')
    def _check_amounts(self):
        for advance in self:
            if advance.amount_total<=0:
                raise ValidationError('El monto total debe ser positivo.')
            if not 0<advance.installment_amount<=advance.amount_total:
                raise ValidationError('La cuota mensual debe ser positiva y no mayor al monto total.')

    @api.constrains('start_month')
    def _check_start_month(self):
        for advance in self:
            if not 1<=advance.start_month<=12:
                raise ValidationError('El mes de inicio de descuento debe estar entre 1 y 12.')

    def _lock(self):
        self.ensure_one();manager(self.env);self.check_access('write')
        self.env.cr.execute('UPDATE erpec_payroll_advance SET write_date=NOW() WHERE id=%s',[self.id]);self.invalidate_recordset()

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            for advance in self.sorted('id'):
                advance._lock()
            if any(advance.state=='approved' for advance in self) and set(values)-{'reason'}:
                raise ValidationError('Un anticipo/préstamo aprobado es inmutable; cancélalo y crea uno nuevo si hubo un error.')
        return super().write(values)

    def unlink(self):
        if any(advance.state=='approved' for advance in self):
            raise ValidationError('No se elimina un anticipo/préstamo aprobado; cancélalo en su lugar.')
        return super().unlink()

    def action_approve(self):
        self.ensure_one();manager(self.env);self.check_access('write')
        if self.state!='draft':
            raise ValidationError('Solo se aprueba un anticipo/préstamo en borrador.')
        if not self.reason.strip():
            raise ValidationError('Registra el motivo antes de aprobar.')
        self.with_context(_erpec_payroll_token=_INTERNAL).write(
            {'state':'approved','approved_by':self.env.user.id,'approved_at':fields.Datetime.now()})
        return True

    def action_cancel(self):
        self.ensure_one();manager(self.env);self.check_access('write')
        if self.state=='cancelled':
            return True
        if self.deduction_ids:
            raise ValidationError('Ya tiene cuotas descontadas; no se cancela un anticipo/préstamo en curso.')
        self.with_context(_erpec_payroll_token=_INTERNAL).write({'state':'cancelled'})
        return True


class AdvanceDeduction(models.Model):
    _name='erpec.payroll.advance.deduction'
    _description='Cuota de un anticipo/préstamo aplicada a un período de nómina (solo generado por el cálculo)'
    advance_id=fields.Many2one('erpec.payroll.advance','Anticipo/préstamo',required=True,ondelete='cascade')
    line_id=fields.Many2one('erpec.payroll.line','Línea de nómina',required=True,ondelete='cascade')
    amount=fields.Float('Monto',required=True)
    period_state=fields.Selection(related='line_id.period_id.state',string='Estado del período',readonly=True)
    _sql_constraints=[('line_once','unique(advance_id,line_id)','Este período ya tiene una cuota registrada para este anticipo/préstamo.')]

    @api.model_create_multi
    def create(self,values_list):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            raise ValidationError('Las cuotas se generan solo al calcular el período; no se crean a mano.')
        return super().create(values_list)

    def write(self,values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            raise ValidationError('Las cuotas se generan solo al calcular el período; no se editan a mano.')
        return super().write(values)

    def unlink(self):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            raise ValidationError('Las cuotas se generan solo al calcular el período; no se eliminan a mano.')
        return super().unlink()
