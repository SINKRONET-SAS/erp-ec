"""Ensaya una siembra nueva en otra empresa y revierte toda la transacción."""
from pathlib import Path
import subprocess,sys,os,json,hashlib,datetime
root=Path(__file__).resolve().parents[1]
directory=Path(json.loads((root/'.cache/windows/operational-current.json').read_text(encoding='utf-8'))['directory'])
if not directory.resolve().is_relative_to((root/'.cache/windows/operational-tests').resolve()):
    raise RuntimeError('Se requiere copia aislada.')
seed=root/'scripts/seed-demo.py'
before=hashlib.sha256(seed.read_bytes()).hexdigest()
code="""env['ir.model.data'].search([('module','=','erpec_demo_seed')]).unlink()
env.company.name='Origen aislado para ensayo de semilla'
company=env['res.company'].create({'name':'Ensayo semilla nueva DEMO','country_id':env.ref('base.ec').id})
env=env(context=dict(env.context,allowed_company_ids=[company.id],erpec_seed_rollback=True,no_reset_password=True))
env['stock.warehouse'].create({'name':'Bodega de ensayo semilla','code':'TSNEW','company_id':company.id})
exec(compile(open('scripts/seed-demo.py',encoding='utf-8').read(),'seed-demo.py','exec'))
print('Semilla nueva verificada; operación revertida.')
"""
result=subprocess.run([sys.executable,str(root/'.cache/odoo-community/odoo-bin'),'shell','-c',str(directory/'odoo.conf'),'--no-http'],input=code.encode('utf-8'),env={**os.environ,'PYTHONIOENCODING':'utf-8'},capture_output=True)
text=(result.stdout+result.stderr).decode('utf-8',errors='backslashreplace')
assert text.encode('utf-8').decode('utf-8')==text
log=directory/'fresh-seed.log';log.write_bytes(text.encode('utf-8'))
if result.returncode:
    print(text[-4000:])
    raise RuntimeError('Falló la prueba de semilla nueva.')
if before!=hashlib.sha256(seed.read_bytes()).hexdigest():raise RuntimeError('La semilla cambió durante el ensayo.')
value={'exitCode':0,'seedSha256':before,'logSha256':hashlib.sha256(log.read_bytes()).hexdigest(),'log':str(log),'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rolledBack':True}
text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
assert text.encode('utf-8').decode('utf-8')==text
(root/'.cache/windows/fresh-seed-result.json').write_bytes(text.encode('utf-8'))
print('Semilla nueva aprobada en copia aislada, sin conservar cambios.')
