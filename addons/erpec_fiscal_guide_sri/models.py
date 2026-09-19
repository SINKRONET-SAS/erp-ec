"""Guía de remisión electrónica (codDoc 06): documento propio (no es un asiento contable) enlazable a
un traslado de inventario (stock.picking) y a la factura que la sustenta. Firma XAdES y transmisión
al SRI reutilizando erpec.fiscal.emission; numeración por punto de emisión y ambiente."""
import base64
import secrets

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.erpec_fiscal_native import guiaremision_engine, xades
from odoo.addons.erpec_fiscal_sri.models import _INTERNAL as _SRI_INTERNAL

SEQUENCE_CODE = 'erpec.fiscal.guide.sri'


class Guide(models.Model):
    _name = 'erpec.fiscal.guide'
    _description = 'Guía de remisión electrónica (SRI)'
    _check_company_auto = True
    _order = 'id desc'
    _rec_name = 'sri_number'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict')
    point_id = fields.Many2one('erpec.fiscal.point', string='Punto de emisión', required=True, check_company=True, ondelete='restrict',
                               default=lambda self: self._default_point())
    ambiente = fields.Selection(related='point_id.ambiente', string='Ambiente')
    sri_number = fields.Char('Número SRI', readonly=True, copy=False)
    picking_id = fields.Many2one('stock.picking', string='Traslado de inventario', check_company=True, copy=False, ondelete='restrict')
    move_id = fields.Many2one('account.move', string='Factura de venta que sustenta', domain="[('move_type','=','out_invoice'),('state','=','posted')]",
                              check_company=True, ondelete='restrict')
    support_authorization = fields.Char('Autorización de la factura (10 a 49 dígitos)')
    partner_id = fields.Many2one('res.partner', string='Destinatario', required=True)
    recipient_address = fields.Char('Dirección de destino', required=True)
    origin_address = fields.Char('Dirección de partida', required=True)
    reason = fields.Char('Motivo del traslado', required=True, default='Venta')
    carrier_name = fields.Char('Transportista (razón social)', required=True)
    carrier_type = fields.Selection([('04', 'RUC'), ('05', 'Cédula'), ('06', 'Pasaporte'), ('08', 'Identificación del exterior')],
                                    string='Tipo de identificación del transportista', required=True, default='04')
    carrier_vat = fields.Char('Identificación del transportista', required=True)
    plate = fields.Char('Placa', required=True, size=20)
    date_start = fields.Date('Inicio del traslado', required=True, default=fields.Date.context_today)
    date_end = fields.Date('Fin del traslado', required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('erpec.fiscal.guide.line', 'guide_id', string='Bienes a trasladar', copy=True)
    emission_ids = fields.One2many('erpec.fiscal.emission', 'guide_id', string='Emisiones SRI', copy=False)
    state = fields.Selection([('draft', 'Borrador'), ('emitted', 'Firmada / emitida')], compute='_compute_state', store=True)

    @api.model
    def _default_point(self):
        points = self.env['erpec.fiscal.point'].search([('company_id', '=', self.env.company.id)])
        return self.env.user.ec_point_id if self.env.user.ec_point_id in points else (points if len(points) == 1 else points.browse())

    @api.depends('emission_ids')
    def _compute_state(self):
        for guide in self:
            guide.state = 'emitted' if guide.emission_ids else 'draft'

    @api.onchange('point_id')
    def _onchange_point(self):
        if self.point_id and not self.origin_address:
            self.origin_address = self.point_id.establishment_address

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id and not self.recipient_address:
            self.recipient_address = self.partner_id.street

    def write(self, values):
        if any(guide.emission_ids for guide in self):
            raise ValidationError('La guía ya fue firmada y emitida; no se modifica.')
        return super().write(values)

    def unlink(self):
        if any(guide.emission_ids or guide.sri_number for guide in self):
            raise ValidationError('Conserva la guía emitida para conciliación y auditoría.')
        return super().unlink()

    def _load_from_picking(self, picking):
        self.ensure_one()
        lines = [(0, 0, {'code': move.product_id.default_code or False, 'description': move.product_id.display_name,
                         'quantity': move.product_uom_qty}) for move in picking.move_ids if move.product_uom_qty > 0]
        self.write({'line_ids': lines})

    def _next_number(self):
        # Un consecutivo por punto de emisión Y por ambiente: pruebas y producción nunca comparten numeración.
        self.ensure_one()
        point = self.point_id
        code = '%s.%s.%s.%s' % (SEQUENCE_CODE, point.ambiente, point.establishment, point.emission)
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', code), ('company_id', '=', self.company_id.id)], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'Guías de remisión SRI %s-%s (%s)' % (point.establishment, point.emission, 'pruebas' if point.ambiente == '1' else 'producción'),
                'code': code, 'company_id': self.company_id.id, 'padding': 9, 'number_next': 1, 'implementation': 'no_gap'})
        return '%s-%s-%s' % (point.establishment, point.emission, sequence.next_by_id())

    def _gather_sri_data(self):
        self.ensure_one()
        company, partner = self.company_id, self.partner_id.commercial_partner_id
        if company.country_id.code != 'EC':
            raise ValidationError('Se requiere una empresa de Ecuador.')
        company._check_regime_supported()
        if not company.ec_native_ordinary or not company.ec_native_accounting:
            raise ValidationError('Completa el perfil fiscal de la empresa (perfil ordinario y obligación contable).')
        if not self.line_ids:
            raise ValidationError('Agrega al menos un bien a trasladar.')
        data = {
            'date': str(fields.Date.context_today(self)), 'ambiente': self.point_id.ambiente,
            'establishment_address': self.point_id.establishment_address, 'issuer_vat': company.vat, 'issuer_name': company.name,
            'issuer_address': company.street, 'accounting': company.ec_native_accounting, 'origin_address': self.origin_address,
            'carrier_type': self.carrier_type, 'carrier_vat': self.carrier_vat, 'carrier_name': self.carrier_name, 'plate': self.plate,
            'date_start': str(self.date_start), 'date_end': str(self.date_end), 'recipient_vat': partner.vat,
            'recipient_name': partner.name, 'recipient_address': self.recipient_address, 'reason': self.reason,
            'items': [{'code': line.code, 'description': line.description, 'quantity': line.quantity} for line in self.line_ids]}
        if self.move_id:
            number = self.move_id.l10n_latam_document_number
            data['support'] = {'doc_type': '01', 'doc_number': number or '', 'doc_date': str(self.move_id.invoice_date),
                               'doc_authorization': self.support_authorization or False}
        return data

    def action_sri_emit(self):
        self.ensure_one()
        self.check_access('write')
        if self.emission_ids:
            return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission', 'res_id': self.emission_ids[0].id, 'view_mode': 'form'}
        certificate = self.env['erpec.fiscal.certificate'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not certificate or not certificate.verified:
            raise ValidationError('Configura y verifica primero el certificado de firma electrónica de esta empresa.')
        point = self.point_id
        if point.ambiente == '2' and not point.production_acknowledged:
            raise ValidationError('La emisión en producción requiere un punto de emisión habilitado para producción.')
        data = self._gather_sri_data()
        number = self.sri_number or self._next_number()
        data['number'] = number
        data['numeric'] = str(secrets.randbelow(10**8)).zfill(8)
        try:
            access_key, xml_unsigned = guiaremision_engine.generate(data)
            xml_signed = xades.sign(xml_unsigned, *certificate._signing_material(), self.company_id.vat)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        emission = self.env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=_SRI_INTERNAL).create({
            'guide_id': self.id, 'access_key': access_key, 'ambiente': point.ambiente,
            'xml_unsigned': base64.b64encode(xml_unsigned), 'xml_signed': base64.b64encode(xml_signed),
            'state': 'signed', 'message': 'Firmada. Procesar la cola para transmitir al SRI.'})
        self.env.cr.execute('UPDATE erpec_fiscal_guide SET sri_number=%s WHERE id=%s', [number, self.id])
        self.invalidate_recordset(['sri_number'])
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission', 'res_id': emission.id, 'view_mode': 'form'}


