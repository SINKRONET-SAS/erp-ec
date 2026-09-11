"""Comprueba accesos reales del centro sin crear movimientos de negocio."""
import json, socket, time, xmlrpc.client
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
password = json.loads((STATE/'demo/credentials.json').read_text(encoding='utf-8'))['admin']
url = 'http://127.0.0.1:8369'
socket.setdefaulttimeout(20)
uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate('erpec_demo','demo',password,{})
if not uid:
    raise RuntimeError('No se pudo autenticar la demo')

def call(model, method, args, kwargs=None):
    return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object').execute_kw('erpec_demo',uid,password,model,method,args,kwargs or {})

home = call('erpec.workspace','action_home',[])
arch = call('erpec.workspace','get_view',[],{'view_id':home['views'][0][0],'view_type':'form'})['arch']
assert 'Centro de trabajo' in arch and 'edit="false"' in arch
assert 'create' not in home['context'] and 'edit' not in home['context']
results = []
for area in ['sales','purchases','inventory','imports','manufacturing','workorders','invoices','bills','payroll','fiscal']:
    start = time.perf_counter()
    action = call('erpec.workspace','action_area',[[home['res_id']]],{'context':{'erpec_area':area}})
    model = action['res_model']
    view = call(model,'get_view',[],{'view_type':'list'})
    assert view['arch']
    results.append({'area':area,'model':model,'listCompiled':True,'seconds':round(time.perf_counter()-start,3)})
purchase_arch = call('purchase.order','get_view',[],{'view_type':'form'})['arch']
assert 'erpec_purchase_guide' in purchase_arch
assert 'Preparar factura / nota de crédito' in purchase_arch
purchase_guides = call('purchase.order','search_read',[[('state','=','purchase')]],
    {'fields':['name','receipt_status','invoice_status','erpec_purchase_guide'],'limit':5})
assert purchase_guides and all(row['erpec_purchase_guide'] for row in purchase_guides)
result = {'authenticated':True,'homeRecord':home['res_id'],'homeAction':home['id'],'areas':results,
          'purchaseGuidance':purchase_guides,'businessRecordsCreated':False,'scope':'Accesos y vistas con el perfil demo; no acredita ciclos completos ni carga concurrente'}
text = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
assert text.encode('utf-8').decode('utf-8') == text
(STATE/'workspace-runtime-result.json').write_bytes(text.encode('utf-8'))
print(json.dumps(result,ensure_ascii=True))
