"""Configuración de casos tributarios; el cálculo y las cuentas siguen siendo nativos."""
import hashlib
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

OPERATIONS = [('purchase', 'Compras'), ('bill', 'Factura de proveedor'),
              ('import', 'Importaciones'), ('sale', 'Ventas / factura de cliente')]


class SriReference(models.Model):
    _name = 'erpec.tax.reference'
    _description = 'Referencia de catálogo SRI'
    _order = 'name'
    name = fields.Char('Descripción', required=True)
    code = fields.Char('Código SRI', required=True)
    family = fields.Char('Catálogo / familia', required=True)
    category = fields.Selection([('tax', 'Impuesto'), ('income', 'Retención en la fuente de Renta'), ('vat', 'Retención de IVA')], default='tax', required=True, string='Clase')
    rate_description = fields.Char('Tarifa y condiciones de la fuente')
    rate_mode = fields.Selection([
        ('single', 'Tarifa numérica única'),
        ('conditional', 'Tarifa condicionada o múltiple'),
        ('unspecified', 'Sin tarifa especificada'),
    ], string='Lectura de la tarifa', compute='_compute_rate_structure')
    fixed_rate = fields.Float('Tarifa única publicada (%)', compute='_compute_rate_structure', digits=(16, 6))
    version = fields.Char('Versión de la fuente', required=True)
    source_url = fields.Char('Fuente oficial', required=True)
    active = fields.Boolean('Activo', default=True)
    tax_ids = fields.One2many('account.tax', 'erpec_reference_id', 'Detalles vinculados')
    _sql_constraints = [('reference_unique', 'unique(family, code, version)', 'Ya existe este código en la versión del catálogo.')]

    @api.depends('rate_description')
    def _compute_rate_structure(self):
        pattern = re.compile(r'^\s*\d+(?:[\.,]\d+)?\s*$')
        for record in self:
            description = record.rate_description or ''
            if not description.strip():
                record.rate_mode = 'unspecified'
                record.fixed_rate = 0
            elif pattern.fullmatch(description):
                record.rate_mode = 'single'
                record.fixed_rate = float(description.strip().replace(',', '.'))
            else:
                record.rate_mode = 'conditional'
                record.fixed_rate = 0

    @api.constrains('source_url')
    def _check_source(self):
        from urllib.parse import urlparse
        for record in self:
            url = urlparse(record.source_url)
            if url.scheme != 'https' or not (url.hostname == 'sri.gob.ec' or (url.hostname or '').endswith('.sri.gob.ec')):
                raise ValidationError('Registre una fuente HTTPS oficial de sri.gob.ec.')


