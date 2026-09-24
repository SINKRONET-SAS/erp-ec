"""DI25-04.2: agregador real del ATS. Concilia compras, ventas y anulados a partir de documentos
reales del ERP (account.move) y de los modelos de retención/emisión ya construidos en
erpec_withholding_accounting/erpec_fiscal_withholding_sri/erpec_fiscal_sri/erpec_fiscal_connector,
y presenta una vista previa de faltantes con el documento origen para cada dato que no se puede
completar automáticamente. No se fabrica ningún dato: un documento sin la información exigida por
el esquema del ATS se excluye de la sección correspondiente y aparece en la vista de faltantes con
su enlace al documento origen, no con un valor supuesto.

Vive en un módulo aparte (no en erpec_fiscal_native) porque necesita datos de erpec_fiscal_sri /
erpec_fiscal_withholding_sri, que a su vez dependen de erpec_fiscal_native: agregarlos ahí crearía
una dependencia circular.

Brechas conocidas y registradas explícitamente (no fabricadas):
- Ventas a consumidor final sin tipo de identificación SRI del cliente no se agrupan (no se asume
  el código de consumidor final "07" sin una fuente que confirme el criterio de la empresa para
  usarlo); el documento aparece en faltantes.
- Retención de IVA/renta (bloque air y valRetBien10/valRetServ20/valorRetBienes/valRetServ50/
  valorRetServicios/valRetServ100) solo se adjunta cuando la factura de compra tiene un único
  sustento tributario ATS (un único grupo de compra); si una factura se divide en varios grupos por
  tener líneas con distinto sustento, la retención no se reparte automáticamente entre ellos (campos
  opcionales del esquema: se omiten, no se inventa un reparto).
- Líneas con impuestos compuestos (más de un impuesto, p. ej. ICE + IVA en la misma línea) no se
  clasifican automáticamente: el documento completo aparece en faltantes hasta revisarse a mano.
- La sección anulados existe y se prueba (_gather_anulados), pero en este ERP es, en la práctica,
  inalcanzable desde la interfaz: erpec_fiscal_connector bloquea deliberadamente button_draft/
  button_cancel una vez que un comprobante tiene una emisión fiscal ("La cancelación contable no
  anula una solicitud fiscal."), y un comprobante que nunca se autorizó no tiene nada que reportar
  como anulado. El código queda listo por si una migración de datos legados o un cambio de flujo
  futuro produce el estado; no se fuerza ni se simula esa vía en el flujo real.
"""
import base64
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.erpec_fiscal_native import ats_catalog, ats_export

# Tabla 20 de la Ficha Técnica del ATS (retención de IVA por tramo de tarifa), ya documentada en
# erpec.withholding.line.sri_code (addons/erpec_fiscal_withholding_sri/models.py): 9=10%, 10=20%,
# 1=30%, 11=50%, 2=70%, 3=100%, 7=0%. 10% y 30% son las tarifas históricas de bienes; 20/50/70/100%
# las de servicios (30% y 70% son los tramos previos a la ampliación de tramos de 06/2015-01/2016
# documentada en ats_export.py). El código 7 (0%) no aporta a ningún campo de retención.
VAT_RETENTION_FIELD = {
    '9': 'val_ret_bien10',
    '1': 'valor_ret_bienes',
    '10': 'val_ret_serv20',
    '11': 'val_ret_serv50',
    '2': 'valor_ret_servicios',
    '3': 'val_ret_serv100',
}
VAT_TAXED_GROUPS = {'vat05', 'vat08', 'vat12', 'vat13', 'vat14', 'vat15'}


def _ats_identification(env, partner, sale):
    """(código tpIdProv/tpIdCliente, identificación) o (False, False) si no hay tipo SRI reconocido."""
    commercial = partner.commercial_partner_id
    ident = commercial.l10n_latam_identification_type_id
    ruc = env.ref('l10n_ec.ec_ruc', raise_if_not_found=False)
    dni = env.ref('l10n_ec.ec_dni', raise_if_not_found=False)
    passport = env.ref('l10n_ec.ec_passport', raise_if_not_found=False)
    if ruc and ident == ruc:
        return ('04' if sale else '01'), commercial.vat
    if dni and ident == dni:
        return ('05' if sale else '02'), commercial.vat
    if passport and ident == passport:
        return ('06' if sale else '03'), commercial.vat
    return False, False


