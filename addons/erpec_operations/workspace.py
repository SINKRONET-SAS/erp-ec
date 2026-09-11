"""Accesos de operación Community y diagnóstico básico de la empresa."""
from odoo import api, fields, models


class Workspace(models.Model):
    _inherit = 'erpec.workspace'

    company_readiness = fields.Text('Configuración de la empresa', compute='_compute_company_readiness')
    fiscal_scope = fields.Text('Emisión electrónica', compute='_compute_company_readiness')

    @api.depends('company_id.name','company_id.vat','company_id.country_id','company_id.currency_id','company_id.street')
    def _compute_company_readiness(self):
        for workspace in self:
            company = workspace.company_id
            missing = []
            if company.country_id.code != 'EC':
                missing.append('país Ecuador')
            if company.currency_id.name != 'USD':
                missing.append('moneda USD')
            if not company.vat:
                missing.append('RUC de la empresa')
            if not company.street:
                missing.append('dirección de la empresa')
            workspace.company_readiness = ('Completar: '+', '.join(missing)+'.') if missing else 'Datos básicos presentes. Revisar su exactitud y la configuración contable con el responsable de la empresa.'
            workspace.fiscal_scope = 'Pendiente: conector de emisión electrónica y validación de XML/RIDE y estados fiscales. Crear una factura contable en Odoo no acredita su autorización por el SRI.'

    def _open_operation(self, external_id):
        self.ensure_one()
        self.check_access('read')
        return self.env['ir.actions.actions']._for_xml_id(external_id)

    def action_sales(self):
        return self._open_operation('sale.action_quotations')

    def action_purchases(self):
        return self._open_operation('purchase.purchase_rfq')

    def action_inventory(self):
        return self._open_operation('stock.stock_picking_type_action')

    def action_invoices(self):
        return self._open_operation('account.action_move_out_invoice_type')
