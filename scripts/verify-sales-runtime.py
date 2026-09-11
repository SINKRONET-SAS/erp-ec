"""Comprueba enlaces comerciales y vistas en la demo, sin registrar operaciones."""
from pathlib import Path
import datetime, json, socket, xmlrpc.client
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.cache/windows'
socket.setdefaulttimeout(15)
password=json.loads((STATE/'demo/credentials.json').read_text(encoding='utf-8'))['admin']
url='http://127.0.0.1:8369'
uid=xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate('erpec_demo','demo',password,{})
if not uid:raise RuntimeError('No se pudo comprobar la demo')
def call(model,method,args,kwargs=None):
    return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object').execute_kw('erpec_demo',uid,password,model,method,args,kwargs or {})
def ref(module,name):
    rows=call('ir.model.data','search_read',[[('module','=',module),('name','=',name)]],{'fields':['res_id']})
    if len(rows)!=1:raise RuntimeError('Referencia de demostración ausente o ambigua')
    return rows[0]['res_id']
company=call('res.company','read',[[1]],{'fields':['vat','name']})[0]
assert not company['vat'] and 'DEMO' in company['name']
items=[]
for key,total,original_total in [('invoice',575,500),('bill',230,200)]:
    source=call('account.move','read',[[ref('erpec_demo_seed',key)]],{'fields':['state','amount_total','amount_residual']})[0]
    assert source['state']=='posted' and source['amount_total']==original_total and source['amount_residual']==0
    move=call('account.move','read',[[ref('erpec_sanitized_demo',key)]],{'fields':['name','state','amount_total','invoice_origin','invoice_line_ids']})[0]
    assert move['state']=='posted' and move['amount_total']==total and len(move['invoice_line_ids'])==1
    line=call('account.move.line','read',[move['invoice_line_ids']],{'fields':['sale_line_ids','purchase_line_id']})[0]
    if key=='invoice':
        assert len(line['sale_line_ids'])==1
        orderline=call('sale.order.line','read',[line['sale_line_ids']],{'fields':['order_id','qty_to_invoice','qty_invoiced']})[0]
        assert orderline['qty_to_invoice']==0 and orderline['qty_invoiced']==1
        model='sale.order'
    else:
        assert line['purchase_line_id']
        orderline=call('purchase.order.line','read',[[line['purchase_line_id'][0]]],{'fields':['order_id','qty_invoiced']})[0]
        assert orderline['qty_invoiced']==1
        model='purchase.order'
    order=call(model,'read',[[orderline['order_id'][0]]],{'fields':['name','amount_total','invoice_status','invoice_ids']})[0]
    assert order['invoice_status']=='invoiced' and order['amount_total']==total and move['id'] in order['invoice_ids']
    assert move['invoice_origin']==order['name']
    items.append({'document':move['name'],'order':order['name'],'total':total,'invoiceStatus':order['invoice_status'],'linked':True})
arch=call('erpec.importation','get_view',[],{'view_type':'form'})['arch']
root=etree.fromstring(arch.encode('utf-8'))
assert root.xpath("//field[@name='cost_ids']")[0].get('readonly')=='True'
assert root.xpath("//field[@name='purchase_ids']")[0].get('readonly')=='bool(cost_ids)'
value={'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authenticated':True,
       'demoWithoutRuc':True,'commercialLinks':items,'importCostsReadOnly':True,
       'externalTransfers':False,'sriEmission':False}
text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
assert text.encode('utf-8').decode('utf-8')==text
(STATE/'sales-runtime-result.json').write_text(text,encoding='utf-8',newline='\n')
print(json.dumps(value,ensure_ascii=True))
