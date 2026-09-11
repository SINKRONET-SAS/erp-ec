"""Valida la semilla en copia aislada y registra su hash, sin conservar operaciones."""
from pathlib import Path
import json,hashlib,subprocess,sys,datetime
root=Path(__file__).resolve().parents[1]
state=root/'.cache/windows'
directory=Path(json.loads((state/'operational-current.json').read_text(encoding='utf-8'))['directory'])
if not directory.resolve().is_relative_to((state/'operational-tests').resolve()):
    raise RuntimeError('Se requiere una copia operativa aislada.')
seed=root/'scripts/seed-treasury-demo.py'
before=hashlib.sha256(seed.read_bytes()).hexdigest()
code="env=env(context=dict(env.context,erpec_seed_rollback=True))\nexec(compile(open("+repr(str(seed))+",encoding='utf-8').read(),'seed-treasury-demo.py','exec'))"
result=subprocess.run([sys.executable,str(root/'.cache/odoo-community/odoo-bin'),'shell','-c',str(directory/'odoo.conf'),'--no-http'],input=code,text=True,capture_output=True,encoding='utf-8')
log=directory/'treasury-seed.log'
log.write_bytes((result.stdout+result.stderr).encode('utf-8'))
if result.returncode:
    print(result.stderr[-4000:])
    raise RuntimeError('Falló la semilla de tesorería en copia aislada.')
if before!=hashlib.sha256(seed.read_bytes()).hexdigest():
    raise RuntimeError('La semilla cambió durante el ensayo.')
value={'exitCode':result.returncode,'seedSha256':before,'log':str(log),'logSha256':hashlib.sha256(log.read_bytes()).hexdigest(),'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rolledBack':True}
text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
assert text.encode('utf-8').decode('utf-8')==text
(state/'treasury-seed-result.json').write_bytes(text.encode('utf-8'))
print(result.stdout)
