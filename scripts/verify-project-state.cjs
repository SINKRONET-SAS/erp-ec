const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const entries = ['README.md', 'docs/MATRIZ_CAPACIDADES.md', 'docs/ARQUITECTURA_Y_CONTRATOS.md', 'docs/FACTURACION_LOCAL.md'];

// Comprueba las entradas vigentes; las evidencias históricas conservan su contexto temporal.
function verifyProjectState(read = file => fs.readFileSync(path.join(root, file))) {
  const text = file => {
    const bytes = read(file), decoded = bytes.toString('utf8');
    if (!bytes.equals(Buffer.from(decoded, 'utf8')) || decoded.startsWith('\ufeff')) throw Error('UTF-8 inválido: ' + file);
    return decoded;
  };
  let links = 0;
  for (const file of entries) {
    const content = text(file);
    for (const match of content.matchAll(/\[[^\]]*\]\(([^\s)]+)\)/g)) {
      const target = match[1].split('#')[0];
      if (!target || /^(https?:|mailto:)/.test(target)) continue;
      const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(file), target));
      if (resolved.startsWith('../') || target.includes('\\') || /^[A-Za-z]:|^\//.test(target)) throw Error('Enlace fuera del repositorio: ' + target);
      try { read(resolved); } catch (error) { throw Error('Enlace local ausente en ' + file + ': ' + resolved, {cause: error}); }
      links++;
    }
  }
  const pin = JSON.parse(text('upstream.json'));
  const audit = JSON.parse(text('docs/evidencias/community-audit.json'));
  if (!/^[a-f0-9]{40}$/.test(pin.commit) || pin.commit !== audit.revision) throw Error('Pin Community y auditoría divergentes');
  for (const name of ['l10n_ec', 'l10n_ec_stock', 'l10n_ec_website_sale']) {
    if (audit.requiredModules?.[name]?.license !== 'LGPL-3') throw Error('Localización Community no acreditada: ' + name);
  }
  return {links, revision: pin.commit};
}
module.exports = {verifyProjectState};
if (require.main === module) {
  try { const result = verifyProjectState(); console.log('Coherencia documental válida: ' + result.links + ' enlaces, pin ' + result.revision + '. No valida funcionamiento.'); }
  catch (error) { console.error('Falló la coherencia documental:', error.message); process.exitCode = 1; }
}
