"""Proyección de derechos del contrato en la base cliente; solo el trabajador la sincroniza."""
import os
import logging
from odoo import api, fields, models, SUPERUSER_ID
from odoo.exceptions import AccessError, ValidationError
from .capabilities import CAPABILITIES, missing_requirements

_INTERNAL = object()
_logger = logging.getLogger(__name__)
PREFIXES = [('erpec.payroll.disbursement','treasury'),('erpec.payroll.bonus.settlement','treasury'),('erpec.purchase.withholding','fiscal'),('erpec.reimbursement','fiscal'),('erpec.route','routes'),('erpec.asset','assets'),('erpec.payroll','payroll'),('erpec.treasury','treasury'),
            ('erpec.bank','treasury'),('erpec.fiscal','fiscal'),('erpec.withholding','fiscal'),
            ('erpec.ats','fiscal'),('erpec.field','routes'),('sale.','sales'),('purchase.','purchases'),
            ('stock.','inventory'),('mrp.','manufacturing')]
PROTECTED = {'ir.module.module','ir.actions.server','ir.cron','ir.model','ir.model.fields'}


def capability(model):
    return next((code for prefix,code in PREFIXES if model.startswith(prefix)),None)


def entitlement(env):
    if not env.registry.ready or os.environ.get('ERPEC_CM28_INSTALLATION') == '1' or env.context.get('_erpec_entitlement_token') is _INTERNAL:
        return env['erpec.tenant.entitlement']
    return env['erpec.tenant.entitlement'].sudo().search([],limit=1)


def denied(record, operation):
    code=capability(record._name)
    if not code and record._name not in PROTECTED:
        return False
    rights=entitlement(record.env)
    if not rights:
        return False
    if operation!='read' and record._name in PROTECTED:
        return 'La configuración técnica la administra el operador del servicio.'
    if code:
        available=rights.ever_capabilities if operation=='read' else rights.snapshot.get('capabilities',[])
        if code not in (available or []):
            return 'Este módulo no está contratado para esta operación. Puedes revisar tu plan en el portal del cliente.'
    return False


class Entitlement(models.Model):
    _name='erpec.tenant.entitlement'
    _description='Derechos contratados de la instancia'
    name=fields.Char(default='Contrato vigente',required=True)
    singleton=fields.Integer(default=1,required=True)
    customer_reference=fields.Char('Cliente',required=True,readonly=True)
    revision=fields.Char('Revisión aplicada',required=True,readonly=True)
    snapshot=fields.Json('Condiciones',required=True,readonly=True)
    ever_capabilities=fields.Json('Historial de capacidades',readonly=True)
    ends_on=fields.Date('Vigente hasta',readonly=True)
    active_users=fields.Integer('Usuarios internos activos',compute='_compute_usage')
    max_users=fields.Integer('Usuarios contratados',compute='_compute_usage')
    module_names=fields.Char('Módulos activos',compute='_compute_terms')
    historical_module_names=fields.Char('Historial en consulta',compute='_compute_terms')
    period_label=fields.Char('Periodo contratado',compute='_compute_terms')
    price_label=fields.Char('Total del periodo',compute='_compute_terms')

    @api.depends('snapshot','ever_capabilities')
    def _compute_terms(self):
        for record in self:
            current=set(record.snapshot.get('capabilities',[]))
            historical=set(record.ever_capabilities or [])-current
            record.module_names=', '.join(CAPABILITIES[key][0] for key in sorted(current)) or 'Contabilidad general'
            record.historical_module_names=', '.join(CAPABILITIES[key][0] for key in sorted(historical)) or False
            record.period_label='Anual' if record.snapshot.get('period')=='annual' else 'Mensual'
            record.price_label='USD %.2f' % record.snapshot.get('total',0)

    _sql_constraints=[('singleton_unique','unique(singleton)','Solo existe una proyección de derechos por instancia.'),('singleton_one','check(singleton=1)','Identificador inválido.')]

    @api.depends('snapshot')
    def _compute_usage(self):
        for record in self:
            record.active_users=self.env['res.users'].sudo().search_count([('active','=',True),('share','=',False),('id','!=',SUPERUSER_ID)])
            record.max_users=record.snapshot.get('users',0)

    @api.model_create_multi
    def create(self,values_list):
        if self.env.context.get('_erpec_entitlement_token') is not _INTERNAL:
            raise AccessError('Solo el trabajador autorizado registra derechos.')
        return super().create(values_list)

    def write(self,values):
        if self.env.context.get('_erpec_entitlement_token') is not _INTERNAL:
            raise AccessError('Los derechos se sincronizan desde el contrato, no se editan en la instancia.')
        return super().write(values)

    def unlink(self):
        raise AccessError('Los derechos y su historial se conservan.')

    @api.model
    def _sync(self,customer,revision,snapshot,ends_on):
        if self.env.uid!=SUPERUSER_ID:
            raise AccessError('La sincronización requiere el trabajador local.')
        if not isinstance(snapshot,dict) or type(snapshot.get('users')) is not int or snapshot['users']<1 or set(snapshot.get('capabilities',[]))-set(CAPABILITIES):
            raise ValidationError('Condiciones de instancia inválidas.')
        if missing_requirements(snapshot['capabilities']):
            raise ValidationError('Fabricación requiere contratar Inventario.')
        self.env.cr.execute('SELECT pg_advisory_xact_lock(280028)')
        record=self.sudo().search([],limit=1)
        if record and record.customer_reference!=customer:
            raise ValidationError('La base pertenece a otro cliente.')
        used=self.env['res.users'].sudo().search_count([('active','=',True),('share','=',False),('id','!=',SUPERUSER_ID)])
        companies=self.env['res.company'].sudo().search_count([])
        if used>snapshot['users'] or companies>snapshot['max_companies']:
            raise ValidationError('Reduce usuarios o empresas antes de aplicar el plan; no se desactivan datos automáticamente.')
        values={'customer_reference':customer,'revision':revision,'snapshot':snapshot,'ends_on':ends_on,
                'ever_capabilities':sorted(set((record.ever_capabilities if record else []) or [])|set(snapshot['capabilities']))}
        target=self.with_context(_erpec_entitlement_token=_INTERNAL)
        if record:
            record.with_context(_erpec_entitlement_token=_INTERNAL).write(values)
        else:
            record=target.create(values)
        self.env.registry.clear_cache()
        return record.with_env(self.env)

    @api.model
    def _lock_for_capacity(self):
        rights=entitlement(self.env)
        if rights:
            self.env.cr.execute('UPDATE erpec_tenant_entitlement SET write_date=write_date WHERE id=%s RETURNING id',[rights.id])
            rights.invalidate_recordset()
        return rights

    def _check_capacity(self):
        self.ensure_one()
        self.env['res.users'].flush_model(['active','share'])
        used=self.env['res.users'].sudo().search_count([('active','=',True),('share','=',False),('id','!=',SUPERUSER_ID)])
        companies=self.env['res.company'].sudo().search_count([])
        if used>self.snapshot['users'] or companies>self.snapshot['max_companies']:
            raise AccessError('Se supera la cantidad de usuarios internos o empresas contratadas. Revisa tu plan.')


