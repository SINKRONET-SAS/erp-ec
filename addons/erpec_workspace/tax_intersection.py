"""Aplicación nativa de la intersección de detalles entre planes de tercero y producto."""
from odoo import api, fields, models
from odoo.addons.erpec_fiscal_native.ats_catalog import SUPPORT_CODES
from odoo.exceptions import ValidationError

ATS_SUSTENTO_SELECTION = [(code, '%s — %s' % (code, data['name'])) for code, data in SUPPORT_CODES.items()]


class Classification(models.Model):
    _inherit = 'erpec.tax.classification'
    policy_ids = fields.Many2many('erpec.tax.policy', string='Planes de impuestos', check_company=True)


class Partner(models.Model):
    _inherit = 'res.partner'
    erpec_policy_ids = fields.Many2many('erpec.tax.policy', 'erpec_partner_policy_rel',
        string='Planes de impuestos', groups='account.group_account_manager')


class Product(models.Model):
    _inherit = 'product.template'
    erpec_policy_ids = fields.Many2many('erpec.tax.policy', 'erpec_product_policy_rel',
        string='Planes de impuestos', groups='account.group_account_manager')


class Case(models.Model):
    _inherit = 'erpec.tax.case'
    withholding_bases_confirmed = fields.Boolean('Bases y tarifas de retención revisadas',
        help='Confirma para este caso Renta sobre subtotal neto e IVA sobre IVA causado. Casos con otras bases requieren preparación manual.')
    ats_sustento_code = fields.Selection(ATS_SUSTENTO_SELECTION, string='Sustento tributario ATS',
        help='Código de sustento del comprobante (Catálogo ATS del SRI, Tabla 5) que corresponde a este caso. '
             'Solo aplica a compras: el esquema del ATS (ats.xsd, detalleComprasType) exige codSustento únicamente '
             'en el detalle de compras, no en el de ventas.')

    @api.constrains('operation', 'ats_sustento_code')
    def _check_ats_sustento_operation(self):
        for case in self:
            if case.ats_sustento_code and case.operation not in ('purchase', 'bill', 'import'):
                raise ValidationError('El sustento tributario ATS solo aplica a casos de compras, factura de proveedor o importaciones.')


class Policy(models.Model):
    _inherit = 'erpec.tax.policy'

    @api.model
    def _intersection(self, company, operation, partner, product):
        empty = self.env['account.tax']
        result = dict(configured=False, taxes=empty, income=empty, vat=empty, sustento_code=False,
                      bases_confirmed=False, message='Sin planes asignados: configuración nativa del artículo.')
        if not company or not partner or not product:
            return result
        if company not in self.env.companies:
            raise ValidationError('La empresa del documento no está habilitada en esta sesión.')
        # Lectura acotada de configuración: no concede edición de planes al vendedor.
        third = partner.sudo().with_company(company).commercial_partner_id
        item = product.sudo().with_company(company)
        partner_type, product_type = third.erpec_tax_type_id, item.erpec_tax_type_id
        left = (third.erpec_policy_ids | partner_type.policy_ids).filtered(lambda p: p.company_id == company)
        right = (item.erpec_policy_ids | product_type.policy_ids).filtered(lambda p: p.company_id == company)
        if not left and not right:
            return result
        result['configured'] = True
        if not left or not right:
            result['message'] = 'Complete los planes del tercero y del producto; no hay intersección.'
            return result
        if any(not p.active for p in left | right):
            raise ValidationError('Hay un plan archivado asignado al tercero o producto.')
        operations = ('bill', 'purchase') if operation == 'bill' else (operation,)
        def eligible(plans):
            cases = plans.case_ids.filtered(lambda c: c.active and c.operation in operations)
            return cases.filtered(lambda c: not c.mapping_ids or any(
                m.operation == c.operation and m.partner_type_id == partner_type and m.product_type_id == product_type for m in c.mapping_ids))
        left_cases, right_cases = eligible(left), eligible(right)
        for case in left_cases | right_cases:
            issue = case._configuration_issue()
            if issue:
                raise ValidationError(case.name + ': ' + issue)
        for key, field in (('taxes', 'tax_ids'), ('income', 'income_withholding_ids'), ('vat', 'vat_withholding_ids')):
            a = left_cases.mapped(field).flatten_taxes_hierarchy()
            b = right_cases.mapped(field).flatten_taxes_hierarchy()
            common = a & b
            if any(t.company_id != company for t in common):
                raise ValidationError('Un detalle común pertenece a otra empresa.')
            refs = common.mapped('erpec_reference_id')
            if len(refs) != len(common):
                raise ValidationError('Hay varios detalles comunes para la misma referencia SRI; elimine la duplicación del plan.')
            result[key] = empty.browse(common.ids)
        common_retentions = result['income'] | result['vat']
        applicable = (left_cases | right_cases).filtered(
            lambda c: bool((c.income_withholding_ids | c.vat_withholding_ids) & common_retentions.sudo()))
        result['bases_confirmed'] = bool(applicable) and all(applicable.mapped('withholding_bases_confirmed'))
        result['message'] = ('Detalles comunes aplicados automáticamente; planes distintos son compatibles.'
                             if result['taxes'] else 'Sin detalles de impuestos comunes; revise los planes antes de confirmar.')
        if common_retentions:
            result['message'] += (' Retenciones previstas separadas del impuesto facturado.' if result['bases_confirmed']
                                  else ' Retenciones pendientes: confirme bases y tarifas en los casos de ambos planes.')
        if operation in ('purchase', 'bill', 'import'):
            sustento_codes = set((left_cases | right_cases).mapped('ats_sustento_code')) - {False}
            if len(sustento_codes) == 1:
                result['sustento_code'] = next(iter(sustento_codes))
            elif sustento_codes:
                result['message'] += ' Sustento ATS ambiguo: los casos del tercero y del producto no coinciden en el mismo código.'
            else:
                result['message'] += ' Falta configurar el sustento tributario ATS en el caso aplicable.'
        return result


