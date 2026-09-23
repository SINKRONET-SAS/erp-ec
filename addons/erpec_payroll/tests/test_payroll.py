"""Pruebas de ensayo: cálculo decimal, cierre y contabilidad de nómina."""
import json
from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged
from ..engine import calculate

from ..demo_parameters import PARAMS

@tagged('post_install','-at_install')
class PayrollCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company=self.env.company
        self.company.write({'name':'DEMO nómina sintética','vat':False})
        self.expense=self.env['account.account'].create({'code':'PAYTESTEXP','name':'Nómina ensayo','account_type':'expense'})
        self.liability=self.env['account.account'].create({'code':'PAYTESTLIAB','name':'Obligaciones ensayo','account_type':'liability_current'})
        self.journal=self.env['account.journal'].create({'name':'Nómina ensayo','code':'PAYT','type':'general'})
        # Año reservado al ensayo para no colisionar con la versión real de la demo.
        self.policy=self.env['erpec.payroll.policy'].create({'name':'SINTETICA-1','year':2099,'journal_id':self.journal.id,'parameters':json.dumps(PARAMS),'authorization':'Ensayo local sin corte de SKNOMINA','source_reference':'Parámetros ficticios para pruebas'})
        for concept in ('gross','net','personal_iess','tax','advances','loans','other_deductions','employer_iess','thirteenth','fourteenth','vacation','reserve_iess'):
            self.env['erpec.payroll.mapping'].create({'policy_id':self.policy.id,'concept':concept,'debit_id':self.expense.id if concept not in ('net','personal_iess','tax','advances','loans','other_deductions') else False,'credit_id':self.liability.id if concept!='gross' else False})
        self.policy.action_activate()
        self.employee=self.env['hr.employee'].create({'name':'Persona ficticia','company_id':self.company.id})
        self.partner=self.env['res.partner'].create({'name':'Pago ficticio'})
        self.period=self.env['erpec.payroll.period'].create({'name':'ENSAYO-SEP','policy_id':self.policy.id,'month':9,'line_ids':[(0,0,{'employee_id':self.employee.id,'partner_id':self.partner.id,'start_date':'2025-01-01','wage':1200,'approved':True})]})

    def test_close_post_repeat_reverse_correct(self):
        self.period.action_calculate()
        self.assertEqual(self.period.line_ids.net,1072)
        self.assertEqual(self.period.line_ids.cost,1630)
        self.period.action_close(); self.period.action_post()
        move=self.period.move_id
        self.assertEqual(move.state,'posted');self.assertAlmostEqual(sum(move.line_ids.mapped('balance')),0)
        self.period.action_post();self.assertEqual(self.period.move_id,move)
        with self.assertRaises(ValidationError):
            self.period.line_ids.wage=1500
        with self.assertRaises(ValidationError):
            move.button_draft()
        with self.assertRaises(ValidationError):
            move.line_ids[0].debit=999
        self.period.action_reverse();reverse=self.period.reversal_id
        self.assertEqual(reverse.state,'posted')
        self.assertAlmostEqual(sum(move.line_ids.mapped('debit')),sum(reverse.line_ids.mapped('credit')))
        self.period.action_reverse();self.assertEqual(self.period.reversal_id,reverse)
        action=self.period.action_correct(); correction=self.env['erpec.payroll.period'].browse(action['res_id'])
        self.assertEqual(correction.version,2);self.assertEqual(correction.state,'draft')
        correction.line_ids.write({'wage':1300,'approved':True})
        correction.action_calculate();correction.action_close();correction.action_post()
        self.assertNotEqual(correction.move_id,move)
        self.assertEqual(self.period.line_ids.wage,1200)
        self.assertEqual(self.period.action_correct()['res_id'],correction.id)

    def test_approval_authority_mapping_and_tamper(self):
        self.period.line_ids.approved=False
        self.period.action_calculate()
        with self.assertRaises(ValidationError):self.period.action_close()
        self.period.action_reopen();self.period.line_ids.approved=True
        with self.assertRaises(ValidationError):self.policy.parameters='{}'
        with self.assertRaises(ValidationError):self.policy.mapping_ids[0].unlink()
        with self.assertRaises(ValidationError):self.period.write({'state':'posted'})
        with self.assertRaises(ValidationError):self.period.line_ids.write({'result':'{}'})
        with self.assertRaises(ValidationError),self.cr.savepoint():
            self.policy.copy({'name':'SINTETICA-2'}).action_activate()
        self.period.action_calculate();self.period.action_close();self.period.action_post()
        self.assertEqual(self.period.move_id.state,'posted')

    def test_decimal_proration_benefits_and_tax_rebate(self):
        data={'start_date':'2026-09-16','wage':1200,'hours_50':2,'hours_100':1,'night_hours':4,'bonus':20,'commission':10,'advances':25,'personal_expenses':1000}
        result=calculate(data,PARAMS,2026,9)
        self.assertEqual(result['days'],15);self.assertEqual(result['salary'],600)
        self.assertEqual(result['overtime'],30);self.assertEqual(result['base'],660)
        self.assertEqual(result['net'],569);self.assertEqual(result['reserve_iess'],0)
        data={'start_date':'2025-01-01','wage':2400,'personal_expenses':1000}
        result=calculate(data,PARAMS,2026,9)
        self.assertEqual(result['tax'],101)
        accrued=calculate({'start_date':'2025-01-01','wage':1200},PARAMS,2026,9)
        paid=calculate({'start_date':'2025-01-01','wage':1200,'monthly_thirteenth':True,'monthly_fourteenth':True,'reserve_paid':True},PARAMS,2026,9)
        self.assertEqual(paid['cost'],accrued['cost'])
        self.assertEqual(paid['thirteenth'],0);self.assertEqual(paid['reserve_iess'],0)
        for values in ({'wage':100},{'wage':float('nan')},{'advances':99999},{'hours_50':-1}):
            with self.assertRaises(ValueError):calculate({'start_date':'2025-01-01','wage':1200,**values},PARAMS,2026,9)

    def test_tax_treaty_exempt_and_capped_rate_override_the_progressive_table(self):
        # Caso 11 (DI25-03): convenio de doble imposición registrado (erpec.payroll.tax.treaty).
        plain = calculate({'start_date': '2025-01-01', 'wage': 4000, 'personal_expenses': 1000}, PARAMS, 2026, 9)
        self.assertGreater(plain['tax'], 0)
        exempt = calculate({'start_date': '2025-01-01', 'wage': 4000, 'personal_expenses': 1000, 'treaty_mechanism': 'exempt'}, PARAMS, 2026, 9)
        self.assertEqual(exempt['tax'], 0)
        self.assertEqual(exempt['annual_tax_caused'], 0)
        capped = calculate({'start_date': '2025-01-01', 'wage': 4000, 'personal_expenses': 1000, 'treaty_mechanism': 'capped_rate', 'treaty_rate': 10}, PARAMS, 2026, 9)
        self.assertEqual(capped['personal_expense_rebate'], 0)  # la rebaja no aplica bajo un tope de tratado
        self.assertNotEqual(capped['tax'], plain['tax'])

    def test_gross_up_assumed_tax_resolves_the_net_guarantee_by_bisection(self):
        # Caso 11 (DI25-03): impuesto asumido por "contrato de ingreso neto en nómina". La LRTI no
        # fija una tarifa única de gross-up; se resuelve por bisección contra la misma tabla
        # progresiva (annual_income_tax), tratándola como caja negra.
        from ..engine import gross_up_assumed_tax, annual_income_tax
        base_annual_base, net_target = 15000, 1000
        assumed = gross_up_assumed_tax(net_target, base_annual_base, 0, PARAMS)
        self.assertGreater(assumed, 0)
        _, _, base_tax = annual_income_tax(base_annual_base, 0, PARAMS)
        _, _, with_addition_tax = annual_income_tax(base_annual_base+net_target+assumed, 0, PARAMS)
        self.assertAlmostEqual(float(with_addition_tax-base_tax), float(assumed), places=2)
        self.assertEqual(gross_up_assumed_tax(0, base_annual_base, 0, PARAMS), 0)
        with self.assertRaises(ValueError):
            gross_up_assumed_tax(-1, base_annual_base, 0, PARAMS)

    def test_net_income_target_grosses_up_and_does_not_add_withholding_to_the_employee(self):
        # El neto garantizado llega íntegro (gross/net suben exactamente lo pactado); el impuesto
        # que asume el empleador es informativo y no se descuenta al trabajador (tax no cambia).
        plain = calculate({'start_date': '2025-01-01', 'wage': 3000}, PARAMS, 2026, 9)
        assumed = calculate({'start_date': '2025-01-01', 'wage': 3000, 'net_income_target': 500}, PARAMS, 2026, 9)
        self.assertAlmostEqual(assumed['gross']-plain['gross'], 500, places=2)
        self.assertAlmostEqual(assumed['net']-plain['net'], 500, places=2)
        self.assertAlmostEqual(assumed['tax'], plain['tax'], places=2)
        self.assertGreater(assumed['employer_assumed_tax'], 0)
        self.assertAlmostEqual(assumed['cost']-plain['cost'], 500+assumed['employer_assumed_tax'], places=2)
        with self.assertRaises(ValueError):
            calculate({'start_date': '2025-01-01', 'wage': 3000, 'net_income_target': -1}, PARAMS, 2026, 9)

    def test_vacation_payout_is_taxable_but_not_iess_material(self):
        # Caso 3 (DI25-03): la liquidación de vacaciones no gozadas grava impuesto a la renta
        # pero no IESS (catálogo RDEP vigente); se suma una sola vez a la base anual, como el
        # ingreso de otro empleador (D8), no como un devengo mensual recurrente.
        plain = calculate({'start_date': '2025-01-01', 'wage': 1200}, PARAMS, 2026, 9)
        paid = calculate({'start_date': '2025-01-01', 'wage': 1200, 'vacation_payout': 500}, PARAMS, 2026, 9)
        self.assertEqual(paid['gross'] - plain['gross'], 500)
        self.assertEqual(paid['personal_iess'], plain['personal_iess'])
        self.assertGreater(paid['tax'], plain['tax'])
        with self.assertRaises(ValueError):
            calculate({'start_date': '2025-01-01', 'wage': 1200, 'vacation_payout': -1}, PARAMS, 2026, 9)

    def test_company_permissions_and_views(self):
        user=self.env['res.users'].with_context(no_reset_password=True).create({'name':'Operador sin nómina','login':'payroll_no_access','company_id':self.company.id,'company_ids':[(6,0,self.company.ids)],'groups_id':[(6,0,[self.env.ref('base.group_user').id])]})
        with self.assertRaises(AccessError):self.period.with_user(user).action_calculate()
        other=self.env['res.company'].create({'name':'DEMO otra empresa'})
        self.employee.company_id=other
        with self.assertRaises(ValidationError):self.period.action_calculate()
        for model in ('erpec.payroll.period','erpec.payroll.policy'):
            self.assertTrue(self.env[model].get_view(view_type='form')['arch'])


    def test_official_2026_parameters_and_expense_limit(self):
        from ..parameters_ec2026 import PARAMS as official
        result=calculate({'start_date':'2025-01-01','wage':1200},official,2026,9)
        self.assertEqual(result['personal_iess'],113.4)
        self.assertEqual(result['employer_iess'],133.8)
        self.assertEqual(result['reserve_iess'],99.96)
        self.assertEqual(result['fourteenth'],40.17)
        self.assertEqual(result['tax'],3.46)
        self.assertEqual(result['net'],1083.14)
        self.assertEqual(result['employer_other'],12)
        self.assertEqual(result['cost'],1635.93)
        low=calculate({'start_date':'2025-01-01','wage':482},official,2026,9)
        self.assertEqual(low['personal_iess'],45.55);self.assertEqual(low['tax'],0)
        high=calculate({'start_date':'2025-01-01','wage':2400,'personal_expenses':1000},official,2026,9)
        self.assertEqual(high['tax'],96.49)
        with self.assertRaises(ValueError):calculate({'start_date':'2025-01-01','wage':481},official,2026,9)

    def test_personal_expense_cap_function(self):
        # Boletín NAC-COM-26-006 (SRI): tope único total por cargas familiares,
        # multiplicado por 1.803 en Galápagos; sin cargas ni Galápagos, sin cambios.
        from ..engine import personal_expense_cap
        self.assertEqual(float(personal_expense_cap(5752.60, 0, 'NO')), 5752.60)
        self.assertAlmostEqual(float(personal_expense_cap(5752.60, 1, 'NO')), 5752.60/7*9, places=2)
        self.assertAlmostEqual(float(personal_expense_cap(5752.60, 4, 'NO')), 5752.60/7*17, places=2)
        self.assertAlmostEqual(float(personal_expense_cap(5752.60, 5, 'NO')), 5752.60/7*20, places=2)
        self.assertAlmostEqual(float(personal_expense_cap(5752.60, 9, 'NO')), 5752.60/7*20, places=2)
        self.assertAlmostEqual(float(personal_expense_cap(5752.60, 0, 'SI')), 5752.60*1.803, places=2)
        with self.assertRaises(ValueError):
            personal_expense_cap(5752.60, -1, 'NO')

    def test_official_2026_expense_cap_scales_monthly_withholding(self):
        # El motor mensual debe usar el mismo tope escalado que el anexo RDEP
        # (erpec_payroll.engine.personal_expense_cap), no solo el tope de 0 cargas.
        from ..parameters_ec2026 import PARAMS as official
        baseline = calculate({'start_date': '2025-01-01', 'wage': 4000, 'personal_expenses': 6500}, official, 2026, 9)
        with_dependents = calculate({'start_date': '2025-01-01', 'wage': 4000, 'personal_expenses': 6500, 'dependents_count': 1}, official, 2026, 9)
        self.assertLess(with_dependents['tax'], baseline['tax'])
        # Caso 11 (18.0.1.14.12): Galápagos ya no solo escala el tope de gastos personales, sino
        # también el salario (misma reforma LOREG/IPCEG, ver D5); con el mismo wage de entrada
        # (salario de referencia continental) el ingreso real es mayor, así que paga más impuesto
        # pese al tope de gastos más alto. Se aísla el efecto puro del tope en
        # test_personal_expense_cap_function, que no toca el salario.
        galapagos = calculate({'start_date': '2025-01-01', 'wage': 4000, 'personal_expenses': 6500, 'galapagos': 'SI'}, official, 2026, 9)
        self.assertGreater(galapagos['tax'], baseline['tax'])
        self.assertAlmostEqual(galapagos['salary'], baseline['salary']*1.803, places=2)
        explicit_zero = calculate({'start_date': '2025-01-01', 'wage': 4000, 'personal_expenses': 6500, 'dependents_count': 0, 'galapagos': 'NO'}, official, 2026, 9)
        self.assertEqual(explicit_zero['tax'], baseline['tax'])
