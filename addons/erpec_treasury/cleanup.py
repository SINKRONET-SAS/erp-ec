"""Saneamiento limitado a los identificadores de la semilla inicial de la demo."""
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class Workspace(models.Model):
    _inherit = 'erpec.workspace'

    @api.model
    def action_sanitize_demo(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('El saneamiento requiere administración.')
        company = self.env.company
        if company.vat or 'DEMO' not in company.name or company.country_id.code != 'EC':
            raise ValidationError('Solo se permite sanear la empresa DEMO sin RUC.')
        self.env.cr.execute('SELECT id FROM res_company WHERE id=%s FOR UPDATE',[company.id])
        result = self.env['account.move']
        for key in ['bill','invoice']:
            existing = self.env.ref('erpec_sanitized_demo.'+key,raise_if_not_found=False)
            if existing:
                result |= existing
        if result:
            if len(result)!=2 or result.company_id!=company:
                raise ValidationError('El saneamiento previo no está completo o pertenece a otra empresa.')
            self._link_sanitized_documents()
            return self._sanitized_action(result)

        source = [self.env.ref('erpec_demo_seed.'+key) for key in ['bill','invoice']]
        for move, expected in zip(source,[200,500]):
            if move.company_id!=company or move.state!='posted' or move.amount_total!=expected or len(move.invoice_line_ids)!=1 or move.ec_fiscal_job_ids:
                raise ValidationError('La semilla cambió o tiene actividad fiscal. Revisión manual necesaria.')
            retentions = move.ec_accounting_withholding_ids
            if len(retentions)!=1 or retentions.state!='posted' or retentions.amount!=expected*.02:
                raise ValidationError('Las retenciones ya no corresponden al ensayo inicial.')
            matched = move.line_ids.matched_debit_ids | move.line_ids.matched_credit_ids
            partners = (matched.debit_move_id | matched.credit_move_id).move_id - move
            if partners != retentions.entry_id:
                raise ValidationError('Existen pagos u otras conciliaciones ajenas a la semilla. No se modifica el documento.')
        taxes = {}
        for use in ['purchase','sale']:
            tax = self.env['account.tax'].search([('company_id','=',company.id),('type_tax_use','=',use),
                ('amount_type','=','percent'),('amount','=',15),('price_include','=',False)],limit=1)
            if not tax:
                raise ValidationError('Falta el IVA general del 15 % en la localización; no se inventará un impuesto.')
            taxes[use] = tax
        accounts = {}
        for kind,code,label in [('expense','ECDEMOSEXP','Servicios adquiridos DEMO'),('income','ECDEMOSINC','Servicios prestados DEMO')]:
            account = self.env['account.account'].search([('code','=',code),('company_ids','in',company.ids)],limit=1)
            if not account:
                account = self.env['account.account'].create({'code':code,'name':label,
                    'account_type':kind,'company_ids':[(6,0,company.ids)]})
            if account.account_type!=kind:
                raise ValidationError('La cuenta reservada a la demo tiene otra clasificación.')
            accounts[kind] = account
        products = (source[0] | source[1]).invoice_line_ids.product_id
        products.with_company(company).write({'property_account_expense_id':accounts['expense'].id,
            'property_account_income_id':accounts['income'].id,'taxes_id':[(6,0,taxes['sale'].ids)],
            'supplier_taxes_id':[(6,0,taxes['purchase'].ids)]})
        quote = self.env.ref('erpec_demo_seed.quote',raise_if_not_found=False)
        if quote and quote.company_id==company and quote.state=='draft':
            quote.order_line.filtered(lambda l:l.product_id in products).write({'tax_id':[(6,0,taxes['sale'].ids)]})
        for index,(key,move) in enumerate(zip(['bill','invoice'],source)):
            retention = move.ec_accounting_withholding_ids
            retention.write({'reversal_date':fields.Date.today(),'reversal_reason':'SP02-D01: retirar retención ficticia del ensayo inicial'})
            retention.action_reverse()
            reverse = move._reverse_moves([{'date':fields.Date.today(),'invoice_date':fields.Date.today(),
                'ref':'SP02-D01: neutralización de documento histórico',
                'l10n_latam_document_type_id':self.env.ref('l10n_ec.ec_dt_04').id,
                'l10n_latam_document_number':'999-999-'+str(800001+index).zfill(9)}],cancel=True)
            use = 'purchase' if key=='bill' else 'sale'
            account = accounts['expense' if key=='bill' else 'income']
            original = move.invoice_line_ids
            values = original.copy_data()[0]
            values.update({'account_id':account.id,'tax_ids':[(6,0,taxes[use].ids)]})
            values.pop('move_id',None)
            replacement = self.env['account.move'].create({'move_type':move.move_type,
                'company_id':company.id,'partner_id':move.partner_id.id,'journal_id':move.journal_id.id,
                'invoice_date':fields.Date.today(),'ref':'DEMO corregida · SP02-D01 · '+move.name,
                'l10n_latam_document_type_id':self.env.ref('l10n_ec.ec_dt_01').id,
                'l10n_latam_document_number':'999-999-'+str(900001+index).zfill(9),
                'invoice_line_ids':[(0,0,values)]})
            replacement.action_post()
            if move.amount_residual or replacement.amount_total!=[230,575][index]:
                raise ValidationError('El saneamiento no conserva los saldos esperados.')
            for suffix,record in [(key,replacement),(key+'_reversal',reverse)]:
                self.env['ir.model.data'].create({'module':'erpec_sanitized_demo','name':suffix,
                    'model':record._name,'res_id':record.id,'noupdate':True})
            result |= replacement
        self._link_sanitized_documents()
        return self._sanitized_action(result)

    def _link_sanitized_documents(self):
        """Restaura solo vínculos conocidos de la semilla; nunca infiere un pedido."""
        changes = []
        for key, expected in [('bill', 230), ('invoice', 575)]:
            source = self.env.ref('erpec_demo_seed.' + key)
            replacement = self.env.ref('erpec_sanitized_demo.' + key)
            if (source.company_id != self.env.company or replacement.company_id != self.env.company
                    or source.state != 'posted' or replacement.state != 'posted'
                    or replacement.amount_total != expected or replacement.ec_fiscal_job_ids
                    or len(source.invoice_line_ids) != 1 or len(replacement.invoice_line_ids) != 1):
                raise ValidationError('Los documentos saneados cambiaron; revisa sus vínculos manualmente.')
            original, line = source.invoice_line_ids, replacement.invoice_line_ids
            if (line.product_id != original.product_id or line.quantity != original.quantity
                    or line.price_unit != original.price_unit or line.discount != original.discount
                    or len(line.tax_ids) != 1 or line.tax_ids.amount != 15):
                raise ValidationError('El detalle del documento saneado no coincide con su origen.')
            commercial = original.purchase_line_id if key == 'bill' else original.sale_line_ids
            current = line.purchase_line_id if key == 'bill' else line.sale_line_ids
            if len(commercial) != 1 or (current and current != commercial):
                raise ValidationError('Vínculo comercial ausente o ambiguo; no se asociará otro pedido.')
            order = commercial.order_id
            quantity = commercial.product_qty if key == 'bill' else commercial.product_uom_qty
            if (order.company_id != self.env.company or order.partner_id != source.partner_id
                    or order.state not in ('sale', 'purchase', 'done')
                    or commercial.product_id != original.product_id or quantity != original.quantity
                    or commercial.price_unit != original.price_unit):
                raise ValidationError('El pedido de origen cambió; no se modifica automáticamente.')
            allowed = source | source.reversal_move_ids | replacement
            linked = commercial.invoice_lines.move_id.filtered(lambda move: move.state != 'cancel')
            if linked - allowed:
                raise ValidationError('Hay otros documentos en el pedido; revisa una posible duplicación antes de vincular.')
            changes.append((key, replacement, line, commercial))
        before = {move.id: [(line.id, line.balance, line.amount_currency, line.account_id.id)
                  for line in move.line_ids] for _key, move, _line, _commercial in changes}
        for key, move, line, commercial in changes:
            if key == 'bill':
                if line.purchase_line_id != commercial:
                    line.purchase_line_id = commercial
                if commercial.taxes_id != line.tax_ids:
                    commercial.taxes_id = line.tax_ids
            else:
                if line.sale_line_ids != commercial:
                    line.sale_line_ids = commercial
                if commercial.tax_id != line.tax_ids:
                    commercial.tax_id = line.tax_ids
            if move.invoice_origin != commercial.order_id.name:
                move.invoice_origin = commercial.order_id.name
            if before[move.id] != [(item.id, item.balance, item.amount_currency, item.account_id.id) for item in move.line_ids]:
                raise ValidationError('La vinculación alteraría el asiento publicado; se revierte la operación.')

    def _sanitized_action(self, moves):
        return {'type':'ir.actions.act_window','name':'Documentos saneados de la demo',
                'res_model':'account.move','view_mode':'list,form','domain':[('id','in',moves.ids)]}


class LegacyMove(models.Model):
    _inherit = 'account.move'

    @api.depends('company_id','reversal_move_ids.state')
    def _compute_legacy_demo_notice(self):
        super()._compute_legacy_demo_notice()
        for move in self:
            if move.erpec_legacy_demo_notice and move.reversal_move_ids.filtered(lambda r:r.state=='posted'):
                move.erpec_legacy_demo_notice = 'Documento histórico neutralizado mediante reversión. Se conserva para trazabilidad; consulta los documentos saneados de la demo.'
