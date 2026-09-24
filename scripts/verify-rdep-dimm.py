"""Valida un XML RDEP con la clase oficial ValidacionEsquema del plug-in RDEP del DIMM (jpype, Java 8, sin interfaz grafica), contra rdepv10.xsd.
Uso: python scripts/verify-rdep-dimm.py ruta.xml. Tambien genera un negativo (numRuc invalido) junto al XML para probar que el validador rechaza."""
import sys, glob, tempfile, zipfile
from pathlib import Path
import jpype
DIMM = Path(r'C:\SRI-DIMM\Dimm\plugins')
JVM = sorted(glob.glob(r'C:\Program Files\Java\jre1.8.0_*\bin\server\jvm.dll'), reverse=True)[0]
tmp = Path(tempfile.mkdtemp(prefix='rdep-libs-'))
cp = []
for plugin in DIMM.iterdir():
    if plugin.is_file() and plugin.suffix == '.jar':
        cp.append(str(plugin))
        with zipfile.ZipFile(plugin) as z:
            for n in z.namelist():
                if n.startswith('lib/') and n.endswith('.jar'):
                    t = tmp / (plugin.name + '__' + Path(n).name)
                    t.write_bytes(z.read(n)); cp.append(str(t))
    elif plugin.is_dir():
        cp.append(str(plugin))
        for jar in plugin.glob('lib/*.jar'):
            cp.append(str(jar))
seen = set(); final = []
for c in cp:
    if c not in seen: seen.add(c); final.append(c)
jpype.startJVM(JVM, '-Djava.class.path=' + ';'.join(final), convertStrings=True)
from jpype import JClass
File = JClass('java.io.File'); FileInputStream = JClass('java.io.FileInputStream')
xml = sys.argv[1]
def show(title, coll):
    print('==', title)
    try:
        items = list(coll)
    except Exception as e:
        print('  (no iterable)', coll); return
    print('  total', len(items))
    for it in items[:25]:
        print('  -', str(it)[:300])
VE = JClass('ec.gov.sri.dimm.rdep.validacion.validador.esquema.ValidacionEsquema')
xsd = r'C:/SRI-DIMM/Dimm/plugins/ec.gov.sri.dimm.rdep.validacion_3.13.0/schemas/rdepv10.xsd'
try:
    r = VE.validarEsquema(FileInputStream(File(xml)), FileInputStream(File(xsd)), 10)
    print('validarEsquema ->', r)
    for m in r.getClass().getMethods():
        n = str(m.getName())
        if n.startswith('get') or n.startswith('is') or n.startswith('esV'):
            try:
                if m.getParameterCount() == 0: print('  ', n, '=', str(m.invoke(r))[:300])
            except Exception as e: pass
except Exception as e:
    print('esquema ERR', type(e).__name__, str(e)[:500])
# negativo: XML corrupto para demostrar que el validador detecta errores
bad = xml.replace('.xml', '-bad.xml')
open(bad, 'w', encoding='utf-8').write(open(xml, encoding='utf-8').read().replace('<numRuc>1793235327001</numRuc>', '<numRuc>abc</numRuc>'))
r = VE.validarEsquema(FileInputStream(File(bad)), FileInputStream(File(xsd)), 10)
print('negativo ->', r); print('MSG', [str(x.getMensaje()) if hasattr(x,'getMensaje') else str(x) for x in r.getMensajes()])
for m in r.getClass().getMethods():
    n = str(m.getName())
    if (n.startswith('get') or n.startswith('is')) and m.getParameterCount() == 0 and n != 'getClass':
        try: print('  ', n, '=', str(m.invoke(r))[:400])
        except Exception: pass