def selection(line, operation):
    order = line.order_id if line._name != 'account.move.line' else line.move_id
    return line.env['erpec.tax.policy']._intersection(order.company_id, operation, order.partner_id, line.product_id)


def apply_taxes(line, result, field, position):
    if result['configured']:
        line[field] = position.map_tax(result['taxes'])


class PurchaseLine(models.Model):
    _inherit = 'purchase.order.line'
    erpec_tax_notice = fields.Text('Aplicación del plan', compute='_compute_erpec_selection')
    erpec_retention_ids = fields.Many2many('account.tax', string='Retenciones previstas', compute='_compute_erpec_selection')

    @api.depends('product_id', 'order_id.partner_id', 'order_id.company_id')
    def _compute_erpec_selection(self):
        for line in self:
            result = selection(line, 'purchase')
            line.erpec_tax_notice = result['message']
            line.erpec_retention_ids = result['income'] | result['vat']

    def _compute_tax_id(self):
        super()._compute_tax_id()
        for line in self.filtered(lambda l: l.order_id.state in ('draft', 'sent', 'to approve') and l.product_id):
            apply_taxes(line, selection(line, 'purchase'), 'taxes_id', line.order_id.fiscal_position_id)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines.filtered(lambda l: l.order_id.state in ('draft', 'sent', 'to approve') and l.product_id):
            apply_taxes(line, selection(line, 'purchase'), 'taxes_id', line.order_id.fiscal_position_id)
        return lines

    def write(self, vals):
        result = super().write(vals)
        if 'product_id' in vals:
            self._compute_tax_id()
        return result


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def write(self, vals):
        result = super().write(vals)
        if {'partner_id', 'fiscal_position_id'} & vals.keys():
            self.filtered(lambda o: o.state in ('draft', 'sent', 'to approve')).order_line._compute_tax_id()
        return result

    def button_confirm(self):
        for line in self.order_line.filtered('product_id'):
            result = selection(line, 'purchase')
            if result['configured'] and not result['taxes']:
                raise ValidationError(result['message'])
            if result['configured'] and line.taxes_id != line.order_id.fiscal_position_id.map_tax(result['taxes']):
                raise ValidationError('Los planes cambiaron: vuelva a seleccionar el producto para actualizar los impuestos.')
        return super().button_confirm()