def _ats_voucher_code(document_type):
    code = (document_type.code or '') if document_type else ''
    if not code.isdigit():
        return False
    voucher = str(int(code))
    return voucher if voucher in ats_catalog.VOUCHER_TYPES else False


def _line_category(line):
    taxes = line.tax_ids
    if len(taxes) != 1:
        return None
    group = taxes.tax_group_id.l10n_ec_type
    if group == 'not_charged_vat':
        return 'no_gra'
    if group == 'zero_vat':
        return 'imponible'
    if group in VAT_TAXED_GROUPS:
        return 'imp_grav'
    if group == 'exempt_vat':
        return 'exe'
    if group == 'ice':
        return 'ice'
    return None


def _period_bounds(year, month):
    first = date(year, int(month), 1)
    following = date(year + 1, 1, 1) if month == '12' else date(year, int(month) + 1, 1)
    return first, following


class Move(models.Model):
    _inherit = 'account.move'

    ec_purchase_sri_authorization = fields.Char(
        'Autorización SRI del proveedor (compra)',
        help='Número de autorización o clave de acceso del comprobante electrónico del proveedor. '
             'El ATS exige este dato en cada compra; el ERP no lo captura automáticamente porque la '
             'factura de compra se registra manualmente. Sin este dato la compra queda en faltantes '
             'del agregador ATS (erpec.ats.report).')

    @api.constrains('ec_purchase_sri_authorization', 'move_type')
    def _check_ec_purchase_sri_authorization(self):
        for move in self:
            if move.ec_purchase_sri_authorization and move.move_type != 'in_invoice':
                raise ValidationError('La autorización SRI del proveedor solo aplica a facturas de compra.')


class AtsReportCompra(models.Model):
    _name = 'erpec.ats.report.compra'
    _description = 'Fila de compra del agregador ATS'
    _order = 'id'

    report_id = fields.Many2one('erpec.ats.report', required=True, ondelete='cascade')
    move_id = fields.Many2one('account.move', string='Factura de compra', required=True, ondelete='restrict')
    cod_sustento = fields.Char(required=True)
    base_no_gra_iva = fields.Monetary(currency_field='currency_id')
    base_imponible = fields.Monetary(currency_field='currency_id')
    base_imp_grav = fields.Monetary(currency_field='currency_id')
    base_imp_exe = fields.Monetary(currency_field='currency_id')
    monto_ice = fields.Monetary(currency_field='currency_id')
    monto_iva = fields.Monetary(currency_field='currency_id')
    val_ret_bien10 = fields.Monetary(currency_field='currency_id')
    val_ret_serv20 = fields.Monetary(currency_field='currency_id')
    valor_ret_bienes = fields.Monetary(currency_field='currency_id')
    val_ret_serv50 = fields.Monetary(currency_field='currency_id')
    valor_ret_servicios = fields.Monetary(currency_field='currency_id')
    val_ret_serv100 = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='report_id.company_id.currency_id')
    payload = fields.Json(readonly=True)


class AtsReportVenta(models.Model):
    _name = 'erpec.ats.report.venta'
    _description = 'Fila agrupada de venta del agregador ATS'
    _order = 'id'

    report_id = fields.Many2one('erpec.ats.report', required=True, ondelete='cascade')
    tp_id_cliente = fields.Char(required=True)
    id_cliente = fields.Char(required=True)
    tipo_comprobante = fields.Char(required=True)
    tipo_emision = fields.Char(required=True)
    numero_comprobantes = fields.Integer(required=True)
    base_no_gra_iva = fields.Monetary(currency_field='currency_id')
    base_imponible = fields.Monetary(currency_field='currency_id')
    base_imp_grav = fields.Monetary(currency_field='currency_id')
    monto_iva = fields.Monetary(currency_field='currency_id')
    valor_ret_iva = fields.Monetary(currency_field='currency_id')
    valor_ret_renta = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='report_id.company_id.currency_id')
    move_ids = fields.Many2many('account.move', string='Comprobantes agrupados')
    payload = fields.Json(readonly=True)


class AtsReportAnulado(models.Model):
    _name = 'erpec.ats.report.anulado'
    _description = 'Fila de comprobante anulado del agregador ATS'
    _order = 'id'

    report_id = fields.Many2one('erpec.ats.report', required=True, ondelete='cascade')
    move_id = fields.Many2one('account.move', string='Comprobante anulado', required=True, ondelete='restrict')
    tipo_comprobante = fields.Char(required=True)
    establecimiento = fields.Char(required=True)
    punto_emision = fields.Char(required=True)
    secuencial_inicio = fields.Char(required=True)
    secuencial_fin = fields.Char(required=True)
    autorizacion = fields.Char(required=True)
    payload = fields.Json(readonly=True)


