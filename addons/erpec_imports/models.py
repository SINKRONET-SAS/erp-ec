"""Expediente y clasificación de gastos; la valoración permanece en Community."""
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_INTERNAL = object()


class Importation(models.Model):
    _name = 'erpec.importation'
    _description = 'Expediente de importación comercial'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    name = fields.Char('Referencia', required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True, string='Empresa')
    partner_id = fields.Many2one('res.partner', 'Proveedor extranjero', required=True, check_company=True)
    currency_id = fields.Many2one('res.currency', 'Moneda de compra', required=True, default=lambda self: self.env.company.currency_id)
    incoterm_id = fields.Many2one('account.incoterms', 'Términos comerciales')
    transport = fields.Selection([('sea', 'Marítimo'), ('air', 'Aéreo'), ('land', 'Terrestre')], string='Transporte', required=True, default='sea')
    shipment = fields.Char('Embarque / documento de transporte', tracking=True)
    shipped_on = fields.Date('Fecha de embarque')
    arrival_on = fields.Date('Llegada prevista')
    customs_reference = fields.Char('Referencia de declaración / liquidación', tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Documentos de respaldo')
    purchase_ids = fields.Many2many('purchase.order', string='Compras', check_company=True)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_pickings', string='Recepciones')
    charge_ids = fields.One2many('erpec.import.charge', 'import_id', 'Gastos y tributos clasificados')
    cost_ids = fields.One2many('stock.landed.cost', 'erpec_import_id', 'Costos y ajustes de valoración')
    has_prepared_costs = fields.Boolean('Tiene costos preparados', compute='_compute_has_prepared_costs', compute_sudo=True)

    @api.depends('cost_ids')
    def _compute_has_prepared_costs(self):
        # Expone solo el bloqueo de edición, sin cargar documentos contables en bodega.
        for record in self:
            record.has_prepared_costs = bool(record.cost_ids)

    regulatory_note = fields.Text('Validación aduanera', default='Expediente documental local. No acredita autorización SENAE. El responsable contable debe revisar documentos y clasificación de costos, gastos y tributos antes de operar con datos reales.', readonly=True)
    _sql_constraints = [('reference_company', 'unique(company_id,name)', 'La referencia ya existe en esta empresa.')]

    @api.depends('purchase_ids.picking_ids')
    def _compute_pickings(self):
        for record in self:
            record.picking_ids = record.purchase_ids.picking_ids.filtered(lambda picking: picking.picking_type_id.code == 'incoming')

    @api.constrains('purchase_ids', 'company_id', 'partner_id', 'currency_id')
    def _check_purchases(self):
        for record in self:
            if any(order.company_id != record.company_id or order.partner_id != record.partner_id or order.currency_id != record.currency_id for order in record.purchase_ids):
                raise ValidationError('Las compras deben pertenecer a la misma empresa, proveedor y moneda del expediente.')

    def _lock(self):
        self.ensure_one()
        self.check_access('write')
        self.env.cr.execute('UPDATE erpec_importation SET write_date=NOW() WHERE id=%s RETURNING id', [self.id])
        self.invalidate_recordset()

    def action_prepare_cost(self):
        self._lock()
        charges = self.charge_ids.filtered(lambda charge: charge.kind == 'capital' and not charge.cost_id)
        if not charges:
            raise ValidationError('No hay gastos capitalizables nuevos. Revisa los costos ya preparados.')
        self._check_documents()
        receipts = self.picking_ids.filtered(lambda picking: picking.state == 'done')
        if not receipts:
            raise ValidationError('Completa al menos una recepción antes de distribuir costos.')
        products=receipts.move_ids.filtered(lambda move:move.state=='done' and move.product_id.is_storable).product_id
        if not products or any(product.cost_method not in ('fifo','average') or product.valuation!='real_time' for product in products):
            raise ValidationError('La importación requiere productos FIFO/AVCO con valoración contable automática.')
        for charge in charges:
            charge._validate_source()
        journal = self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('type', '=', 'general')], limit=1)
        if not journal:
            raise ValidationError('Configura un diario contable de valoración.')
        cost = self.env['stock.landed.cost'].with_context(_erpec_import_token=_INTERNAL).create({'erpec_import_id': self.id, 'company_id': self.company_id.id, 'account_journal_id': journal.id, 'picking_ids': [(6, 0, receipts.ids)], 'cost_lines': [(0, 0, {'name': charge.name, 'product_id': charge.bill_line_id.product_id.id, 'price_unit': charge.bill_line_id.balance, 'account_id': charge.bill_line_id.account_id.id, 'split_method': charge.split_method}) for charge in charges]})
        charges.with_context(_erpec_import_token=_INTERNAL).write({'cost_id': cost.id})
        cost.compute_landed_cost()
        return {'type': 'ir.actions.act_window', 'res_model': 'stock.landed.cost', 'res_id': cost.id, 'view_mode': 'form'}

    def _check_documents(self):
        self.ensure_one()
        if not self.shipment or not self.customs_reference or not self.attachment_ids:
            raise ValidationError('Completa embarque, referencia aduanera y documentos de respaldo.')
        self.attachment_ids.check_access('read')
        if any(attachment.company_id and attachment.company_id != self.company_id for attachment in self.attachment_ids):
            raise ValidationError('Los documentos de respaldo pertenecen a otra empresa.')

    def write(self, values):
        if set(values) & {'company_id', 'partner_id', 'currency_id', 'purchase_ids'} and self.cost_ids:
            raise ValidationError('No cambies la vinculación del expediente después de preparar costos.')
        return super().write(values)


