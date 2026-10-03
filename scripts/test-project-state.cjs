const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {verifyProjectState} = require('./verify-project-state.cjs');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file));
const override = (file, value) => name => name === file ? Buffer.from(value) : read(name);

test('comprueba las entradas reales y el pin auditado', () => assert.ok(verifyProjectState().links > 0));
test('rechaza el enlace histórico roto al contexto', () => assert.throws(() => verifyProjectState(override('README.md', '[Contexto](.github/CODEX/_CONTEXT.md)')), /Enlace local ausente/));
test('rechaza enlaces que salen del repositorio', () => assert.throws(() => verifyProjectState(override('README.md', '[Fuera](../fuera.md)')), /fuera del repositorio/));
test('rechaza divergencia entre revisión y evidencia', () => {
  const pin = JSON.parse(read('upstream.json')); pin.commit = 'a'.repeat(40);
  assert.throws(() => verifyProjectState(override('upstream.json', JSON.stringify(pin))), /divergentes/);
});
test('rechaza licencia restringida en localización auditada', () => {
  const audit = JSON.parse(read('docs/evidencias/community-audit.json')); audit.requiredModules.l10n_ec.license = 'OPL-1';
  assert.throws(() => verifyProjectState(override('docs/evidencias/community-audit.json', JSON.stringify(audit))), /no acreditada/);
});
test('rechaza BOM en documentación vigente', () => assert.throws(() => verifyProjectState(override('README.md', '\ufeffTexto')), /UTF-8 inválido/));
