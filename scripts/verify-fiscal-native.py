"""Ensaya generación local y regresión del conector en la copia operativa existente."""
import importlib.util,json,subprocess,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verify',ROOT/'scripts/verify-operational-plan.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
directory=Path(json.loads((verify.STATE/'operational-current.json').read_text())['directory'])
if not directory.resolve().is_relative_to((verify.STATE/'operational-tests').resolve()):raise RuntimeError('Se requiere copia operativa aislada')
modules=['erpec_fiscal_native','erpec_fiscal_connector']
def hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for m in modules for p in (ROOT/'addons'/m).rglob('*') if p.is_file() and p.suffix in ('.py','.xml','.csv','.xsd')}
before=hashes();log=directory/('native-tests-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.log')
result=subprocess.run([sys.executable,str(verify.SOURCE/'odoo-bin'),'-c',str(directory/'odoo.conf'),'-i',','.join(modules),'-u',','.join(modules),'--test-enable','--test-tags',','.join('/'+m for m in modules),'--stop-after-init','--no-http','--logfile',str(log)])
if before!=hashes():raise RuntimeError('Los archivos cambiaron durante las pruebas')
verify.write(verify.STATE/'fiscal-native-test-result.json',json.dumps({'exitCode':result.returncode,'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directory':str(directory),'log':str(log),'logSha256':hashlib.sha256(log.read_bytes()).hexdigest(),'modules':modules,'fileHashes':before},indent=2)+'\n')
print('Resultado fiscal local:',result.returncode);sys.exit(result.returncode)