class Base(models.AbstractModel):
    _inherit='base'

    def _check_company(self,fnames=None):
        # La comprobación nativa consulta referencias técnicas de módulos dependientes.
        # El permiso de la operación ya se exige en create/write/read, antes de esta validación privada.
        scoped=self.with_context(_erpec_entitlement_token=_INTERNAL)
        return super(Base,scoped)._check_company(fnames=fnames)

    def _check_access(self,operation):
        reason=denied(self,operation)
        if reason:
            return self,lambda:AccessError(reason)
        return super()._check_access(operation)

    def _search(self,domain,offset=0,limit=None,order=None):
        reason=denied(self,'read')
        if reason:
            raise AccessError(reason)
        return super()._search(domain,offset=offset,limit=limit,order=order)

    def read(self,fields=None,load='_classic_read'):
        reason=denied(self,'read')
        if reason:
            raise AccessError(reason)
        return super().read(fields=fields,load=load)

    @api.model_create_multi
    def create(self,values_list):
        reason=denied(self,'create')
        if reason:
            raise AccessError(reason)
        return super().create(values_list)

    def write(self,values):
        reason=denied(self,'write')
        if reason:
            raise AccessError(reason)
        return super().write(values)

    def unlink(self):
        reason=denied(self,'unlink')
        if reason:
            raise AccessError(reason)
        return super().unlink()


class Users(models.Model):
    _inherit='res.users'

    @api.model_create_multi
    def create(self,values_list):
        rights=self.env['erpec.tenant.entitlement']._lock_for_capacity()
        records=super().create(values_list)
        if rights:
            rights._check_capacity()
        return records

    def write(self,values):
        rights=self.env['erpec.tenant.entitlement']._lock_for_capacity() if set(values)&{'active','groups_id','share','company_ids'} else False
        if SUPERUSER_ID in self.ids and entitlement(self.env):
            raise AccessError('La cuenta técnica protegida no se modifica desde la instancia.')
        result=super().write(values)
        if rights:
            self.flush_recordset(['active','share'])
            rights._check_capacity()
        return result


class Company(models.Model):
    _inherit='res.company'

    @api.model_create_multi
    def create(self,values_list):
        rights=self.env['erpec.tenant.entitlement']._lock_for_capacity()
        records=super().create(values_list)
        if rights:
            rights._check_capacity()
        return records


class Menu(models.Model):
    _inherit='ir.ui.menu'

    def _filter_visible_menus(self):
        menus=super()._filter_visible_menus()
        return menus.filtered(lambda menu: not menu.action or menu.action.type!='ir.actions.act_window' or not denied(self.env[menu.action.res_model],'read'))


class Groups(models.Model):
    _inherit='res.groups'

    @api.model_create_multi
    def create(self, values_list):
        rights=self.env['erpec.tenant.entitlement']._lock_for_capacity()
        records=super().create(values_list)
        if rights:
            rights._check_capacity()
        return records

    def write(self, values):
        rights=self.env['erpec.tenant.entitlement']._lock_for_capacity() if set(values)&{'users','implied_ids'} else False
        result=super().write(values)
        if rights:
            rights._check_capacity()
        return result
