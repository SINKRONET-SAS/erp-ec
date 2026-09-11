"""Períodos, parámetros versionados y asiento nativo; sin llamadas a SKNOMINA."""
import hashlib
import json
import uuid
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from .engine import calculate, validate_parameters

_INTERNAL = object()
CONCEPTS = [('gross','Ingresos brutos'), ('net','Neto por pagar'), ('personal_iess','IESS personal'), ('tax','Renta por pagar'), ('advances','Anticipos'), ('loans','Préstamos'), ('other_deductions','Otros descuentos'), ('employer_iess','IESS patronal'), ('employer_other','Contribución IECE/SECAP'), ('thirteenth','Décimo tercero acumulado'), ('fourteenth','Décimo cuarto acumulado'), ('vacation','Vacaciones'), ('reserve_iess','Fondo de reserva IESS')]


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
    parameters = fields.Text('Configuración técnica revisada', required=True)
    parameter_summary = fields.Text('Valores aplicados',compute='_compute_parameter_summary')

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
    journal_id = fields.Many2one('account.journal','Diario de nómina',required=True)
    _sql_constraints = [('version_unique','unique(company_id,name)','La versión ya existe en esta empresa.')]

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
        return super().write(values)

    @api.model_create_multi
    def create(self, values_list):
        if any(values.get('state','draft') != 'draft' for values in values_list):
            raise ValidationError('Activa los parámetros desde su acción de revisión.')
        return super().create(values_list)


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

    @api.depends('result')
    def _compute_totals(self):
        for line in self:
            result=json.loads(line.result or '{}')
            for key in ('gross','net','deductions','cost'):
                line[key]=result.get(key,0)

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
    _sql_constraints=[('employee_once','unique(period_id,employee_id)','El empleado ya pertenece a este período.')]

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