class SaleLine(models.Model):
    _inherit = 'sale.order.line'
    erpec_tax_notice = fields.Text('Aplicación del plan', compute='_compute_erpec_selection')
    erpec_retention_ids = fields.Many2many('account.tax', string='Retenciones previstas', compute='_compute_erpec_selection')

    @api.depends('product_id', 'order_id.partner_id', 'order_id.company_id')
    def _compute_erpec_selection(self):
        for line in self:
            result = selection(line, 'sale')
            line.erpec_tax_notice = result['message']
            line.erpec_retention_ids = result['income'] | result['vat']

    @api.depends('product_id', 'company_id', 'order_id.partner_id', 'order_id.fiscal_position_id')
    def _compute_tax_id(self):
        frozen = self.filtered(lambda l: l.order_id.state not in ('draft', 'sent'))
        editable = self - frozen
        super(SaleLine, editable)._compute_tax_id()
        for line in editable.filtered('product_id'):
            apply_taxes(line, selection(line, 'sale'), 'tax_id', line.order_id.fiscal_position_id)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for line in self.order_line.filtered('product_id'):
            result = selection(line, 'sale')
            if result['configured'] and not result['taxes']:
                raise ValidationError(result['message'])
            if result['configured'] and line.tax_id != line.order_id.fiscal_position_id.map_tax(result['taxes']):
                raise ValidationError('Los planes cambiaron: vuelva a seleccionar el producto para actualizar los impuestos.')
        return super().action_confirm()


class InvoiceLine(models.Model):
    _inherit = 'account.move.line'
    erpec_tax_notice = fields.Text('Aplicación del plan', compute='_compute_erpec_selection')
    erpec_retention_ids = fields.Many2many('account.tax', string='Retenciones previstas', compute='_compute_erpec_selection')
    erpec_ats_sustento_code = fields.Selection(ATS_SUSTENTO_SELECTION, string='Sustento ATS',
        compute='_compute_erpec_selection', store=True, readonly=False,
        help='Código de sustento tributario del Anexo Transaccional Simplificado, resuelto automáticamente desde '
             'el caso aplicable del tercero y del producto. Vacío si no hay un caso configurado o si los planes '
             'del tercero y del producto no coinciden en el mismo código; se completa manualmente en ese caso. '
             'No aplica a ventas (el esquema oficial del ATS solo exige este dato en el detalle de compras).')

    @api.depends('product_id', 'move_id.partner_id', 'move_id.company_id')
    def _compute_erpec_selection(self):
        for line in self:
            is_sale = line.move_id.is_sale_document()
            result = selection(line, 'sale' if is_sale else 'bill')
            line.erpec_tax_notice = result['message']
            line.erpec_retention_ids = result['income'] | result['vat']
            if is_sale:
                line.erpec_ats_sustento_code = False
            elif result.get('sustento_code'):
                line.erpec_ats_sustento_code = result['sustento_code']

    @api.depends('product_id', 'product_uom_id', 'move_id.partner_id', 'move_id.fiscal_position_id')
    def _compute_tax_ids(self):
        editable = self.filtered(lambda l: l.move_id.state == 'draft')
        super(InvoiceLine, editable)._compute_tax_ids()

    def _get_computed_taxes(self):
        native = super()._get_computed_taxes()
        if self.move_id.state != 'draft' or not self.product_id or not self.move_id.is_invoice():
            return native
        result = selection(self, 'sale' if self.move_id.is_sale_document() else 'bill')
        return self.move_id.fiscal_position_id.map_tax(result['taxes']) if result['configured'] else native


