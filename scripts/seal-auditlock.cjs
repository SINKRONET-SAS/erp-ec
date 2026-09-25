// Sella un nuevo eslabón del AuditLock (RULES.md §6 y §13): archiva los bytes exactos del lock anterior,
// registra su SHA256, firma SHA256(bytes anteriores + updatedAt) y recalcula los hashes de entregables.
// Uso: node scripts/seal-auditlock.cjs <etiqueta> <cambios.json>
//   cambios.json: {"checks": [...], "pendingAdd": [...], "pendingDropPrefix": [...],
//                  "requiredPromptsAdd": [...], "set": {"bloque": {"clave": valor}}}
// Los binarios (png, pdf, xls, xlsx) se registran por manifiesto, no aquí.
const fs = require('fs'), path = require('path'), crypto = require('crypto'), cp = require('child_process');

const root = path.resolve(__dirname, '..');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const EXCLUDED_SUFFIXES = ['.png', '.pdf', '.xls', '.xlsx'];
const EXCLUDED_FILES = new Set(['.vscode/AuditLock.json', 'addons/erpec_fiscal_native/xsd/at.xsd', 'docs/evidencias/AuditLock.before-CF01.json']);

function writeUtf8(relative, text) {
  if (Buffer.from(text, 'utf8').toString('utf8') !== text) throw Error('UTF-8 inválido: ' + relative);
  fs.writeFileSync(path.join(root, relative), text, 'utf8');
}

function changedFiles() {
  const status = cp.execFileSync('git', ['status', '--porcelain', '-uall'], {cwd: root, encoding: 'utf8'});
  return status.split(/\r?\n/).filter(Boolean)
    .map(line => line.slice(3).trim().replace(/^"|"$/g, ''))
    .map(entry => entry.includes(' -> ') ? entry.split(' -> ')[1] : entry)
    .filter(file => !EXCLUDED_FILES.has(file) && !file.includes('__pycache__')
      && !EXCLUDED_SUFFIXES.some(suffix => file.toLowerCase().endsWith(suffix)));
}

function main() {
  const [label, changesPath] = process.argv.slice(2);
  if (!label || !/^[A-Z0-9-]+$/.test(label) || !changesPath) {
    throw Error('Uso: node scripts/seal-auditlock.cjs ETIQUETA-EN-MAYUSCULAS cambios.json');
  }
  const changes = JSON.parse(fs.readFileSync(changesPath, 'utf8'));
  if (!Array.isArray(changes.checks) || !changes.checks.length) throw Error('El sellado exige al menos una validación realizada en "checks".');
  const raw = fs.readFileSync(path.join(root, '.vscode/AuditLock.json'));
  const previous = JSON.parse(raw);
  const updatedAt = new Date().toISOString();
  const stamp = updatedAt.replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
  const snapshot = 'docs/evidencias/AuditLock.before-' + label + '-' + stamp + '.json';
  writeUtf8(snapshot, raw.toString('utf8'));

  const changed = changedFiles();
  const files = [...new Set([...previous.filesModified, ...changed, snapshot])]
    .filter(file => !EXCLUDED_FILES.has(file)).sort();
  const fileHashes = {};
  for (const file of files) {
    const absolute = path.join(root, file);
    if (!fs.existsSync(absolute)) throw Error('Entregable listado inexistente: ' + file);
    fileHashes[file] = hash(fs.readFileSync(absolute));
  }
  const drop = changes.pendingDropPrefix || [];
  const pendingChecks = [...previous.pendingChecks.filter(item => !drop.some(prefix => item.startsWith(prefix))), ...(changes.pendingAdd || [])];
  const lock = {
    ...previous, updatedAt, filesModified: files,
    validationChecks: [...previous.validationChecks, ...changes.checks], pendingChecks, fileHashes,
    previousAuditLockSnapshot: snapshot, previousAuditLockHash: hash(raw),
    signature: hash(Buffer.concat([raw, Buffer.from(updatedAt, 'utf8')])),
  };
  if (changes.requiredPromptsAdd) lock.requiredPrompts = [...new Set([...(previous.requiredPrompts || []), ...changes.requiredPromptsAdd])];
  for (const [block, values] of Object.entries(changes.set || {})) lock[block] = {...(previous[block] || {}), ...values};
  writeUtf8('.vscode/AuditLock.json', JSON.stringify(lock, null, 2) + '\n');
  console.log('AuditLock sellado: ' + snapshot + ' | entregables ' + files.length + ' | modificados ' + changed.length);
}

try {
  main();
} catch (error) {
  console.error('No se selló el AuditLock:', error.message);
  process.exitCode = 1;
}
