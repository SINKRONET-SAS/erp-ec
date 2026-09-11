"""Repite controles y prueba dos solicitudes HTTP concurrentes en la copia respaldada."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json, subprocess, sys, threading, time, xmlrpc.client
from importlib.machinery import SourceFileLoader
ROOT = Path(__file__).resolve().parents[1]
verify = SourceFileLoader('manufacturing_verify', str(ROOT/'scripts/verify-manufacturing.py')).load_module()
report = json.loads((verify.STATE/'manufacturing-test-result.json').read_text(encoding='utf-8'))
directory = Path(report['backup'])
conf = directory/'odoo.conf'
command = [sys.executable, str(verify.SOURCE/'odoo-bin'), '-c', str(conf)]
result = subprocess.run(command + ['-u', 'erpec_manufacturing', '--test-enable', '--test-tags', '/erpec_manufacturing', '--stop-after-init', '--no-http'])
if result.returncode:
    raise RuntimeError('Fallaron los controles de fabricación')
seed = "exec(compile(open(" + repr(str(ROOT/'scripts/seed-manufacturing-demo.py')) + ",encoding='utf-8').read(),'seed-manufacturing-demo.py','exec'))"
subprocess.run([sys.executable, str(verify.SOURCE/'odoo-bin'), 'shell', '-c', str(conf), '--no-http'], input=seed, text=True, check=True)
password = json.loads((verify.DEMO/'credentials.json').read_text(encoding='utf-8'))['admin']
url = 'http://127.0.0.1:8469'
server = subprocess.Popen(command, cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    for attempt in range(60):
        try:
            uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(report['database'], 'demo', password, {})
            if uid:
                break
        except (OSError, xmlrpc.client.Error):
            if attempt == 59:
                raise RuntimeError('La copia no respondió') from None
        time.sleep(1)
    else:
        raise RuntimeError('No se autenticó la copia')
    def call(model, method, args, kwargs=None):
        return xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object').execute_kw(report['database'], uid, password, model, method, args, kwargs or {})
    metadata = call('ir.model.data', 'search_read', [[('module', '=', 'erpec_manufacturing_demo'), ('name', '=', 'pending_order')]], {'fields': ['res_id']})
    stages = call('mrp.workorder', 'search_read', [[('production_id', '=', metadata[0]['res_id'])]], {'fields': ['id'], 'order': 'id'})
    first = stages[0]['id']
    barrier = threading.Barrier(2)
    def start():
        barrier.wait(timeout=10)
        return call('mrp.workorder', 'button_start', [[first]])
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(start) for _ in range(2)]
        assert all(future.result(timeout=40) is True for future in futures)
    count = call('mrp.workcenter.productivity', 'search_count', [[('workorder_id', '=', first), ('date_end', '=', False)]])
    assert count == 1, 'Las solicitudes concurrentes duplicaron el temporizador'
    call('mrp.workorder', 'write', [[first], {'erpec_pause_reason': 'Fin del ensayo concurrente'}])
    call('mrp.workorder', 'button_pending', [[first]])
    assert call('mrp.workcenter.productivity', 'search_count', [[('workorder_id', '=', first), ('date_end', '=', False)]]) == 0
    report.update({'exitCode': 0, 'fileHashes': verify.hashes(), 'seedHash': verify.hashlib.sha256((ROOT/'scripts/seed-manufacturing-demo.py').read_bytes()).hexdigest(), 'concurrentRequests': 2, 'openTimersAfterConcurrentStart': count, 'openTimersAfterPause': 0, 'seedPassed': True})
    verify.write(verify.STATE/'manufacturing-test-result.json', report)
    print(json.dumps(report), flush=True)
finally:
    server.terminate()
    server.wait(30)
