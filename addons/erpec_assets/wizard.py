"""Asistentes con fecha y motivo explícitos para cambios contables."""
from odoo import fields, models
from odoo.exceptions import ValidationError
from .models import internal

class Adjustment(models.TransientModel):
    _name='erpec.asset.adjustment'
    _description='Cambio de estimación de activo'
    asset_id=fields.Many2one('erpec.asset',required=True,string='Activo')
    effective_date=fields.Date('Desde el primer día del mes',required=True,default=fields.Date.today)
    months=fields.Integer('Meses restantes',required=True)
    residual=fields.Float('Residual nuevo',required=True)
    reason=fields.Text('Justificación',required=True)

    def action_apply(self):
        self.ensure_one();asset=self.asset_id;asset._authorize()
        if asset.state!='running' or self.effective_date.day!=1 or not 1<=self.months<=1200 or not self.reason.strip():
            raise ValidationError('El cambio requiere activo en uso, primer día del mes, plazo válido y justificación.')
        asset._check_date(self.effective_date)
        posted=asset.line_ids.filtered('move_id')
        pending=asset.line_ids-posted
        if self.effective_date<asset.service_date or any(x.date>=self.effective_date for x in posted) or any(x.date<self.effective_date for x in pending):
            raise ValidationError('Contabiliza las cuotas anteriores; no cambies periodos ya contabilizados.')
        if not 0<=self.residual<=asset.cost-asset.accumulated:
            raise ValidationError('El residual no puede superar el valor en libros.')
        internal(self.env['erpec.asset.revision']).create({'asset_id':asset.id,'effective_date':self.effective_date,
            'previous_months':asset.months,'months':self.months,'previous_residual':asset.residual,'residual':self.residual,'reason':self.reason})
        internal(pending).unlink()
        internal(asset).write({'months':self.months,'residual':self.residual})
        asset._schedule(self.effective_date,self.months,asset.cost-asset.accumulated-self.residual)
        return {'type':'ir.actions.act_window_close'}

class Disposal(models.TransientModel):
    _name='erpec.asset.disposal'
    _description='Baja o venta de activo'
    asset_id=fields.Many2one('erpec.asset',required=True,string='Activo')
    date=fields.Date('Fecha de baja',required=True,default=fields.Date.today)
    sale_line_id=fields.Many2one('account.move.line',string='Línea de venta contabilizada',domain="[('move_id.move_type','=','out_invoice'),('move_id.state','=','posted'),('display_type','=','product')]")

    def action_apply(self):
        self.ensure_one();self.asset_id._dispose(self.date,self.sale_line_id)
        return {'type':'ir.actions.act_window_close'}

class Reversal(models.TransientModel):
    _name='erpec.asset.reversal'
    _description='Reversión integral de activo'
    asset_id=fields.Many2one('erpec.asset',required=True,string='Activo')
    date=fields.Date('Fecha de reversión',required=True,default=fields.Date.today)

    def action_apply(self):
        self.ensure_one();self.asset_id._reverse(self.date)
        return {'type':'ir.actions.act_window_close'}