class AtsReportMissing(models.Model):
    _name = 'erpec.ats.report.missing'
    _description = 'Faltante detectado por el agregador ATS, con su documento origen'
    _order = 'id'

    report_id = fields.Many2one('erpec.ats.report', required=True, ondelete='cascade')
    move_id = fields.Many2one('account.move', string='Documento origen', ondelete='cascade')
    section = fields.Selection([('compra', 'Compra'), ('venta', 'Venta'), ('anulado', 'Anulado')], required=True)
    reason = fields.Char(required=True)


class AtsReport(models.Model):
    _name = 'erpec.ats.report'
    _description = 'Anexo Transaccional Simplificado (ATS) — agregador'
    _inherit = ['mail.thread']
    _order = 'year desc, month desc'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    year = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    month = fields.Selection([(code, label) for code, label in ats_catalog.MONTHS.items()], required=True)
    state = fields.Selection([('draft', 'Borrador'), ('built', 'Construido')], default='draft', readonly=True, copy=False, tracking=True)
    compra_ids = fields.One2many('erpec.ats.report.compra', 'report_id', copy=False)
    venta_ids = fields.One2many('erpec.ats.report.venta', 'report_id', copy=False)
    anulado_ids = fields.One2many('erpec.ats.report.anulado', 'report_id', copy=False)
    missing_ids = fields.One2many('erpec.ats.report.missing', 'report_id', copy=False)
    compra_count = fields.Integer(compute='_compute_counts')
    venta_count = fields.Integer(compute='_compute_counts')
    anulado_count = fields.Integer(compute='_compute_counts')
    missing_count = fields.Integer(compute='_compute_counts')
    xml_preview = fields.Binary('XML de ensayo', readonly=True, copy=False, attachment=False)
    xml_filename = fields.Char(readonly=True, copy=False)
    build_notice = fields.Text(readonly=True, copy=False)
    _sql_constraints = [('period_once', 'unique(company_id, year, month)', 'Ya existe un anexo ATS para esta empresa y período.')]

    @api.depends('compra_ids', 'venta_ids', 'anulado_ids', 'missing_ids')
    def _compute_counts(self):
        for report in self:
            report.compra_count = len(report.compra_ids)
            report.venta_count = len(report.venta_ids)
            report.anulado_count = len(report.anulado_ids)
            report.missing_count = len(report.missing_ids)

    # -- construcción -----------------------------------------------------------------------

    def _gather_compras(self, first, following):
        self.ensure_one()
        moves = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted'),
            ('invoice_date', '>=', first), ('invoice_date', '<', following),
        ])
        rows, missing = [], []
        for move in moves:
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            if not lines:
                continue
            reasons = []
            number = move.l10n_latam_document_number or ''
            parts = number.split('-')
            if len(parts) != 3 or not all(part.isdigit() for part in parts) or len(parts[0]) != 3 or len(parts[1]) != 3 or len(parts[2]) != 9:
                reasons.append('el número de documento no tiene el formato establecimiento-punto-secuencial (001-001-000000001)')
            if not move.ec_purchase_sri_authorization:
                reasons.append('falta la autorización SRI del comprobante del proveedor')
            voucher = _ats_voucher_code(move.l10n_latam_document_type_id)
            if not voucher:
                reasons.append('el tipo de comprobante no mapea a un código del catálogo ATS')
            tp_id, id_prov = _ats_identification(self.env, move.partner_id, sale=False)
            if not tp_id:
                reasons.append('el proveedor no tiene un tipo de identificación SRI reconocido (RUC/cédula/pasaporte)')
            uncategorized = lines.filtered(lambda l: not l.erpec_ats_sustento_code)
            if uncategorized:
                reasons.append('%d línea(s) sin sustento tributario ATS clasificado' % len(uncategorized))
            compound = lines.filtered(lambda l: _line_category(l) is None)
            if compound:
                reasons.append('%d línea(s) con impuestos compuestos o sin categoría ATS reconocida' % len(compound))
            if reasons:
                missing.append({'move_id': move.id, 'section': 'compra', 'reason': '; '.join(reasons)})
                continue
            establecimiento, punto, secuencial = parts
            groups = {}
            for line in lines:
                groups.setdefault(line.erpec_ats_sustento_code, []).append(line)
            retention_extra = self._compra_retention_extra(move) if len(groups) == 1 else {}
            for sustento, group_lines in groups.items():
                totals = {'base_no_gra_iva': 0.0, 'base_imponible': 0.0, 'base_imp_grav': 0.0,
                          'base_imp_exe': 0.0, 'monto_ice': 0.0, 'monto_iva': 0.0}
                for line in group_lines:
                    category = _line_category(line)
                    tax_amount = line.price_total - line.price_subtotal
                    if category == 'no_gra':
                        totals['base_no_gra_iva'] += line.price_subtotal
                    elif category == 'imponible':
                        totals['base_imponible'] += line.price_subtotal
                    elif category == 'imp_grav':
                        totals['base_imp_grav'] += line.price_subtotal
                        totals['monto_iva'] += tax_amount
                    elif category == 'exe':
                        totals['base_imp_exe'] += line.price_subtotal
                    elif category == 'ice':
                        totals['monto_ice'] += tax_amount
                # Regla real del DIMM (no del XSD, que lo marca opcional): un detalle de compra cuya
                # suma de bases imponibles + IVA + ICE supere USD 500 exige formasDePago. Confirmado
                # contra el motor real del DIMM (docs/evidencias/DI25/DI25-04-dimm-validacion.json).
                group_total = totals['base_imponible'] + totals['base_imp_grav'] + totals['monto_iva'] + totals['monto_ice']
                if group_total > 500 and not move.ec_fiscal_payment_code:
                    missing.append({'move_id': move.id, 'section': 'compra',
                                     'reason': 'la suma de bases e IVA/ICE de este detalle (sustento %s) supera USD 500 '
                                               'y no tiene forma de pago registrada (ec_fiscal_payment_code)' % sustento})
                    continue
                payload = dict({
                    'cod_sustento': sustento, 'tp_id_prov': tp_id, 'id_prov': id_prov, 'tipo_comprobante': voucher,
                    'fecha_registro': move.date.strftime('%d/%m/%Y'), 'establecimiento': establecimiento,
                    'punto_emision': punto, 'secuencial': secuencial, 'fecha_emision': move.invoice_date.strftime('%d/%m/%Y'),
                    'autorizacion': move.ec_purchase_sri_authorization,
                    'val_ret_bien10': 0.0, 'val_ret_serv20': 0.0, 'valor_ret_bienes': 0.0,
                    'val_ret_serv50': 0.0, 'valor_ret_servicios': 0.0, 'val_ret_serv100': 0.0,
                    'tot_bases_imp_reemb': 0.0, 'pago_local_o_exterior': '01',
                    'aplica_convenio_doble_tributacion': 'NA', 'pago_exterior_sujeto_retencion_normativa': 'NA',
                }, **totals)
                if move.ec_fiscal_payment_code:
                    payload['forma_pago'] = [move.ec_fiscal_payment_code]
                payload.update(retention_extra)
                rows.append((move, payload))
        return rows, missing

    def _compra_retention_extra(self, move):
        withholding = move.ec_accounting_withholding_ids.filtered(lambda w: w.direction == 'issued' and w.state == 'posted')
        if not withholding:
            return {}
        extra = {}
        air_entries = []
        for wh in withholding:
            for wh_line in wh.line_ids:
                if wh_line.kind == 'vat' and wh_line.sri_code in VAT_RETENTION_FIELD:
                    field = VAT_RETENTION_FIELD[wh_line.sri_code]
                    extra[field] = extra.get(field, 0.0) + wh_line.amount
                elif wh_line.kind == 'income' and wh_line.sri_code:
                    air_entries.append({'cod_ret_air': wh_line.sri_code, 'base_imp_air': wh_line.base,
                                         'porcentaje_air': wh_line.rate, 'val_ret_air': wh_line.amount})
        if air_entries:
            extra['air'] = air_entries
        authorized = withholding.filtered(lambda w: w.sri_number and w.emission_ids.filtered(lambda e: e.state == 'authorized'))
        if authorized:
            wh = authorized[0]
            entity, emission_pt, seq = wh.sri_number.split('-')
            authorized_emission = wh.emission_ids.filtered(lambda e: e.state == 'authorized')[0]
            extra.update({
                'estab_retencion1': entity, 'pto_emi_retencion1': emission_pt, 'sec_retencion1': seq,
                'aut_retencion1': authorized_emission.authorization_number, 'fecha_emi_ret1': wh.date.strftime('%d/%m/%Y'),
            })
        return extra

    def _gather_ventas(self, first, following):
        self.ensure_one()
        moves = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id), ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'), ('invoice_date', '>=', first), ('invoice_date', '<', following),
        ])
        groups, missing = {}, []
        for move in moves:
            reasons = []
            voucher = _ats_voucher_code(move.l10n_latam_document_type_id)
            if not voucher:
                reasons.append('el tipo de comprobante no mapea a un código del catálogo ATS')
            tp_id, id_cliente = _ats_identification(self.env, move.partner_id, sale=True)
            if not tp_id:
                reasons.append('el cliente no tiene un tipo de identificación SRI reconocido (RUC/cédula/pasaporte); '
                                'no se asume el código de consumidor final sin ese dato')
            authorized = move.ec_fiscal_emission_ids.filtered(lambda e: e.state == 'authorized') \
                or move.ec_fiscal_job_ids.filtered(lambda j: j.state == 'authorized')
            if not authorized:
                reasons.append('el comprobante no tiene una autorización SRI vigente (ni emisión nativa ni conector externo)')
            if reasons:
                missing.append({'move_id': move.id, 'section': 'venta', 'reason': '; '.join(reasons)})
                continue
            key = (tp_id, id_cliente, voucher, 'E')
            group = groups.setdefault(key, {
                'tp_id_cliente': tp_id, 'id_cliente': id_cliente, 'tipo_comprobante': voucher, 'tipo_emision': 'E',
                'numero_comprobantes': 0, 'base_no_gra_iva': 0.0, 'base_imponible': 0.0, 'base_imp_grav': 0.0,
                'monto_iva': 0.0, 'valor_ret_iva': 0.0, 'valor_ret_renta': 0.0, 'move_ids': [],
            })
            group['numero_comprobantes'] += 1
            group['move_ids'].append(move.id)
            sign = -1 if move.move_type == 'out_refund' else 1
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                category = _line_category(line)
                tax_amount = line.price_total - line.price_subtotal
                if category == 'no_gra':
                    group['base_no_gra_iva'] += sign * line.price_subtotal
                elif category == 'imponible':
                    group['base_imponible'] += sign * line.price_subtotal
                elif category == 'imp_grav':
                    group['base_imp_grav'] += sign * line.price_subtotal
                    group['monto_iva'] += sign * tax_amount
            received = move.ec_accounting_withholding_ids.filtered(lambda w: w.direction == 'received' and w.state == 'posted')
            for wh in received:
                for wh_line in wh.line_ids:
                    if wh_line.kind == 'vat':
                        group['valor_ret_iva'] += sign * wh_line.amount
                    elif wh_line.kind == 'income':
                        group['valor_ret_renta'] += sign * wh_line.amount
        return list(groups.values()), missing

    def _gather_anulados(self, first, following):
        self.ensure_one()
        moves = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id), ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'cancel'), ('invoice_date', '>=', first), ('invoice_date', '<', following),
        ])
        rows, missing = [], []
        for move in moves:
            authorized = move.ec_fiscal_emission_ids.filtered(lambda e: e.state == 'authorized') \
                or move.ec_fiscal_job_ids.filtered(lambda j: j.state == 'authorized')
            if not authorized:
                # Nunca fue autorizado por el SRI: no hay nada que reportar como anulado.
                continue
            voucher = _ats_voucher_code(move.l10n_latam_document_type_id)
            number = move.l10n_latam_document_number or ''
            parts = number.split('-')
            reasons = []
            if not voucher:
                reasons.append('el tipo de comprobante no mapea a un código del catálogo ATS')
            if len(parts) != 3 or not all(part.isdigit() for part in parts):
                reasons.append('el número de documento no tiene el formato establecimiento-punto-secuencial')
            access_key = getattr(authorized[0], 'access_key', False)
            if not access_key:
                reasons.append('falta la clave de acceso de la autorización')
            if reasons:
                missing.append({'move_id': move.id, 'section': 'anulado', 'reason': '; '.join(reasons)})
                continue
            establecimiento, punto, secuencial = parts
            payload = {'tipo_comprobante': voucher, 'establecimiento': establecimiento, 'punto_emision': punto,
                       'secuencial_inicio': secuencial, 'secuencial_fin': secuencial, 'autorizacion': access_key}
            rows.append((move, payload))
        return rows, missing

    def action_build(self):
        self.ensure_one()
        self.check_access('write')
        first, following = _period_bounds(self.year, self.month)
        compra_rows, compra_missing = self._gather_compras(first, following)
        venta_rows, venta_missing = self._gather_ventas(first, following)
        anulado_rows, anulado_missing = self._gather_anulados(first, following)

        self.compra_ids.unlink()
        self.venta_ids.unlink()
        self.anulado_ids.unlink()
        self.missing_ids.unlink()

        for move, payload in compra_rows:
            self.env['erpec.ats.report.compra'].create(dict({
                'report_id': self.id, 'move_id': move.id, 'cod_sustento': payload['cod_sustento'],
                'base_no_gra_iva': payload['base_no_gra_iva'], 'base_imponible': payload['base_imponible'],
                'base_imp_grav': payload['base_imp_grav'], 'base_imp_exe': payload['base_imp_exe'],
                'monto_ice': payload['monto_ice'], 'monto_iva': payload['monto_iva'],
                'val_ret_bien10': payload['val_ret_bien10'], 'val_ret_serv20': payload['val_ret_serv20'],
                'valor_ret_bienes': payload['valor_ret_bienes'], 'val_ret_serv50': payload['val_ret_serv50'],
                'valor_ret_servicios': payload['valor_ret_servicios'], 'val_ret_serv100': payload['val_ret_serv100'],
                'payload': payload,
            }))
        for payload in venta_rows:
            move_ids = payload.pop('move_ids')
            self.env['erpec.ats.report.venta'].create(dict({
                'report_id': self.id, 'move_ids': [(6, 0, move_ids)],
                'tp_id_cliente': payload['tp_id_cliente'], 'id_cliente': payload['id_cliente'],
                'tipo_comprobante': payload['tipo_comprobante'], 'tipo_emision': payload['tipo_emision'],
                'numero_comprobantes': payload['numero_comprobantes'], 'base_no_gra_iva': payload['base_no_gra_iva'],
                'base_imponible': payload['base_imponible'], 'base_imp_grav': payload['base_imp_grav'],
                'monto_iva': payload['monto_iva'], 'valor_ret_iva': payload['valor_ret_iva'],
                'valor_ret_renta': payload['valor_ret_renta'], 'payload': payload,
            }))
        for move, payload in anulado_rows:
            self.env['erpec.ats.report.anulado'].create(dict({
                'report_id': self.id, 'move_id': move.id, **payload,
            }))
        for entry in compra_missing + venta_missing + anulado_missing:
            self.env['erpec.ats.report.missing'].create(dict({'report_id': self.id}, **entry))

        notice_parts = ['%d compra(s), %d venta(s) agrupada(s), %d anulado(s), %d faltante(s).' % (
            len(compra_rows), len(venta_rows), len(anulado_rows),
            len(compra_missing) + len(venta_missing) + len(anulado_missing))]
        xml_bytes = None
        if compra_rows or venta_rows or anulado_rows:
            header = {
                'tipo_id_informante': 'R', 'id_informante': self.company_id.vat, 'razon_social': self.company_id.name,
                'anio': self.year, 'mes': self.month, 'codigo_operativo': 'IVA',
            }
            try:
                xml_bytes = ats_export.build_ats_xml(
                    header,
                    compras=[payload for _move, payload in compra_rows],
                    ventas=venta_rows,
                    anulados=[payload for _move, payload in anulado_rows],
                )
            except ValueError as error:
                notice_parts.append('El XML de ensayo no se generó: %s' % error)
        else:
            notice_parts.append('Sin datos suficientes para generar un XML de ensayo este período.')
        if xml_bytes:
            self.write({'xml_preview': base64.b64encode(xml_bytes), 'xml_filename': 'ATS-ENSAYO-%s-%s.xml' % (self.year, self.month)})
        self.write({'state': 'built', 'build_notice': ' '.join(notice_parts)})
        return True

    def action_reset(self):
        for report in self:
            report.check_access('write')
            report.compra_ids.unlink()
            report.venta_ids.unlink()
            report.anulado_ids.unlink()
            report.missing_ids.unlink()
            report.write({'state': 'draft', 'xml_preview': False, 'xml_filename': False, 'build_notice': False})
        return True