class GuideLine(models.Model):
    _name = 'erpec.fiscal.guide.line'
    _description = 'Bien a trasladar en una guía de remisión'

    guide_id = fields.Many2one('erpec.fiscal.guide', required=True, ondelete='cascade')
    code = fields.Char('Código interno', size=25)
    description = fields.Char('Descripción', required=True)
    quantity = fields.Float('Cantidad', required=True, digits=(16, 6), default=1.0)

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('La cantidad debe ser positiva.')


class Picking(models.Model):
    _inherit = 'stock.picking'

    ec_guide_ids = fields.One2many('erpec.fiscal.guide', 'picking_id', string='Guías de remisión SRI', copy=False)

    def action_create_sri_guide(self):
        self.ensure_one()
        if self.ec_guide_ids:
            guide = self.ec_guide_ids[0]
        else:
            partner = self.partner_id
            point = self.env.user.ec_point_id if self.env.user.ec_point_id.company_id == self.company_id else self.env['erpec.fiscal.point'].search([('company_id', '=', self.company_id.id)]).sorted(lambda item: (not item.establishment_id.is_principal, item.establishment, item.emission))[:1]
            if not point:
                raise ValidationError('Configura primero un establecimiento y punto de emisión (Fiscal > Establecimientos y puntos de emisión).')
            guide = self.env['erpec.fiscal.guide'].create({
                'company_id': self.company_id.id, 'point_id': point.id, 'picking_id': self.id,
                'partner_id': partner.id or self.company_id.partner_id.id,
                'recipient_address': partner.street or partner.commercial_partner_id.street or '-',
                'origin_address': point.establishment_address, 'carrier_name': '-', 'carrier_vat': '-', 'plate': '-',
                'reason': 'Venta' if self.picking_type_code == 'outgoing' else 'Traslado'})
            guide._load_from_picking(self)
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.guide', 'res_id': guide.id, 'view_mode': 'form'}


class Emission(models.Model):
    _inherit = 'erpec.fiscal.emission'

    guide_id = fields.Many2one('erpec.fiscal.guide', string='Guía de remisión', check_company=True, ondelete='restrict')
    _sql_constraints = [('one_guide', 'unique(guide_id)', 'La guía ya tiene una emisión nativa.')]

    @api.depends('guide_id.company_id')
    def _compute_company_id(self):
        super()._compute_company_id()
        for emission in self:
            if not emission.company_id and emission.guide_id:
                emission.company_id = emission.guide_id.company_id

    def _has_source(self):
        return super()._has_source() or bool(self.guide_id)