class TaxDetail(models.Model):
    _inherit = 'account.tax'
    erpec_reference_id = fields.Many2one('erpec.tax.reference', 'Referencia del catálogo SRI', ondelete='restrict')
    erpec_reference_rate_description = fields.Char(
        related='erpec_reference_id.rate_description', string='Tarifa publicada', readonly=True)
    erpec_reference_code = fields.Char(
        related='erpec_reference_id.code', string='Código SRI', readonly=True)
    erpec_reference_rate_mode = fields.Selection(
        related='erpec_reference_id.rate_mode', string='Lectura de tarifa', readonly=True)
    erpec_rate_review_note = fields.Text('Justificación de la tarifa condicionada', copy=False)
    erpec_rate_review_key = fields.Char('Huella de revisión tributaria', copy=False, readonly=True)
    erpec_rate_reviewed_at = fields.Datetime('Tarifa revisada el', copy=False, readonly=True)
    erpec_rate_reviewed_by_id = fields.Many2one(
        'res.users', 'Tarifa revisada por', copy=False, readonly=True)
    erpec_rate_review_current = fields.Boolean(
        'Conciliación vigente', compute='_compute_erpec_rate_status')
    erpec_rate_state = fields.Selection([
        ('missing', 'Falta referencia'),
        ('matched', 'Coincide'),
        ('mismatch', 'No coincide'),
        ('review_pending', 'Revisión pendiente'),
        ('reviewed', 'Revisada'),
        ('not_applicable', 'No aplica'),
    ], string='Conciliación', compute='_compute_erpec_rate_status')
    erpec_rate_status = fields.Char('Estado de conciliación', compute='_compute_erpec_rate_status')

    def _erpec_review_fingerprint(self):
        self.ensure_one()
        reference = self.erpec_reference_id
        source = '|'.join([
            str(reference.id or ''),
            reference.code or '',
            reference.category or '',
            reference.family or '',
            reference.version or '',
            reference.rate_description or '',
            reference.source_url or '',
            self.amount_type or '',
            format(abs(self.amount), '.12g'),
        ])
        return hashlib.sha256(source.encode('utf-8')).hexdigest()

    def _erpec_fixed_rate_matches(self):
        self.ensure_one()
        return (self.amount_type == 'percent'
                and abs(abs(self.amount) - self.erpec_reference_id.fixed_rate) <= 0.000001)

    @api.depends('erpec_reference_id', 'erpec_reference_id.code', 'erpec_reference_id.category',
                 'erpec_reference_id.family', 'erpec_reference_id.version',
                 'erpec_reference_id.rate_description', 'erpec_reference_id.source_url',
                 'erpec_reference_id.rate_mode', 'amount', 'amount_type',
                 'tax_group_id.l10n_ec_type', 'erpec_rate_review_key', 'erpec_rate_review_note')
    def _compute_erpec_rate_status(self):
        for tax in self:
            reference = tax.erpec_reference_id
            withholding = (tax.tax_group_id.l10n_ec_type or '').startswith('withhold_')
            if not reference:
                tax.erpec_rate_review_current = False
                tax.erpec_rate_state = 'missing' if withholding else 'not_applicable'
                tax.erpec_rate_status = ('Referencia SRI pendiente.' if withholding
                                         else 'No aplica conciliación de retención.')
            elif reference.category not in ('income', 'vat'):
                tax.erpec_rate_review_current = False
                tax.erpec_rate_state = 'mismatch' if withholding else 'not_applicable'
                tax.erpec_rate_status = ('La referencia vinculada no corresponde a una retención.' if withholding
                                         else 'No aplica conciliación de retención.')
            elif reference.rate_mode == 'single':
                matches = tax._erpec_fixed_rate_matches()
                tax.erpec_rate_review_current = matches
                tax.erpec_rate_state = 'matched' if matches else 'mismatch'
                tax.erpec_rate_status = (
                    'Tarifa operativa coincide con la referencia.' if matches
                    else 'La tarifa operativa no coincide con la referencia.'
                )
            else:
                current = bool(tax.erpec_rate_review_note and tax.erpec_rate_review_key
                               and tax.erpec_rate_review_key == tax._erpec_review_fingerprint())
                tax.erpec_rate_review_current = current
                tax.erpec_rate_state = 'reviewed' if current else 'review_pending'
                tax.erpec_rate_status = (
                    'Condición revisada para la versión y tarifa actuales.' if current
                    else 'Revisión contable pendiente para esta condición.'
                )

    def _erpec_retention_rate_issue(self):
        self.ensure_one()
        reference = self.erpec_reference_id
        if not reference or reference.category not in ('income', 'vat'):
            return False
        if reference.rate_mode == 'single' and not self._erpec_fixed_rate_matches():
            return ('La tarifa operativa de %s no coincide con %s %% publicada para el código %s.'
                    % (self.display_name, format(reference.fixed_rate, 'g'), reference.code))
        if reference.rate_mode != 'single' and not self.erpec_rate_review_current:
            return ('La tarifa de %s es condicionada o no está especificada; registre una revisión '
                    'vigente con justificación antes de usarla en un plan.' % self.display_name)
        return False

    def action_erpec_confirm_rate_review(self):
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError('Solo el responsable contable puede confirmar una tarifa condicionada.')
        for tax in self:
            reference = tax.erpec_reference_id
            if not reference or reference.category not in ('income', 'vat'):
                raise ValidationError('Vincule primero una referencia de retención de Renta o IVA.')
            if reference.rate_mode == 'single':
                if not tax._erpec_fixed_rate_matches():
                    raise ValidationError('Corrija la tarifa operativa; una divergencia fija no admite confirmación manual.')
                raise ValidationError('La tarifa numérica ya coincide automáticamente y no requiere confirmación manual.')
            if not (tax.erpec_rate_review_note or '').strip():
                raise ValidationError('Registre la justificación contable de la tarifa condicionada.')
            tax.with_context(erpec_confirming_rate_review=True).write({
                'erpec_rate_review_key': tax._erpec_review_fingerprint(),
                'erpec_rate_reviewed_at': fields.Datetime.now(),
                'erpec_rate_reviewed_by_id': self.env.user.id,
            })
        return True

    def write(self, vals):
        protected = {'erpec_rate_review_key', 'erpec_rate_reviewed_at', 'erpec_rate_reviewed_by_id'}
        if protected & vals.keys() and not self.env.context.get('erpec_confirming_rate_review'):
            raise AccessError('La revisión tributaria solo puede registrarse mediante la acción del formulario.')
        return super().write(vals)


