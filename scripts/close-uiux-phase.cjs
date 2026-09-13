// Cierra el incremento UI/UX sin alterar la cronología histórica del ERP.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const cp = require('child_process');
const root = path.resolve(__dirname, '..');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const phase = process.argv[2];
if (!['00', '01', '02', '03'].includes(phase)) throw Error('Fase UI/UX inválida');
const lockPath = path.join(root, '.vscode/AuditLock.json');
const raw = fs.readFileSync(lockPath);
const previous = JSON.parse(raw);
const reportPath = `docs/evidencias/ERPEC26-UIUX-${phase}.json`;
const report = JSON.parse(fs.readFileSync(path.join(root, reportPath), 'utf8'));
if (report.status !== 'passed' || !report.checks?.length) throw Error('Faltan comprobaciones aprobadas');
if (phase !== '00' && previous.uiUx?.phaseCompleted !== `ERPEC26-UIUX-${String(Number(phase) - 1).padStart(2, '0')}`) throw Error('Dependencia UI/UX no cerrada');
const previousBytes = fs.readFileSync(path.join(root, previous.previousAuditLockSnapshot));
if (hash(previousBytes) !== previous.previousAuditLockHash || hash(Buffer.concat([previousBytes, Buffer.from(previous.updatedAt)])) !== previous.signature) throw Error('Cadena previa inválida');
const snapshot = `docs/evidencias/AuditLock.before-UIUX-${phase}.json`;
if (fs.existsSync(path.join(root, snapshot))) throw Error('El cierre ya existe; no sobrescribir historia');
const updatedAt = new Date().toISOString();
const files = cp.execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard'], {cwd: root, encoding: 'utf8'}).trim().split(/\r?\n/);
// El lock de este incremento acredita su alcance, no cambios concurrentes de otros planes.
const scoped = file => ['.github/CODEX_CONTEXT.md', 'docs/PLAN_HAIKY_UI_UX.md',
    'scripts/close-uiux-phase.cjs', 'scripts/install-fiscal-native-demo.py'].includes(file) ||
    ['addons/erpec_workspace/', '.github/prompts/ERPEC26-UIUX-', 'docs/evidencias/ERPEC26-UIUX',
     'docs/evidencias/AuditLock.before-UIUX-'].some(prefix => file.startsWith(prefix));
const unique = [...new Set([...files, snapshot])].filter(scoped).sort();
const fileHashes = {};
for (const file of unique) {
    const bytes = file === snapshot ? raw : fs.readFileSync(path.join(root, file));
    const text = bytes.toString('utf8');
    if (!Buffer.from(text, 'utf8').equals(bytes) || text.startsWith('\ufeff')) throw Error('Codificación inválida: ' + file);
    fileHashes[file] = hash(bytes);
}
const lock = {...previous, updatedAt, filesModified: unique, fileHashes,
    uiUx: {phaseCompleted: `ERPEC26-UIUX-${phase}`, status: phase === '03' ? 'completed-pass' : 'increment-passed', evidence: reportPath},
    validationChecks: report.checks, previousAuditLockSnapshot: snapshot, previousAuditLockHash: hash(raw),
    signature: hash(Buffer.concat([raw, Buffer.from(updatedAt, 'utf8')]))};
const text = JSON.stringify(lock, null, 2) + '\n';
if (Buffer.from(text, 'utf8').toString('utf8') !== text) throw Error('UTF-8 inválido');
fs.writeFileSync(path.join(root, snapshot), raw);
fs.writeFileSync(lockPath, text, 'utf8');
console.log('Cierre UI/UX registrado:', phase);
