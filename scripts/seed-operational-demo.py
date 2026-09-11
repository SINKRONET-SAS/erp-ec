"""Escenarios repetibles de importación y nómina sintética; ejecutar con Odoo shell."""
import base64, json
from odoo import fields
from odoo.addons.erpec_payroll.parameters_ec2026 import PARAMS, SOURCES
company=env.company
if company.vat or 'DEMO' not in company.name:
    raise RuntimeError('Solo se permite preparar la empresa DEMO sin RUC')
env.ref('base.user_admin').write({'groups_id':[(4,env.ref('erpec_payroll.group_payroll_manager').id)]})

def bind(name,record):
    env['ir.model.data'].create({'module':'erpec_operational_demo','name':name,'model':record._name,'res_id':record.id,'noupdate':True})

def account(code,name,kind):
    return env['account.account'].create({'code':code,'name':name,'account_type':kind,'company_ids':[(6,0,company.ids)]})

if not env.ref('erpec_operational_demo.importation',raise_if_not_found=False):
    expense=account('ECDEMOEXP','Gastos operativos DEMO','expense')
    valuation=account('ECDEMOVAL','Inventario importado DEMO','asset_current')
    incoming=account('ECDEMOIN','Inventario por recibir DEMO','asset_current')
    outgoing=account('ECDEMOOUT','Inventario entregado DEMO','asset_current')
    journal=env['account.journal'].create({'name':'Importación DEMO','code':'ECDI','type':'general'})
    category=env['product.category'].create({'name':'Importados DEMO AVCO automático','property_cost_method':'average','property_valuation':'real_time','property_stock_journal':journal.id,'property_stock_valuation_account_id':valuation.id,'property_stock_account_input_categ_id':incoming.id,'property_stock_account_output_categ_id':outgoing.id,'property_account_expense_categ_id':expense.id})
    product=env['product.product'].create({'name':'Herramienta importada DEMO','type':'consu','is_storable':True,'categ_id':category.id,'supplier_taxes_id':[(5,0,0)]})
    supplier=env['res.partner'].create({'name':'Proveedor extranjero DEMO','country_id':env.ref('base.us').id})
    purchase=env['purchase.order'].create({'partner_id':supplier.id,'order_line':[(0,0,{'product_id':product.id,'product_qty':10,'price_unit':10,'taxes_id':[(5,0,0)]})]})
    purchase.button_confirm();receipt=purchase.picking_ids
    receipt.move_ids.quantity=5;receipt.move_ids.picked=True;receipt.with_context(skip_backorder=True).button_validate()
    attachment=env['ir.attachment'].create({'name':'Embarque DEMO sin validez.txt','datas':base64.b64encode(b'Documento ficticio. No autoriza importacion ni nacionalizacion.')})
    dossier=env['erpec.importation'].create({'name':'IMPORTACION-DEMO-001','partner_id':supplier.id,'purchase_ids':[(6,0,purchase.ids)],'shipment':'EMBARQUE-SINTETICO-001','customs_reference':'REFERENCIA-FICTICIA','attachment_ids':[(4,attachment.id)]})
    freight=env['product.product'].create({'name':'Flete DEMO','type':'service','property_account_expense_id':expense.id,'supplier_taxes_id':[(5,0,0)]})
    bill=env['account.move'].create({'move_type':'in_invoice','partner_id':supplier.id,'invoice_date':fields.Date.today(),'l10n_latam_document_number':'999-999-000000041','invoice_line_ids':[(0,0,{'product_id':freight.id,'name':'Flete sintético','quantity':1,'price_unit':10,'account_id':expense.id,'tax_ids':[(5,0,0)]})]})
    bill.action_post()
    env['erpec.import.charge'].create({'import_id':dossier.id,'name':'Flete capitalizable DEMO','kind':'capital','bill_line_id':bill.invoice_line_ids.id})
    cost=env['stock.landed.cost'].browse(dossier.action_prepare_cost()['res_id']);cost.button_validate()
    assert product.standard_price==12 and cost.account_move_id.state=='posted'
    bind('importation',dossier);bind('import_cost',cost);bind('import_product',product);bind('expense',expense)
    print('Importación DEMO: recepción 5 de 10, flete 10, costo unitario 12 y asiento publicado')
else:
    print('Se conserva el expediente de importación existente')

if not env.ref('erpec_operational_demo.payroll_closed',raise_if_not_found=False):
    expense=env.ref('erpec_operational_demo.expense')
    liability=account('ECDEMOPAY','Obligaciones de nómina DEMO','liability_current')
    journal=env['account.journal'].create({'name':'Nómina DEMO','code':'ECDN','type':'general'})
    policy=env['erpec.payroll.policy'].create({'name':'Ecuador 2026 · privado general v1','year':2026,'parameters':json.dumps(PARAMS),'journal_id':journal.id,'authorization':'Ensayo local autorizado. SKNOMINA tiene API. No se migra una empresa real ni se retira su cálculo; un solo motor nativo en esta demo ficticia.','source_reference':'Parámetros oficiales 2026. Privado general, continente, sin cargas ni exenciones especiales. Verificado 11-09-2026. '+json.dumps(SOURCES,ensure_ascii=False)})
    for concept in ('gross','net','personal_iess','tax','advances','loans','other_deductions','employer_iess','employer_other','thirteenth','fourteenth','vacation','reserve_iess'):
        credit_only=concept in ('net','personal_iess','tax','advances','loans','other_deductions')
        env['erpec.payroll.mapping'].create({'policy_id':policy.id,'concept':concept,'debit_id':expense.id if not credit_only else False,'credit_id':liability.id if concept!='gross' else False})
    policy.action_activate()
    employee=env['hr.employee'].create({'name':'Persona sintética DEMO','company_id':company.id})
    partner=env['res.partner'].create({'name':'Beneficiario sintético DEMO'})
    period=env['erpec.payroll.period'].create({'name':'NOMINA-DEMO-2026-08','policy_id':policy.id,'month':8,'line_ids':[(0,0,{'employee_id':employee.id,'partner_id':partner.id,'start_date':'2025-01-01','wage':1200,'approved':True})]})
    period.action_calculate();period.action_close();period.action_post()
    pending=env['erpec.payroll.period'].create({'name':'NOMINA-DEMO-2026-09','policy_id':policy.id,'month':9,'line_ids':[(0,0,{'employee_id':employee.id,'partner_id':partner.id,'start_date':'2025-01-01','wage':1200,'bonus':50,'hours_50':2})]})
    bind('payroll_closed',period);bind('payroll_pending',pending);bind('payroll_policy',policy)
    assert period.line_ids.net==1083.14 and period.move_id.state=='posted'
    print('Nómina DEMO: agosto contabilizado y septiembre listo para revisar novedades')
else:
    print('Se conservan los períodos de nómina existentes')
assert not company.vat
env.cr.commit()
