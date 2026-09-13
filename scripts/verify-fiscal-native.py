"""Ensaya generación local y regresión del conector en la copia operativa existente."""
import importlib.util,json,subprocess,hashlib,datetime,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verify',ROOT/'scripts/verify-operational-plan.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
directory=Path(json.loads((verify.STATE/'operational-current.json').read_text(encoding='utf-8'))['directory'])
if not directory.resolve().is_relative_to((verify.STATE/'operational-tests').resolve()):raise RuntimeError('Se requiere copia operativa aislada')
closeout_mode = '--closeout' in sys.argv
workspace_mode = '--workspace' in sys.argv
modules=['erpec_workspace','erpec_treasury'] if closeout_mode else ['erpec_workspace'] if workspace_mode else ['erpec_fiscal_native','erpec_fiscal_connector']
prefix = 'closeout' if closeout_mode else 'workspace' if workspace_mode else 'fiscal-native'
def hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for m in modules for p in (ROOT/'addons'/m).rglob('*') if p.is_file() and p.suffix in ('.py','.xml','.csv','.xsd','.js','.scss')}
before=hashes();log=directory/(prefix+'-tests-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.log')
result=subprocess.run([sys.executable,str(verify.SOURCE/'odoo-bin'),'-c',str(directory/'odoo.conf'),'-i',','.join(modules),'-u',','.join(modules),'--test-enable','--test-tags',','.join('/'+m for m in modules),'--stop-after-init','--no-http','--logfile',str(log)],env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'})
if before!=hashes():raise RuntimeError('Los archivos cambiaron durante las pruebas')
verify.write(verify.STATE/(prefix+'-test-result.json'),json.dumps({'exitCode':result.returncode,'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directory':str(directory),'log':str(log),'logSha256':hashlib.sha256(log.read_bytes()).hexdigest(),'modules':modules,'fileHashes':before},indent=2)+'\n')
print('Resultado de tesorería y compras:' if closeout_mode else 'Resultado del centro de trabajo:' if workspace_mode else 'Resultado fiscal local:',result.returncode);sys.exit(result.returncode)
