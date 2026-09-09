const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const root = path.resolve(__dirname, '..');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
function read(relative) {
  const absolute = path.resolve(root, relative);
  if (!absolute.startsWith(root + path.sep)) throw Error('Ruta fuera del repositorio: ' + relative);
  return fs.readFileSync(absolute);
}
try {
  const lock = JSON.parse(read('.vscode/AuditLock.json'));
  const previous = read(lock.previousAuditLockSnapshot);
  if (hash(previous) !== lock.previousAuditLockHash) throw Error('Hash del predecesor inválido');
  if (hash(Buffer.concat([previous, Buffer.from(lock.updatedAt, 'utf8')])) !== lock.signature) throw Error('Firma inválida');
  if (!lock.validationChecks.length || !lock.filesModified.length) throw Error('Lock sin evidencia');
  for (const file of lock.filesModified) {
    const bytes = read(file), text = bytes.toString('utf8');
    if (!bytes.equals(Buffer.from(text, 'utf8')) || text.startsWith('\ufeff')) throw Error('Codificación inválida: ' + file);
    if (hash(bytes) !== lock.fileHashes[file]) throw Error('Entregable modificado sin actualizar evidencia: ' + file);
  }
  for (let index = 0; index <= 8; index++) read('.github/prompts/ERPEC26-' + String(index).padStart(2, '0') + '.md');
  console.log('Gobierno ERPEC26 válido: cadena, entregables UTF-8 y nueve prompts. No valida implementación funcional.');
} catch (error) {
  console.error('Falló la validación de gobierno:', error.message);
  process.exitCode = 1;
}
