"""Entrada común por empresa, conservando permisos de las operaciones."""
from odoo import api, models
from odoo.exceptions import AccessError


class Workspace(models.Model):
    _inherit = 'erpec.workspace'

    @api.model
    def _apply_navigation_labels(self):
        # Actualiza solo idiomas instalados; no exige una localización en bases nuevas.
        menu = self.env.ref('account.menu_finance')
        for language in self.env['res.lang'].search([]):
            menu.with_context(lang=language.code).write({'name': 'Contabilidad'})

    @api.model
    def action_home(self):
        if not self.env.user.has_group('base.group_user'):
            raise AccessError('El centro de trabajo requiere un usuario interno.')
        company = self.env.company
        # Serializa la creación de la ficha única de la empresa activa.
        self.env.cr.execute('SELECT id FROM res_company WHERE id = %s FOR UPDATE', [company.id])
        record = self.search([('company_id', '=', company.id)], limit=1)
        if not record:
            record = self.sudo().create({'company_id': company.id})
        return {'id': self.env.ref('erpec_workspace.home_window').id,
                'type': 'ir.actions.act_window', 'name': 'Inicio · ERP EC',
                'res_model': self._name, 'res_id': record.id, 'view_mode': 'form',
                'views': [(self.env.ref('erpec_workspace.home_form').id, 'form')],
                'target': 'main', 'context': dict(self.env.context)}

    def action_area(self):
        self.ensure_one()
        self.check_access('read')
        areas = {
            'tax_plan': ('account.group_account_manager', 'erpec_workspace.tax_plan_action'),
            'sales': ('sales_team.group_sale_salesman', 'erpec_workspace.sale_action'),
            'purchases': ('purchase.group_purchase_user', 'purchase.purchase_rfq'),
            'inventory': ('stock.group_stock_user', 'stock.stock_picking_type_action'),
            'imports': ('stock.group_stock_user,account.group_account_manager', 'erpec_imports.import_action'),
            'manufacturing': ('mrp.group_mrp_user', 'mrp.mrp_production_action'),
            'workorders': ('mrp.group_mrp_user', 'mrp.mrp_workorder_todo'),
            'invoices': ('account.group_account_invoice', 'account.action_move_out_invoice_type'),
            'bills': ('account.group_account_invoice', 'account.action_move_in_invoice_type'),
            'payroll': ('erpec_payroll.group_payroll_manager', 'erpec_payroll.period_action'),
            'fiscal': ('account.group_account_user', 'erpec_fiscal_native.native_action'),
        }
        area = areas.get(self.env.context.get('erpec_area'))
        if not area or not any(self.env.user.has_group(group) for group in area[0].split(',')):
            raise AccessError('Tu perfil no tiene acceso a esta área de trabajo.')
        canonical_menus = {
            'sales': 'sale.menu_sale_quotations',
            'invoices': 'account.menu_action_move_out_invoice_type',
            'bills': 'account.menu_action_move_in_invoice_type',
        }
        menu_xmlid = canonical_menus.get(self.env.context.get('erpec_area'))
        action_xmlid = area[1]
        if menu_xmlid:
            menu = self.env.ref(menu_xmlid)
            if menu.id not in self.env['ir.ui.menu']._visible_menu_ids():
                raise AccessError('Tu perfil no tiene acceso al menú de esta área.')
            action_xmlid = menu.action.get_external_id()[menu.action.id]
        action = self.env['ir.actions.actions']._for_xml_id(action_xmlid)
        action['target'] = 'main'
        return action
