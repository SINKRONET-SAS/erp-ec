// Contraste de función pura; no carga ni modifica el servicio Facturador.
const fs=require('fs'),vm=require('vm'),cp=require('child_process'),crypto=require('crypto'),path=require('path');
const root=path.resolve(__dirname,'..');const source='C:/proyectos web/sinkroniq-mobile/backend/src/services/sri/claveAccesoService.js';
const bytes=fs.readFileSync(source),text=bytes.toString('utf8');const start=text.indexOf('function calcularModulo11('),end=text.indexOf('// ── generarClaveAcceso',start);
if(start<0||end<0)throw Error('No se encontró la función pura esperada');
const sandbox={};vm.runInNewContext(text.slice(start,end)+';this.calculate=calcularModulo11;',sandbox,{timeout:1000});
const cases=['0'.repeat(48),'6'.padStart(48,'0'),...Array.from({length:256},(_,i)=>crypto.createHash('sha256').update('ec-native-'+i).digest('hex').split('').map(c=>parseInt(c,16)%10).join('').slice(0,48))];
const expected=cases.map(sandbox.calculate);const py="import importlib.util,json,sys; s=importlib.util.spec_from_file_location('engine','addons/erpec_fiscal_native/engine.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(json.dumps([m.modulo11(x) for x in json.load(sys.stdin)]))";
const actual=JSON.parse(cp.execFileSync(path.join(root,'.venv/Scripts/python.exe'),['-c',py],{cwd:root,input:JSON.stringify(cases),encoding:'utf8'}));
if(JSON.stringify(expected)!==JSON.stringify(actual))throw Error('Diferencia en módulo 11');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');if(hash(fs.readFileSync(source))!==hash(bytes))throw Error('La fuente cambió durante el contraste');
const report={checkedAt:new Date().toISOString(),source,sourceSha256:hash(bytes),cases:cases.length,passed:true,scope:'Módulo 11 exclusivamente. No acredita equivalencia XML, firma, autorización ni emisión.',sourceModified:false};const output=JSON.stringify(report,null,2)+'\n';if(Buffer.from(output,'utf8').toString('utf8')!==output)throw Error('UTF-8');fs.writeFileSync(path.join(root,'.cache/windows/fiscal-native-equivalence.json'),output);console.log('Módulo 11 contrastado: '+cases.length+' casos, sin modificar Facturador');
