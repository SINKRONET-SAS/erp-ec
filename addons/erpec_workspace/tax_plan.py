"""Consulta transversal de configuración; Odoo conserva la autoridad tributaria."""
from markupsafe import Markup, escape
from odoo import api, fields, models
from odoo.exceptions import AccessError


class TaxPlan(models.Model):
    _name = 'erpec.tax.plan'
    _description = 'Plan de impuestos · Escenario'
    _check_company_auto = True

    name = fields.Char('Escenario', required=True)
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    operation = fields.Selection([('purchase', 'Compras'), ('bill', 'Factura de proveedor'),
                                  ('import', 'Importaciones'), ('sale', 'Ventas / factura de cliente')],
                                 'Operación', required=True, default='purchase')
    product_id = fields.Many2one('product.product', 'Artículo', required=True, check_company=True)
    partner_id = fields.Many2one('res.partner', 'Proveedor / cliente', required=True, check_company=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', 'Posición fiscal resuelta', compute='_compute_plan')
    source_tax_ids = fields.Many2many('account.tax', 'erpec_plan_source_tax_rel', string='Impuestos del artículo', compute='_compute_plan')
    effective_tax_ids = fields.Many2many('account.tax', 'erpec_plan_effective_tax_rel', string='Impuestos resultantes', compute='_compute_plan')
    account_ids = fields.Many2many('account.account', string='Cuentas de repartición', compute='_compute_plan')
    detail = fields.Html('Trazabilidad y pendientes', compute='_compute_plan', sanitize=True)

    @api.depends('company_id', 'operation', 'product_id', 'partner_id',
                 'product_id.taxes_id', 'product_id.supplier_taxes_id',
                 'partner_id.property_account_position_id')
    def _compute_plan(self):
        for record in self:
            scoped = record.with_company(record.company_id)
            position = scoped.env['account.fiscal.position']._get_fiscal_position(scoped.partner_id)
            source = (scoped.product_id.taxes_id if scoped.operation == 'sale'
                      else scoped.product_id.supplier_taxes_id)._filter_taxes_by_company(record.company_id)
            if scoped.operation == 'sale' and scoped.product_id.type == 'combo':
                source = scoped.env['account.tax']
            effective = position.map_tax(source)
            leaves = effective.flatten_taxes_hierarchy()
            repartitions = (leaves.invoice_repartition_line_ids | leaves.refund_repartition_line_ids).filtered(
                lambda line: line.repartition_type == 'tax')
            record.fiscal_position_id = position
            record.source_tax_ids = source
            record.effective_tax_ids = effective
            record.account_ids = repartitions.account_id
            messages = []
            if not record.product_id or not record.partner_id:
                messages.append('Seleccione artículo y tercero para consultar la configuración.')
            if not source:
                messages.append('El artículo no tiene impuestos configurados para esta empresa y operación. No equivale a una exención validada.')
            if source and not effective:
                messages.append('La posición fiscal retira los impuestos de origen; revise su justificación.')
            if not position:
                messages.append('Sin posición fiscal: se conservan los impuestos del artículo.')
            if effective.filtered(lambda tax: not tax.active):
                messages.append('Hay impuestos archivados en el resultado; revise la posición fiscal.')
            rows = []
            for tax in leaves:
                for label, lines in [('Factura', tax.invoice_repartition_line_ids), ('Devolución', tax.refund_repartition_line_ids)]:
                    for line in lines.filtered(lambda item: item.repartition_type == 'tax'):
                        account = line.account_id.display_name or 'Sin cuenta explícita: Odoo usa la cuenta de la línea; revisar.'
                        rows.append(Markup('<tr><td>%s</td><td>%s</td><td>%s %%</td><td>%s</td></tr>') % (
                            escape(tax.display_name), label, line.factor_percent, escape(account)))
                if tax.tax_exigibility == 'on_payment':
                    messages.append('Impuesto al cobro: revisar también su cuenta transitoria en el catálogo.')
            record.detail = Markup('<ul>%s</ul><div class="table-responsive"><table class="table"><thead><tr><th>Impuesto componente</th><th>Documento</th><th>Repartición</th><th>Cuenta</th></tr></thead><tbody>%s</tbody></table></div>') % (
                Markup('').join(Markup('<li>%s</li>') % escape(message) for message in messages),
                Markup('').join(rows))

    def action_catalog(self):
        self.ensure_one()
        self.check_access('read')
        target = self.env.context.get('tax_plan_target')
        actions = {'taxes': 'account.action_tax_form', 'accounts': 'account.action_account_form',
                   'positions': 'account.action_account_fiscal_position_form'}
        if target not in actions:
            raise AccessError('Destino del plan de impuestos no permitido.')
        return self.env['ir.actions.actions']._for_xml_id(actions[target])
