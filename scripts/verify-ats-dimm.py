"""DI25-04.3: valida un XML del ATS contra el motor oficial del DIMM del SRI (validarEsquema +
validarInformacion), no solo contra el esquema XSD que ya tenemos bundleado. Herramienta manual
bajo demanda -- requiere una instalación local del DIMM (Java 8 + DIMM base + plug-in ATS,
descargados de sri.gob.ec) que NO forma parte de este repositorio ni de CI: es software de
terceros (SRI) con su propia licencia, y la ruta/versión varía por máquina.

Cómo funciona: las clases de validación del DIMM (ec.gob.sri.dimm.ats.validacion.ValidacionATS)
viven dentro de bundles OSGi cuyo classpath real está anidado en un `lib/` interno de cada jar del
plugin (ver `Bundle-ClassPath` en su MANIFEST.MF); un `-cp` plano sobre los jars de nivel superior
no basta. Este script extrae esos jars anidados a una carpeta temporal (no al repositorio: son
binarios de terceros con su propia licencia) y arranca una JVM embebida vía jpype para invocar la
API real de validación, sin necesitar la interfaz gráfica del DIMM ni un compilador Java (`javac`)
-- ninguno de los dos está garantizado en la máquina de quien lo ejecute.

Uso:
    .venv/Scripts/python.exe -X utf8 scripts/verify-ats-dimm.py <archivo.xml> [--dimm RUTA] [--jre RUTA]

Por defecto busca el DIMM en C:\\SRI-DIMM\\Dimm y el JRE 8 del sistema en
C:\\Program Files\\Java\\jre1.8.0_*\\bin\\server\\jvm.dll (toma la versión más reciente si hay varias).
Requiere `pip install "jpype1<1.6"` en el entorno (las versiones 1.6+ exigen Java 9+; el DIMM está
compilado contra JavaSE-1.6 y este JRE es Java 8).

No declara presentación ante el SRI por pasar esta validación: valida estructura y reglas de
negocio del DIMM, no sustituye el canal oficial de envío ni acredita aceptación tributaria.
"""
import argparse
import glob
import sys
import tempfile
import zipfile
from pathlib import Path


def find_default_jre(root=r'C:\Program Files\Java'):
    candidates = sorted(glob.glob(str(Path(root) / 'jre1.8.0_*' / 'bin' / 'server' / 'jvm.dll')), reverse=True)
    if not candidates:
        candidates = sorted(glob.glob(str(Path(root) / 'jre1.8.0_*' / 'bin' / 'client' / 'jvm.dll')), reverse=True)
    return candidates[0] if candidates else None


def extract_nested_jars(dimm_plugins_dir, out_dir):
    """Los plug-in del DIMM son bundles OSGi con su classpath real anidado en lib/ dentro del jar
    (Bundle-ClassPath en MANIFEST.MF); un -cp plano sobre los jars de nivel superior no los ve."""
    extracted = []
    for jar_path in Path(dimm_plugins_dir).glob('*.jar'):
        try:
            with zipfile.ZipFile(jar_path) as archive:
                for name in archive.namelist():
                    if name.startswith('lib/') and name.endswith('.jar'):
                        target = Path(out_dir) / Path(name).name
                        if not target.exists():
                            target.write_bytes(archive.read(name))
                        extracted.append(str(target))
        except zipfile.BadZipFile:
            continue
    return extracted


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('xml_file', help='Ruta al archivo XML del ATS a validar')
    parser.add_argument('--dimm', default=r'C:\SRI-DIMM\Dimm', help='Carpeta de instalación del DIMM')
    parser.add_argument('--jre', default=None, help='Ruta a jvm.dll (Java 8); se autodetecta si se omite')
    args = parser.parse_args()

    dimm_root = Path(args.dimm)
    plugins_dir = dimm_root / 'plugins'
    if not plugins_dir.is_dir():
        sys.exit('No se encontró la carpeta de plug-ins del DIMM en %s. Instala el DIMM y el plug-in ATS desde sri.gob.ec/formularios-e-instructivos1.' % plugins_dir)

    jvm_path = args.jre or find_default_jre()
    if not jvm_path:
        sys.exit('No se encontró un JRE 8 del sistema. Instala Java 8 (requisito del instalador del DIMM) o indica --jre.')

    try:
        import jpype
    except ImportError:
        sys.exit('Falta jpype1. Instala con: .venv/Scripts/python.exe -m pip install "jpype1<1.6" (las versiones 1.6+ exigen Java 9+).')

    # No se usa TemporaryDirectory con limpieza automática: la JVM embebida mantiene los .jar
    # abiertos (bloqueo de archivos de Windows) incluso después de shutdownJVM(), y el intento de
    # borrado falla. Se deja la carpeta para que el sistema operativo la limpie con el temp normal.
    tmp = tempfile.mkdtemp(prefix='dimm-libs-')
    top_level_jars = [str(p) for p in plugins_dir.glob('*.jar')]
    nested_jars = extract_nested_jars(plugins_dir, tmp)
    classpath = ';'.join(top_level_jars + nested_jars)

    jpype.startJVM(jvm_path, '-Djava.class.path=' + classpath, convertStrings=False)
    failed = False
    try:
        File = jpype.JClass('java.io.File')
        ValidacionATS = jpype.JClass('ec.gob.sri.dimm.ats.validacion.ValidacionATS')
        archivo = File(str(Path(args.xml_file).resolve()))
        if not archivo.exists():
            sys.exit('No existe el archivo: %s' % args.xml_file)
        validador = ValidacionATS(archivo)

        print('Archivo:', args.xml_file)

        print('\n== Esquema (XSD, motor DIMM) ==')
        try:
            resultado = validador.validarEsquema()
            mensajes = list(resultado.getMensajes())
            if not mensajes:
                print('Sin errores de esquema.')
            else:
                failed = True
                for mensaje in mensajes:
                    print(' - %s: %s' % (mensaje.getNivel(), mensaje.getMensaje()))
        except jpype.JException as error:
            failed = True
            print('EXCEPCIÓN:', error.message())

        print('\n== Información (reglas de negocio del DIMM) ==')
        try:
            contexto = validador.validarInformacion()
            if not contexto.isHasErrors():
                print('Sin errores de negocio (%d advertencias).' % contexto.getTotalWarnings())
            else:
                failed = True
                print('%d errores, %d advertencias.' % (contexto.getTotalErros(), contexto.getTotalWarnings()))
                entries = contexto.getErroresAcumulados().entrySet().iterator()
                while entries.hasNext():
                    entry = entries.next()
                    print(' - %s: %s' % (entry.getKey(), entry.getValue()))
        except jpype.JException as error:
            failed = True
            print('EXCEPCIÓN:', error.message())
    finally:
        jpype.shutdownJVM()

    if failed:
        print('\nValidación con errores. No declara presentación ante el SRI: revisa el canal oficial de envío por separado.')
        sys.exit(1)
    print('\nValidación completa sin errores (esquema + reglas de negocio del DIMM). No declara presentación ante el SRI.')


if __name__ == '__main__':
    main()