class TaxClassification(models.Model):
    _name = 'erpec.tax.classification'
    _description = 'Tipo tributario de tercero o producto'
    _check_company_auto = True
    name = fields.Char('Tipo', required=True)
    kind = fields.Selection([('partner', 'Proveedor / cliente'), ('product', 'Producto')], required=True, string='Clasifica')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string='Empresa')
    active = fields.Boolean('Activo', default=True)
    _sql_constraints = [('type_unique', 'unique(company_id, kind, name)', 'El tipo ya existe en esta empresa.')]


class Partner(models.Model):
    _inherit = 'res.partner'
    erpec_tax_type_id = fields.Many2one('erpec.tax.classification', 'Tipo para planes de impuestos',
        groups='account.group_account_manager', company_dependent=True, domain="[('kind', '=', 'partner')]", ondelete='restrict')

    @api.constrains('erpec_tax_type_id')
    def _check_tax_type(self):
        for record in self:
            value = record.erpec_tax_type_id
            if value and (value.kind != 'partner' or value.company_id != self.env.company or not value.active):
                raise ValidationError('Seleccione un tipo de tercero activo de la empresa actual.')


class Product(models.Model):
    _inherit = 'product.template'
    erpec_tax_type_id = fields.Many2one('erpec.tax.classification', 'Tipo para planes de impuestos',
        groups='account.group_account_manager', company_dependent=True, domain="[('kind', '=', 'product')]", ondelete='restrict')

    @api.constrains('erpec_tax_type_id')
    def _check_tax_type(self):
        for record in self:
            value = record.erpec_tax_type_id
            if value and (value.kind != 'product' or value.company_id != self.env.company or not value.active):
                raise ValidationError('Seleccione un tipo de producto activo de la empresa actual.')


class TaxPolicy(models.Model):
    _name = 'erpec.tax.policy'
    _description = 'Plan de impuestos'
    _check_company_auto = True
    name = fields.Char('Plan', required=True)
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    active = fields.Boolean('Activo', default=True)
    case_ids = fields.One2many('erpec.tax.case', 'policy_id', 'Casos')
    note = fields.Text('Criterio contable y alcance')


