"""Datos ficticios para la instancia local de demostración; ejecutado en Odoo shell."""
import json
from pathlib import Path
root=Path('C:/proyectos web/ERP/_EC')
directory=root/'.cache/windows/demo'
private=json.loads((directory/'credentials.json').read_text(encoding='utf-8'))
company=env.company
company.write({'name':'Comercial Andina DEMO — Datos ficticios','country_id':env.ref('base.ec').id,'vat':False,'street':'Dirección ficticia para demostraciones'})
env['account.chart.template'].try_loading('ec',company,install_demo=False,force_create=False)
admin=env.ref('base.user_admin')
admin.write({'login':'demo','password':private['admin'],'tz':'America/Guayaquil','groups_id':[(4,env.ref('account.group_account_manager').id),(4,env.ref('account.group_account_user').id)]})
lang=env['res.lang'].with_context(active_test=False).search([('code','=','es_EC')],limit=1)
env['base.language.install'].create({'lang_ids':[(6,0,lang.ids)],'overwrite':False}).lang_install()
admin.write({'lang':'es_EC'})
if not env['erpec.workspace'].search_count([('company_id','=',company.id)]):
    env['erpec.workspace'].create({'company_id':company.id,'name':'Demostración comercial — datos ficticios'})
marker=env['ir.model.data'].search([('module','=','erpec_demo_seed'),('name','=','sale')],limit=1)
if not marker:
    customer=env['res.partner'].create({'name':'Cliente de ejemplo DEMO','company_id':company.id,'country_id':company.country_id.id})
    supplier=env['res.partner'].create({'name':'Proveedor de ejemplo DEMO','company_id':company.id,'country_id':company.country_id.id})
    service=env['product.product'].create({'name':'Servicio de implementación DEMO','type':'service','invoice_policy':'order','purchase_method':'purchase','list_price':500,'standard_price':200,'taxes_id':[(5,0,0)],'supplier_taxes_id':[(5,0,0)]})
    sale=env['sale.order'].create({'partner_id':customer.id,'order_line':[(0,0,{'product_id':service.id,'product_uom_qty':1,'price_unit':500,'tax_id':[(5,0,0)]})]})
    sale.action_confirm()
    invoice=sale._create_invoices()
    invoice.write({'invoice_date':'2026-09-10','date':'2026-09-10','l10n_latam_document_number':'001-001-000000001'})
    invoice.action_post()
    purchase=env['purchase.order'].create({'partner_id':supplier.id,'order_line':[(0,0,{'product_id':service.id,'product_qty':1,'price_unit':200,'taxes_id':[(5,0,0)]})]})
    purchase.button_confirm()
    purchase.action_create_invoice()
    bill=purchase.invoice_ids
    bill.write({'invoice_date':'2026-09-10','date':'2026-09-10','l10n_latam_document_number':'001-001-000000002'})
    bill.action_post()
    liability=env['account.account'].create({'name':'Retenciones DEMO por pagar','code':'ECDEMO01','account_type':'liability_current'})
    asset=env['account.account'].create({'name':'Retenciones DEMO recibidas','code':'ECDEMO02','account_type':'asset_current'})
    journal=env['account.journal'].search([('company_id','=',company.id),('type','=','general')],limit=1)
    for move,base,account,reference in [(invoice,500,asset,'DEMO-RET-RECIBIDA-1'),(bill,200,liability,'DEMO-RET-EMITIDA-1')]:
        retention=env['erpec.withholding'].create({'invoice_id':move.id,'reference':reference,'journal_id':journal.id,'date':'2026-09-10','line_ids':[(0,0,{'name':'Concepto ficticio 2% para mostrar el flujo; no tarifa legal','kind':'income','base':base,'rate':2,'account_id':account.id})]})
        retention.action_post()
    quote=env['sale.order'].create({'partner_id':customer.id,'order_line':[(0,0,{'product_id':service.id,'product_uom_qty':2,'price_unit':500,'tax_id':[(5,0,0)]})]})
    for name,record in [('sale',sale),('purchase',purchase),('invoice',invoice),('bill',bill),('quote',quote)]:
        env['ir.model.data'].create({'module':'erpec_demo_seed','name':name,'model':record._name,'res_id':record.id,'noupdate':True})
apps=env.ref('base.open_module_tree')
import ast
existing=ast.literal_eval(apps.domain or '[]')
if ('to_buy','=',False) not in existing:
    apps.write({'domain':repr(existing+[('to_buy','=',False)]),'name':'Aplicaciones ERP EC · Community'})
report=env['erpec.trial.balance'].create({'company_id':company.id,'date_from':'2026-09-01','date_to':'2026-09-30'})
report.action_generate()
assert report.total_balance==0 and report.total_debit==report.total_credit
assert not env['ir.module.module'].search_count([('state','=','installed'),('license','in',['OEEL-1','OPL-1'])])
result={'company':company.name,'database':'erpec_demo','url':'http://127.0.0.1:8369/odoo/action-'+str(env.ref('erpec_withholding_accounting.accounting_action').id),'accountingAction':env.ref('erpec_withholding_accounting.accounting_action').id,'trialBalanceId':report.id,'totalDebit':report.total_debit,'totalCredit':report.total_credit,'retentions':env['erpec.withholding'].search_count([]),'fiscalEmission':False,'syntheticData':True}
env.cr.commit()
(directory/'demo-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