class Charge(models.Model):
    _name = 'erpec.import.charge'
    _description = 'Clasificación de gasto de importación'
    _check_company_auto = True
    import_id = fields.Many2one('erpec.importation', required=True, ondelete='cascade', string='Importación')
    company_id = fields.Many2one(related='import_id.company_id', store=True, string='Empresa')
    name = fields.Char('Concepto', required=True)
    kind = fields.Selection([('capital', 'Costo capitalizable'), ('expense', 'Gasto del período'), ('recoverable', 'Tributo recuperable')], string='Clasificación revisada', required=True)
    bill_line_id = fields.Many2one('account.move.line', 'Línea de factura de gasto', required=True, check_company=True)
    split_method = fields.Selection([('equal', 'Igual'), ('by_quantity', 'Cantidad'), ('by_current_cost_price', 'Valor'), ('by_weight', 'Peso'), ('by_volume', 'Volumen')], default='by_current_cost_price', required=True, string='Criterio de reparto')
    cost_id = fields.Many2one('stock.landed.cost', 'Costo preparado', readonly=True, ondelete='restrict', copy=False)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Moneda')
    amount = fields.Monetary('Importe contabilizado', related='bill_line_id.balance', currency_field='currency_id')
    _sql_constraints = [('source_once', 'unique(bill_line_id)', 'La línea de gasto ya está asignada a una importación.')]

    @api.constrains('bill_line_id', 'import_id', 'kind')
    def _validate_source(self):
        for charge in self:
            line = charge.bill_line_id
            if line.company_id != charge.company_id or line.move_id.state != 'posted' or line.move_id.move_type != 'in_invoice' or line.display_type != 'product' or line.balance <= 0:
                raise ValidationError('Selecciona una línea positiva de una factura de proveedor contabilizada de esta empresa.')
            if charge.kind == 'capital' and (not line.product_id or line.product_id.type != 'service'):
                raise ValidationError('Los gastos capitalizables deben identificar un servicio de flete, seguro u otro costo revisado.')

    @api.model_create_multi
    def create(self, values_list):
        if any(values.get('cost_id') for values in values_list):
            raise ValidationError('El costo se vincula desde la preparación del expediente.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_erpec_import_token') is not _INTERNAL and (self.cost_id or 'cost_id' in values):
            raise ValidationError('Un gasto preparado no se modifica; utiliza un ajuste trazable.')
        return super().write(values)

    def unlink(self):
        if self.cost_id:
            raise ValidationError('Conserva la trazabilidad del gasto preparado.')
        return super().unlink()


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'
    erpec_import_id = fields.Many2one('erpec.importation', 'Expediente de importación', readonly=True, copy=False, ondelete='restrict')
    erpec_reversal_of_id = fields.Many2one('stock.landed.cost', 'Ajuste inverso de', readonly=True, copy=False, ondelete='restrict')
    _sql_constraints = [('one_import_reversal', 'unique(erpec_reversal_of_id)', 'Este costo ya tiene un ajuste inverso.')]

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_import_token') is not _INTERNAL and any(values.get('erpec_import_id') or values.get('erpec_reversal_of_id') for values in values_list):
            raise ValidationError('Prepara el costo desde el expediente de importación.')
        return super().create(values_list)

    def write(self, values):
        if set(values) & {'erpec_import_id', 'erpec_reversal_of_id'} and self.env.context.get('_erpec_import_token') is not _INTERNAL:
            raise ValidationError('El vínculo con el expediente es inmutable.')
        return super().write(values)

    def _check_can_validate(self):
        for cost in self.filtered('erpec_import_id'):
            cost.erpec_import_id._lock()
            cost.erpec_import_id._check_documents()
            if cost.company_id != cost.erpec_import_id.company_id or not cost.picking_ids or any(picking not in cost.erpec_import_id.picking_ids or picking.state != 'done' or picking.company_id != cost.company_id for picking in cost.picking_ids):
                raise ValidationError('Selecciona únicamente recepciones terminadas de las compras de este expediente.')
            products = cost.picking_ids.move_ids.filtered(lambda move: move.state == 'done' and move.product_id.is_storable).product_id
            if not products or any(product.cost_method not in ('fifo', 'average') or product.valuation != 'real_time' for product in products):
                raise ValidationError('La importación requiere productos FIFO/AVCO con valoración contable automática.')
            charges = cost.erpec_import_id.charge_ids.filtered(lambda charge: charge.cost_id == cost)
            if cost.erpec_reversal_of_id:
                original=cost.erpec_reversal_of_id
                expected=sorted((line.product_id.id, line.account_id.id, -line.price_unit, line.split_method) for line in original.cost_lines)
                if cost.picking_ids!=original.picking_ids:
                    raise ValidationError('El ajuste debe conservar las recepciones originales.')
            else:
                charges._validate_source()
                expected=sorted((charge.bill_line_id.product_id.id,charge.bill_line_id.account_id.id,charge.amount,charge.split_method) for charge in charges)
            actual=sorted((line.product_id.id,line.account_id.id,line.price_unit,line.split_method) for line in cost.cost_lines)
            if expected!=actual:
                raise ValidationError('Cada costo debe conservar producto, cuenta, importe y criterio del origen.')

            if not cost.erpec_reversal_of_id and (len(cost.cost_lines) != len(charges) or abs(sum(charges.mapped('amount'))-cost.amount_total) > cost.currency_id.rounding / 2):
                raise ValidationError('Los costos deben coincidir con los gastos de origen; no modifiques sus importes.')
        return super()._check_can_validate()

    def action_erpec_reverse(self):
        self.ensure_one()
        self.erpec_import_id._lock()
        if self.state != 'done' or self.erpec_reversal_of_id:
            raise ValidationError('Solo se ajusta un costo original contabilizado.')
        if self.search_count([('erpec_reversal_of_id', '=', self.id)]):
            raise ValidationError('Ya existe un ajuste inverso de este costo.')
        reverse = self.with_context(_erpec_import_token=_INTERNAL).create({'erpec_import_id': self.erpec_import_id.id, 'erpec_reversal_of_id': self.id, 'company_id': self.company_id.id, 'account_journal_id': self.account_journal_id.id, 'picking_ids': [(6, 0, self.picking_ids.ids)], 'cost_lines': [(0, 0, {'name': 'Reversión: '+line.name, 'product_id': line.product_id.id, 'price_unit': -line.price_unit, 'account_id': line.account_id.id, 'split_method': line.split_method}) for line in self.cost_lines]})
        reverse.compute_landed_cost()
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': reverse.id, 'view_mode': 'form'}


class ImportCostLine(models.Model):
    _inherit='stock.landed.cost.lines'

    def write(self,values):
        if self.cost_id.filtered(lambda cost:cost.erpec_import_id and cost.state=='done'):
            raise ValidationError('El costo contabilizado es inmutable; prepara un ajuste inverso.')
        return super().write(values)

    def unlink(self):
        if self.cost_id.filtered(lambda cost:cost.erpec_import_id and cost.state=='done'):
            raise ValidationError('Conserva las líneas del costo contabilizado.')
        return super().unlink()
