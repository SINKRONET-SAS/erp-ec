const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {verifyGovernance, safePath} = require('./verify-governance.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const encode = x => Buffer.from(JSON.stringify(x));
function fixture() {
  const files = new Map();
  const genesis = 'docs/evidencias/AuditLock.genesis.json';
  files.set(genesis, encode({status:'genesis',phaseCompleted:null}));
  const previous = 'docs/evidencias/previous.json';
  const link = name => ({updatedAt:'2026-09-21T00:00:00Z', previousAuditLockSnapshot:name,
    previousAuditLockHash:hash(files.get(name)),
    signature:hash(Buffer.concat([files.get(name), Buffer.from('2026-09-21T00:00:00Z')]))});
  files.set(previous, encode(link(genesis)));
  files.set('example.md',Buffer.from('Ejemplo'));
  files.set('.vscode/AuditLock.json', encode({...link(previous),filesModified:['example.md'],
    fileHashes:{'example.md':hash(files.get('example.md'))},validationChecks:['ensayo'],diagnosticImprovement:{}}));
  for(let i=0;i<9;i++) files.set('.github/prompts/ERPEC26-'+String(i).padStart(2,'0')+'.md',Buffer.from('Prompt'));
  for(let i=0;i<8;i++) files.set('.github/prompts/ERPEC26-DI25-'+String(i).padStart(2,'0')+'.md',Buffer.from('Prompt'));
  const read = p => {if(!files.has(p))throw Error('Ausente: '+p);return files.get(p);};
  return {files,read};
}
test('recorre todos los enlaces y exige prompts DI25',()=>{assert.deepEqual(verifyGovernance(fixture().read),{links:2,prompts:17});});
test('rechaza alteración de un ancestro',()=>{const x=fixture();x.files.set('docs/evidencias/AuditLock.genesis.json',Buffer.from('{}'));assert.throws(()=>verifyGovernance(x.read),/predecesor/);});
test('rechaza entregable alterado',()=>{const x=fixture();x.files.set('example.md',Buffer.from('Cambio'));assert.throws(()=>verifyGovernance(x.read),/Entregable/);});
test('rechaza prompt faltante',()=>{const x=fixture();x.files.delete('.github/prompts/ERPEC26-DI25-07.md');assert.throws(()=>verifyGovernance(x.read),/Ausente/);});
test('rechaza rutas externas y separadores alternativos',()=>{for(const p of ['../secreto','C:/secreto','docs/../secreto','docs\\..\\secreto'])assert.throws(()=>safePath(p));});
test('rechaza enlace circular incluso sin firma válida',()=>{const x=fixture();const p='.vscode/AuditLock.json';const l=JSON.parse(x.files.get(p));l.previousAuditLockSnapshot=p;x.files.set(p,encode(l));assert.throws(()=>verifyGovernance(x.read),/predecesor|Ciclo/);});
