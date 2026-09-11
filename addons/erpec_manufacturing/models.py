"""Controles operativos sobre fabricación, inventario y tiempos nativos Community."""
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class Production(models.Model):
    _inherit = 'mrp.production'

    def button_mark_done(self):
        self.check_access('write')
        if self.workorder_ids.filtered(lambda order: order.state not in ('done', 'cancel')):
            raise UserError('Finaliza las operaciones de trabajo antes de cerrar la fabricación.')
        return super().button_mark_done()

    def _post_inventory(self, cancel_backorder=False):
        result = super()._post_inventory(cancel_backorder=cancel_backorder)
        # Un error revierte movimientos y valoración dentro de la misma transacción.
        for move in self.move_raw_ids.filtered(lambda item: item.state == 'done' and item.product_id.is_storable):
            locations = move.move_line_ids.location_id.filtered(lambda location: location.usage == 'internal')
            quants = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id), ('location_id', 'in', locations.ids),
                ('company_id', '=', move.company_id.id), ('quantity', '<', 0),
            ])
            if any(float_compare(quant.quantity, 0, precision_rounding=move.product_id.uom_id.rounding) < 0 for quant in quants):
                raise UserError('No se puede cerrar la fabricación: faltan existencias de %s. Repón materiales y vuelve a reservar.' % move.product_id.display_name)
        return result


class Workorder(models.Model):
    _inherit = 'mrp.workorder'

    erpec_pause_reason = fields.Char('Motivo de pausa')
    erpec_downtime = fields.Float('Pausa improductiva (min)', compute='_compute_downtime')

    @api.depends('time_ids.duration', 'time_ids.date_end')
    def _compute_downtime(self):
        for order in self:
            order.erpec_downtime = sum(order.time_ids.filtered('erpec_pause').mapped('duration'))

    def _close_pauses(self, all_users=False):
        pauses = self.time_ids.filtered(lambda item: item.erpec_pause and not item.date_end and (all_users or item.user_id == self.env.user))
        if pauses:
            pauses.write({'date_end': fields.Datetime.now()})

    def _lock_timer(self):
        self.check_access('write')
        # Orden estable; el reintento transaccional de Odoo resuelve una escritura concurrente.
        for order in self.sorted('id'):
            self.env.cr.execute('UPDATE mrp_workorder SET write_date=NOW() WHERE id=%s RETURNING id', [order.id])
        self.invalidate_recordset()
        self.env['mrp.workcenter.productivity'].invalidate_model()

    def button_start(self, raise_on_invalid_state=False):
        self._lock_timer()
        for order in self:
            if order.blocked_by_workorder_ids.filtered(lambda previous: previous.state != 'done'):
                raise UserError('Termina la operación precedente antes de iniciar esta etapa.')
        self._close_pauses()
        super().button_start(raise_on_invalid_state=raise_on_invalid_state)
        return True

    def button_pending(self):
        self._lock_timer()
        for order in self:
            if not (order.erpec_pause_reason or '').strip():
                raise UserError('Indica el motivo de pausa antes de detener el trabajo.')
            active = order.time_ids.filtered(lambda item: not item.date_end and item.user_id == self.env.user)
            if active.filtered('erpec_pause'):
                order.production_id.message_post(body='La pausa ya estaba registrada; no se duplica el intervalo.')
                continue
            if not active or order.state != 'progress':
                raise UserError('Inicia el trabajo antes de registrar una pausa.')
            super(Workorder, order).button_pending()
            self.env['mrp.workcenter.productivity'].create({'workorder_id': order.id, 'workcenter_id': order.workcenter_id.id, 'company_id': order.company_id.id, 'user_id': self.env.uid, 'loss_id': self.env.ref('erpec_manufacturing.pause_loss').id, 'erpec_pause': True, 'description': order.erpec_pause_reason})
            order.production_id.message_post(body='Pausa en %s: %s' % (order.name, order.erpec_pause_reason))
        return True

    def button_finish(self):
        self._lock_timer()
        for order in self.filtered(lambda item: item.state not in ('done', 'cancel')):
            if order.blocked_by_workorder_ids.filtered(lambda previous: previous.state != 'done'):
                raise UserError('Termina la operación precedente antes de finalizar esta etapa.')
        self._close_pauses(all_users=True)
        return super().button_finish()

    def button_done(self):
        self._lock_timer()
        if self.blocked_by_workorder_ids.filtered(lambda previous: previous.state != 'done'):
            raise UserError('Termina la operación precedente antes de finalizar esta etapa.')
        self._close_pauses(all_users=True)
        return super().button_done()


class Productivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'
    erpec_pause = fields.Boolean('Pausa documentada', readonly=True)
