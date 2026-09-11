"""Semilla idempotente de tesorería; solo DEMO sin RUC, en Odoo shell."""
from odoo import fields
import json
company=env.company
if company.vat or 'DEMO' not in company.name:
    raise RuntimeError('La semilla requiere la empresa DEMO sin RUC.')
env=env(context=dict(env.context,no_reset_password=True,tracking_disable=True))
def bind(name,record):
    env['ir.model.data'].create({'module':'erpec_treasury_demo','name':name,'model':record._name,'res_id':record.id,'noupdate':True})
def account(code,name,kind):
    record=env['account.account'].search([('code','=',code),('company_ids','in',company.ids)],limit=1)
    if record:
        if record.account_type!=kind or not record.reconcile:
            raise RuntimeError('Cuenta de demostración incompatible.')
        return record
    return env['account.account'].create({'code':code,'name':name,'account_type':kind,'reconcile':True,'company_ids':[(6,0,company.ids)]})
env['erpec.workspace'].action_sanitize_demo()
marker=env.ref('erpec_treasury_demo.period',raise_if_not_found=False)
if not marker:
    company.erpec_payroll_payable_id=account('ECDEMONPAY','Nómina por pagar DEMO','liability_payable')
    pending=account('ECDEMOTRAN','Pagos en tránsito DEMO','asset_current')
    bank=env['account.journal'].create({'name':'Banco de ensayo DEMO','code':'ECDT','type':'bank','company_id':company.id})
    bank.outbound_payment_method_line_ids.payment_account_id=pending
    bank.inbound_payment_method_line_ids.payment_account_id=pending
    company.erpec_payroll_bank_journal_id=bank
    plan=env['account.analytic.plan'].create({'name':'Centros de nómina DEMO'})
    lines=[]
    for index,wage in enumerate([1200,800]):
        employee=env['hr.employee'].create({'name':['Ana — empleada ficticia DEMO','Luis — empleado ficticio DEMO'][index],'company_id':company.id})
        partner=env['res.partner'].create({'name':employee.name,'company_id':company.id})
        center=env['account.analytic.account'].create({'name':['Administración DEMO','Operaciones DEMO'][index],'plan_id':plan.id,'company_id':company.id})
        lines.append((0,0,{'employee_id':employee.id,'partner_id':partner.id,'analytic_id':center.id,'start_date':'2025-01-01','wage':wage,'approved':True}))
    period=env['erpec.payroll.period'].create({'name':'Julio 2026 — dos empleados DEMO','policy_id':env.ref('erpec_operational_demo.payroll_policy').id,'month':7,'line_ids':lines})
    period.action_calculate();period.action_close();period.action_post();period.action_prepare_payments()
    for index,item in enumerate(period.disbursement_ids.sorted('id')):
        amounts=[100,item.amount-100] if index==0 else [100]
        for number,amount in enumerate(amounts):
            action=item.action_pay()
            payment=env['account.payment.register'].with_context(**action['context']).create({'journal_id':bank.id,'amount':amount,'payment_difference_handling':'open'})._create_payments()
            statement=env['account.bank.statement.line'].create({'journal_id':bank.id,'date':fields.Date.today(),'payment_ref':'DEMO nómina '+str(index+1)+' pago '+str(number+1),'partner_id':item.partner_id.id,'amount':-amount})
            env['erpec.bank.match'].create({'statement_line_id':statement.id,'payment_id':payment.id}).action_match()
            assert statement.is_reconciled
    assert sorted(period.disbursement_ids.mapped('status'))==['partial','settled']
    bind('period',period);bind('bank',bank)
else:
    period=marker
    if not company.erpec_payroll_bank_journal_id:
        company.erpec_payroll_bank_journal_id=env.ref('erpec_treasury_demo.bank')
result={'periodId':period.id,'employeeCount':len(period.line_ids),'payments':[{'id':p.id,'net':p.amount,'residual':p.residual,'state':p.status} for p in period.disbursement_ids],'syntheticOperations':True,'externalBankTransfers':False}
print(json.dumps(result,ensure_ascii=True))
if env.context.get("erpec_seed_rollback"):
    env.cr.rollback()
else:
    env.cr.commit()
