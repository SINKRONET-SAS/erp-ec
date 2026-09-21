const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const root = path.resolve(__dirname, '..');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');

function safePath(relative) {
  if (typeof relative !== 'string' || /^[A-Za-z]:/.test(relative) || relative.includes('\\') || relative.split('/').includes('..') || path.isAbsolute(relative)) {
    throw Error('Ruta de gobierno no permitida: ' + relative);
  }
  const absolute = path.resolve(root, relative);
  if (!absolute.startsWith(root + path.sep)) throw Error('Ruta fuera del repositorio: ' + relative);
  return absolute;
}

function read(relative) {
  const absolute = safePath(relative);
  if (process.argv.includes('--git')) {
    return require('child_process').execFileSync('git', ['show', 'HEAD:' + relative], { cwd: root });
  }
  if (!fs.realpathSync(absolute).startsWith(fs.realpathSync(root) + path.sep)) throw Error('Enlace fuera del repositorio');
  return fs.readFileSync(absolute);
}

function verifyGovernance(reader = read) {
  const readSafe = relative => { safePath(relative); return reader(relative); };
  const decode = (bytes, name) => {
    const text = bytes.toString('utf8');
    if (!bytes.equals(Buffer.from(text, 'utf8')) || text.startsWith('\ufeff')) throw Error('Codificación inválida: ' + name);
    return JSON.parse(text);
  };
  const current = decode(readSafe('.vscode/AuditLock.json'), '.vscode/AuditLock.json');
  let lock = current;
  let location = '.vscode/AuditLock.json';
  const visited = new Set();
  let links = 0;
  while (true) {
    if (visited.has(location)) throw Error('Ciclo en la cadena de gobierno');
    visited.add(location);
    if (lock.status === 'genesis') {
      if (location !== 'docs/evidencias/AuditLock.genesis.json' || lock.phaseCompleted !== null || lock.previousAuditLockSnapshot) {
        throw Error('Génesis inválido');
      }
      break;
    }
    if (typeof lock.updatedAt !== 'string' || !Number.isFinite(Date.parse(lock.updatedAt))) throw Error('Fecha inválida');
    const previous = readSafe(lock.previousAuditLockSnapshot);
    if (hash(previous) !== lock.previousAuditLockHash) throw Error('Hash del predecesor inválido: ' + location);
    if (hash(Buffer.concat([previous, Buffer.from(lock.updatedAt, 'utf8')])) !== lock.signature) throw Error('Firma inválida: ' + location);
    location = lock.previousAuditLockSnapshot;
    lock = decode(previous, location);
    links++;
  }
  if (!current.validationChecks?.length || !current.filesModified?.length) throw Error('Lock sin evidencia');
  // Solo los entregables actuales se contrastan con disco: los históricos pueden tener versiones posteriores.
  for (const file of current.filesModified) {
    const bytes = readSafe(file), text = bytes.toString('utf8');
    if (!bytes.equals(Buffer.from(text, 'utf8')) || text.startsWith('\ufeff')) throw Error('Codificación inválida: ' + file);
    if (hash(bytes) !== current.fileHashes[file]) throw Error('Entregable modificado sin actualizar evidencia: ' + file);
  }
  const prompts = Array.from({length: 9}, (_, i) => '.github/prompts/ERPEC26-' + String(i).padStart(2, '0') + '.md');
  if (current.diagnosticImprovement) {
    prompts.push(...Array.from({length: 8}, (_, i) => '.github/prompts/ERPEC26-DI25-' + String(i).padStart(2, '0') + '.md'));
  }
  for (const prompt of new Set([...prompts, ...(current.requiredPrompts || [])])) readSafe(prompt);
  return {links, prompts: new Set([...prompts, ...(current.requiredPrompts || [])]).size};
}
module.exports = {verifyGovernance, safePath};
if (require.main === module) {
  try {
    const result = verifyGovernance();
    console.log('Gobierno válido: ' + result.links + ' eslabones hasta génesis, entregables UTF-8 y ' + result.prompts + ' prompts. No valida funcionamiento.');
  } catch (error) {
    console.error('Falló la validación de gobierno:', error.message);
    process.exitCode = 1;
  }
}