class TaxCase(models.Model):
    _name = 'erpec.tax.case'
    _description = 'Caso del plan de impuestos'
    _check_company_auto = True
    name = fields.Char('Caso', required=True)
    policy_id = fields.Many2one('erpec.tax.policy', 'Plan', required=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one(related='policy_id.company_id', store=True)
    operation = fields.Selection(OPERATIONS, 'Operación', required=True, default='purchase')
    active = fields.Boolean('Activo', default=True)
    tax_ids = fields.Many2many('account.tax', string='Detalles de impuestos', check_company=True)
    income_withholding_ids = fields.Many2many('account.tax', 'erpec_case_income_rel', string='Detalles de retención de Renta', check_company=True)
    vat_withholding_ids = fields.Many2many('account.tax', 'erpec_case_vat_rel', string='Detalles de retención de IVA', check_company=True)
    mapping_ids = fields.One2many('erpec.tax.assignment', 'case_id', 'Asignaciones')
    note = fields.Text('Justificación del caso')

    def _configuration_issue(self):
        self.ensure_one()
        leaves = self.tax_ids.flatten_taxes_hierarchy()
        if not self.active or not self.policy_id.active:
            return 'El plan o caso está archivado.'
        if not leaves:
            return 'El caso no tiene detalles de impuestos; el vacío no acredita exención.'
        usage = 'sale' if self.operation == 'sale' else 'purchase'
        if self.tax_ids.filtered(lambda tax: tax.type_tax_use != usage or not tax.active):
            return 'Los detalles deben estar activos y corresponder a la operación del caso.'
        if leaves.filtered(lambda tax: tax.erpec_reference_id.category in ('income', 'vat')
                           or (tax.tax_group_id.l10n_ec_type or '').startswith('withhold_')):
            return 'Configure las retenciones en sus campos separados del impuesto facturado.'
        direction = 'sale' if usage == 'sale' else 'purchase'
        for kind, details in (('income', self.income_withholding_ids), ('vat', self.vat_withholding_ids)):
            for tax in details:
                if (tax.tax_group_id.l10n_ec_type != 'withhold_' + kind + '_' + direction
                        or tax.type_tax_use != 'none' or tax.amount_type != 'percent'
                        or tax.price_include or not -100 <= tax.amount <= 0):
                    return 'Revise la clase, operación y porcentaje de los detalles de retención.'
                if tax.erpec_reference_id.category != kind:
                    return 'Vincule cada retención con su clase de catálogo SRI.'
                rate_issue = tax._erpec_retention_rate_issue()
                if rate_issue:
                    return rate_issue
        leaves |= self.income_withholding_ids | self.vat_withholding_ids
        for tax in leaves:
            if not tax.active or not tax.erpec_reference_id or not tax.erpec_reference_id.active:
                return 'Falta una referencia SRI activa en un detalle componente.'
            for lines in (tax.invoice_repartition_line_ids, tax.refund_repartition_line_ids):
                tax_lines = lines.filtered(lambda line: line.repartition_type == 'tax')
                if not tax_lines or any(not line.account_id or line.account_id.deprecated for line in tax_lines):
                    return 'Complete las cuentas contables de factura y devolución de cada detalle.'
        return False


class TaxAssignment(models.Model):
    _name = 'erpec.tax.assignment'
    _description = 'Asignación de caso por tipos'
    _rec_name = 'case_id'
    _check_company_auto = True
    case_id = fields.Many2one('erpec.tax.case', 'Caso del plan', required=True, check_company=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    operation = fields.Selection(OPERATIONS, 'Operación', required=True, default='purchase')
    partner_type_id = fields.Many2one('erpec.tax.classification', 'Tipo de proveedor / cliente', required=True,
        domain="[('kind', '=', 'partner')]", check_company=True, ondelete='restrict')
    product_type_id = fields.Many2one('erpec.tax.classification', 'Tipo de producto', required=True,
        domain="[('kind', '=', 'product')]", check_company=True, ondelete='restrict')
    _sql_constraints = [('assignment_unique', 'unique(company_id, operation, partner_type_id, product_type_id)',
                         'Ya existe una asignación para esta empresa, operación y combinación de tipos. Modifique esa asignación.')]

    @api.constrains('case_id', 'operation', 'partner_type_id', 'product_type_id', 'company_id')
    def _check_assignment(self):
        for record in self:
            if record.operation != record.case_id.operation:
                raise ValidationError('La operación debe coincidir con la del caso.')
            if record.partner_type_id.kind != 'partner' or record.product_type_id.kind != 'product':
                raise ValidationError('La asignación requiere un tipo de tercero y otro de producto.')
            if not record.partner_type_id.active or not record.product_type_id.active:
                raise ValidationError('Los tipos de la asignación deben estar activos.')
            issue = record.case_id._configuration_issue()
            if issue:
                raise ValidationError(issue)

    @api.model
    def _resolve_case(self, company, operation, partner, product):
        partner_type = partner.with_company(company).commercial_partner_id.erpec_tax_type_id
        product_type = product.with_company(company).erpec_tax_type_id
        if not partner_type or not product_type:
            return self.env['erpec.tax.case'], 'Falta clasificar el tercero comercial o el producto.'
        if not partner_type.active or not product_type.active:
            return self.env['erpec.tax.case'], 'Hay un tipo archivado; revise la clasificación.'
        assignment = self.search([('company_id', '=', company.id), ('operation', '=', operation),
            ('partner_type_id', '=', partner_type.id), ('product_type_id', '=', product_type.id)], limit=2)
        if len(assignment) != 1:
            return self.env['erpec.tax.case'], 'No existe una asignación única para esta combinación y operación.'
        if assignment.case_id.operation != operation or assignment.case_id.company_id != company:
            return assignment.case_id, 'El caso ya no coincide con la empresa u operación de la asignación; corríjala.'
        issue = assignment.case_id._configuration_issue()
        return assignment.case_id, issue or 'Caso encontrado. Compare sus impuestos con los del documento antes de operar.'


class TaxScenario(models.Model):
    _inherit = 'erpec.tax.plan'
    case_id = fields.Many2one('erpec.tax.case', 'Caso asignado', compute='_compute_case')
    planned_tax_ids = fields.Many2many('account.tax', 'erpec_scenario_planned_tax_rel', string='Detalles previstos por el caso', compute='_compute_case')
    planned_effective_tax_ids = fields.Many2many('account.tax', 'erpec_scenario_effective_tax_rel', string='Resultado previsto tras posición fiscal', compute='_compute_case')
    planned_account_ids = fields.Many2many('account.account', string='Cuentas contables previstas', compute='_compute_case')
    planned_income_withholding_ids = fields.Many2many('account.tax', 'erpec_scenario_income_rel', string='Retenciones de Renta previstas', compute='_compute_case')
    planned_vat_withholding_ids = fields.Many2many('account.tax', 'erpec_scenario_vat_rel', string='Retenciones de IVA previstas', compute='_compute_case')
    withholding_account_ids = fields.Many2many('account.account', 'erpec_scenario_withhold_account_rel', string='Cuentas de retenciones previstas', compute='_compute_case')
    case_status = fields.Text('Estado del mapeo', compute='_compute_case')

    @api.depends('company_id', 'operation', 'product_id', 'partner_id', 'effective_tax_ids')
    def _compute_case(self):
        for record in self:
            case, message = self.env['erpec.tax.assignment'].with_company(record.company_id)._resolve_case(
                record.company_id, record.operation, record.partner_id, record.product_id)
            record.case_id = case
            record.planned_income_withholding_ids = case.income_withholding_ids
            record.planned_vat_withholding_ids = case.vat_withholding_ids
            retentions = case.income_withholding_ids | case.vat_withholding_ids
            record.withholding_account_ids = (retentions.invoice_repartition_line_ids | retentions.refund_repartition_line_ids).filtered(
                lambda line: line.repartition_type == 'tax').account_id
            record.planned_tax_ids = case.tax_ids
            record.planned_effective_tax_ids = record.fiscal_position_id.map_tax(case.tax_ids)
            if case and record.planned_effective_tax_ids != record.effective_tax_ids:
                message += ' DIFERENCIA: los impuestos operativos actuales no coinciden con el caso.'
            leaves = record.planned_effective_tax_ids.flatten_taxes_hierarchy()
            record.planned_account_ids = (leaves.invoice_repartition_line_ids | leaves.refund_repartition_line_ids).filtered(
                lambda line: line.repartition_type == 'tax').account_id
            if retentions:
                message += ' Retenciones: valide tarifa y base según el caso y la fuente vigente; esta consulta no calcula ni registra retenciones.'
            intersection = self.env['erpec.tax.policy']._intersection(record.company_id, record.operation, record.partner_id, record.product_id)
            if intersection['configured']:
                record.planned_tax_ids = intersection['taxes']
                record.planned_effective_tax_ids = record.fiscal_position_id.map_tax(intersection['taxes'])
                record.planned_income_withholding_ids = intersection['income']
                record.planned_vat_withholding_ids = intersection['vat']
                retentions = intersection['income'] | intersection['vat']
                record.withholding_account_ids = (retentions.invoice_repartition_line_ids | retentions.refund_repartition_line_ids).filtered(
                    lambda line: line.repartition_type == 'tax').account_id
                leaves = record.planned_effective_tax_ids.flatten_taxes_hierarchy()
                record.planned_account_ids = (leaves.invoice_repartition_line_ids | leaves.refund_repartition_line_ids).filtered(
                    lambda line: line.repartition_type == 'tax').account_id
                message = intersection['message']
            record.case_status = message