class Invoice(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        for line in self.filtered(lambda m: m.state == 'draft' and m.is_invoice()).invoice_line_ids.filtered('product_id'):
            result = selection(line, 'sale' if line.move_id.is_sale_document() else 'bill')
            if result['configured'] and not result['taxes']:
                raise ValidationError(result['message'])
            if result['configured'] and line.tax_ids != line.move_id.fiscal_position_id.map_tax(result['taxes']):
                raise ValidationError('Los planes cambiaron: vuelva a seleccionar el producto para actualizar los impuestos.')
        self._sync_plan_withholdings()
        return super().action_post()

    erpec_retention_summary = fields.Text('Retenciones consolidadas previstas', compute='_compute_retention_summary')

    def _retention_bases(self):
        self.ensure_one()
        grouped = {}
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda l: l.product_id and l.display_type == 'product'), 1):
            result = selection(line, 'sale' if self.is_sale_document() else 'bill')
            if not result['bases_confirmed']:
                continue
            native = line.tax_ids.compute_all(line.price_unit * (1 - line.discount / 100),
                currency=self.currency_id, quantity=line.quantity, product=line.product_id, partner=self.partner_id,
                is_refund=self.move_type in ('in_refund', 'out_refund'))
            vat_base = sum(row['amount'] for row in native['taxes']
                if self.env['account.tax'].browse(row['id']).tax_group_id.l10n_ec_type in
                ('vat05', 'vat08', 'vat12', 'vat13', 'vat14', 'vat15', 'zero_vat'))
            for kind, base in (('income', line.price_subtotal), ('vat', vat_base)):
                for tax in result[kind]:
                    entry = grouped.setdefault(tax.id, {'tax': tax, 'base': 0, 'lines': []})
                    entry['base'] += base
                    entry['lines'].append('Línea %s: %s' % (index, base))
        return grouped

    @api.depends('invoice_line_ids.product_id', 'invoice_line_ids.quantity', 'invoice_line_ids.price_unit',
                 'invoice_line_ids.discount', 'invoice_line_ids.tax_ids', 'partner_id')
    def _compute_retention_summary(self):
        for move in self:
            rows = []
            if move.is_invoice():
                for entry in move._retention_bases().values():
                    preview = self.env['erpec.purchase.withholding'].new({
                        'move_id': move, 'tax_id': entry['tax'], 'base_amount': entry['base']})
                    rows.append('%s · base %.2f · importe %.2f %s · %s' % (
                        entry['tax'].name, entry['base'], preview.estimated_amount,
                        move.currency_id.name, '; '.join(entry['lines'])))
            move.erpec_retention_summary = '\n'.join(rows) or 'Sin retenciones calculadas: revise la intersección y la confirmación de bases.'
            if move.is_sale_document():
                move.erpec_retention_summary += '\nPrevisión: el comprobante recibido del cliente se registra por el flujo de retenciones existente.'

    def _sync_plan_withholdings(self):
        if self.env.context.get('_erpec_syncing'):
            return
        for move in self.filtered(lambda m: m.state == 'draft' and isinstance(m.id, int)):
            generated = move.ec_withholding_ids.filtered('erpec_plan_generated')
            expected = move._retention_bases() if move.move_type == 'in_invoice' and move.currency_id.name == 'USD' else {}
            expected = {key: value for key, value in expected.items() if value['base'] > 0 and value['tax'].amount < 0}
            if move.ec_withholding_ids.filtered(lambda w: not w.erpec_plan_generated and w.tax_id.id in expected):
                raise ValidationError('Ya existe una preparación manual para un detalle automático; revise la duplicación.')
            for line in generated:
                if line.tax_id.id not in expected:
                    line.with_context(_erpec_syncing=True).unlink()
            for tax_id, entry in expected.items():
                values = {'base_amount': entry['base'], 'notes': 'Intersección automática; ' + '; '.join(entry['lines'])}
                existing = generated.filtered(lambda w: w.tax_id.id == tax_id)
                if existing:
                    existing.with_context(_erpec_syncing=True).write(values)
                else:
                    self.env['erpec.purchase.withholding'].with_context(_erpec_syncing=True).create({
                        **values, 'move_id': move.id, 'tax_id': tax_id, 'erpec_plan_generated': True})

    @api.model_create_multi
    def create(self, vals_list):
        records = super(Invoice, self.with_context(_erpec_syncing=True)).create(vals_list).with_env(self.env)
        records._sync_plan_withholdings()
        return records

    def write(self, vals):
        if {'company_id', 'currency_id', 'partner_id', 'move_type'} & vals.keys():
            self.filtered(lambda m: m.state == 'draft').ec_withholding_ids.filtered(
                'erpec_plan_generated').with_context(_erpec_syncing=True).unlink()
        result = super(Invoice, self.with_context(_erpec_syncing=True)).write(vals)
        if {'invoice_line_ids', 'line_ids', 'partner_id', 'currency_id', 'move_type'} & vals.keys():
            self._sync_plan_withholdings()
        return result


class PreparedWithholding(models.Model):
    _inherit = 'erpec.purchase.withholding'
    erpec_plan_generated = fields.Boolean('Generada por intersección', readonly=True, copy=False)


class InvoiceLineSync(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.move_id._sync_plan_withholdings()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if {'product_id', 'quantity', 'price_unit', 'discount', 'tax_ids'} & vals.keys():
            self.move_id._sync_plan_withholdings()
        return result

    def unlink(self):
        moves = self.move_id
        result = super().unlink()
        moves.exists()._sync_plan_withholdings()
        return result
