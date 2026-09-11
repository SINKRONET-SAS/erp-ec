/* Contrasta funciones puras inspeccionadas; no ejecuta servicios ni modifica SKNOMINA. */
const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');const crypto=require('node:crypto');const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const sourcePath='C:/proyectos web/nuevo_nomina/backend/src/services/calculoNominaService.js';
const source=fs.readFileSync(sourcePath,'utf8');
function extract(name){
 const start=source.indexOf('function '+name+'(');
 if(start<0)throw new Error('No se encontró la función de referencia: '+name);
 const next=source.indexOf('\nfunction ',start+1);
 const end=next<0?source.indexOf('\nmodule.exports',start):next;
 if(end<start)throw new Error('No se encontró el límite de la función: '+name);
 return source.slice(start,end);
}
const names=['calcularDiasTrabajados','calcularValorHora','getEmployeeMonthlyHours','calcularIR'];
const context=vm.createContext({roundMoney:value=>Math.round((value+Number.EPSILON)*100)/100,AppError:Error});
vm.runInContext(names.map(extract).join('\n'),context,{timeout:1000});
const python=`import importlib.util,json
from datetime import date
from pathlib import Path
spec=importlib.util.spec_from_file_location('engine','addons/erpec_payroll/engine.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
`;
// La tabla sintética se transmite explícitamente; no se importan fixtures de Odoo.
const params={minimum_salary:480,monthly_hours:240,personal_rate:.1,employer_rate:.12,reserve_rate:.08,reserve_months:12,thirteenth_rate:1/12,fourteenth_rate:1/12,vacation_rate:1/24,tax_brackets:[{from:0,to:12000,base:0,rate:0},{from:12000,to:null,base:0,rate:.1}],expense_limit:5000,rebate_rate:.18,overtime_50:1.5,overtime_100:2,night_rate:.25};
const code=python+`params=json.loads(${JSON.stringify(JSON.stringify(params))})\ndates=['2025-01-01','2026-09-16','2026-10-01','2026-08-31']\nprint(json.dumps({'days':[module.days_worked(date.fromisoformat(value),2026,9) for value in dates],'noExpenses':module.calculate({'start_date':'2025-01-01','wage':2400,'hours_50':0},params,2026,9),'withExpenses':module.calculate({'start_date':'2025-01-01','wage':2400,'personal_expenses':1000},params,2026,9),'hour':module.calculate({'start_date':'2025-01-01','wage':2400,'hours_50':1},params,2026,9)['overtime']/1.5}))`;
const native=JSON.parse(execFileSync(path.join(root,'.venv/Scripts/python.exe'),['-c',code],{cwd:root,encoding:'utf8'}));
const dates=['2025-01-01','2026-09-16','2026-10-01','2026-08-31'];
const sourceDays=dates.map(value=>context.calcularDiasTrabajados(value,2026,9));
if(JSON.stringify(sourceDays)!==JSON.stringify(native.days))throw new Error('Diferencia de prorrateo');
if(context.calcularValorHora({sueldo_bruto_mensual:2400},{monthlyWorkHours:240})!==native.hour)throw new Error('Diferencia de valor hora');
const legal={payroll:{personalExpenseDeductionLimit:5000},incomeTax:params.tax_brackets.map(value=>({...value,baseTax:value.base}))};
const sourceNoExpenses=context.calcularIR(2160,legal,0);
if(sourceNoExpenses!==native.noExpenses.tax)throw new Error('Diferencia de renta sin gastos');
const sourceExpenses=context.calcularIR(2160,legal,1000);
if(sourceExpenses!==107.67||native.withExpenses.tax!==101)throw new Error('Cambió el caso documentado de rebaja');
const report={sourcePath,sourceSha256:crypto.createHash('sha256').update(source).digest('hex'),testedFunctions:names,matchingCases:6,days:sourceDays,hour:native.hour,taxWithoutExpenses:sourceNoExpenses,intentionalDifference:{syntheticParameters:true,sourceExpenseTreatment:sourceExpenses,nativeExpenseTreatment:native.withExpenses.tax},fullPayrollEquivalent:false,sourceModified:false};
const text=JSON.stringify(report,null,2)+'\n';if(Buffer.from(text,'utf8').toString('utf8')!==text)throw new Error('Codificación inválida');
fs.writeFileSync(path.join(root,'.cache/windows/payroll-equivalence-result.json'),text);console.log(text);
