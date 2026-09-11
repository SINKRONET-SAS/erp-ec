"""Configura el catálogo Community de un piloto local sin instalar ni eliminar módulos."""
import argparse
import ast
import configparser
import json
from pathlib import Path
import re
import socket
import xmlrpc.client

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
socket.setdefaulttimeout(30)


def configure(directory, password, restore=False):
    config = configparser.ConfigParser(interpolation=None)
    config.read(directory/'odoo.conf', encoding='utf-8')
    database = config['options']['db_name']
    port = int(config['options']['http_port'])
    url = 'http://127.0.0.1:' + str(port)
    common = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common')
    uid = common.authenticate(database, 'admin', password, {})
    if not uid:
        raise RuntimeError('No se pudo autenticar el administrador local')
    models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
    def call(model, method, args, kwargs=None):
        return models.execute_kw(database, uid, password, model, method, args,
            {'context':{'lang':'es_EC'}, **(kwargs or {})})
    installed = call('ir.module.module','search_read',[[('state','=','installed'),('license','in',['OEEL-1','OPL-1'])]],{'fields':['name','license']})
    if installed:
        raise RuntimeError('Existen módulos propietarios de terceros: revisar antes de modificar el catálogo')
    metadata = call('ir.model.data','search_read',[[('module','=','base'),('name','=','open_module_tree')]],{'fields':['res_id']})
    if len(metadata) != 1:
        raise RuntimeError('No se encontró la acción estándar de aplicaciones')
    action_id = metadata[0]['res_id']
    fields = ['name','domain']
    original = call('ir.actions.act_window','read',[[action_id],fields])[0]
    backup = STATE/'catalog-backups'/(directory.name+'-'+str(port)+'.json')
    if backup.exists():
        saved = json.loads(backup.read_text(encoding='utf-8'))
        if saved['database'] != database or saved['action'] != action_id:
            raise RuntimeError('El respaldo no corresponde a esta base y acción')
    else:
        if restore:
            raise RuntimeError('No existe respaldo para revertir este catálogo')
        domain = ast.literal_eval(original['domain'] or '[]')
        if not isinstance(domain,list):
            raise RuntimeError('El dominio existente requiere revisión manual')
        applied = {'name':'Aplicaciones ERP EC · Community',
            'domain':repr(([('to_buy','=',False)] + domain))}
        saved = {'database':database,'action':action_id,
            'original':{key:original[key] for key in fields},'applied':applied}
        text = json.dumps(saved,ensure_ascii=False,indent=2)+'\n'
        assert text.encode('utf-8').decode('utf-8') == text
        backup.parent.mkdir(parents=True,exist_ok=True)
        backup.write_text(text,encoding='utf-8',newline='\n')
    current = {key:original[key] for key in fields}
    if current not in (saved['original'],saved['applied']):
        raise RuntimeError('La acción cambió después del respaldo; conservar el cambio y revisarlo')
    target = saved['original'] if restore else saved['applied']
    if current != target:
        call('ir.actions.act_window','write',[[action_id],target])
    result = call('ir.actions.act_window','read',[[action_id],fields])[0]
    assert all(result[key] == target[key] for key in fields)
    domain = ast.literal_eval(result['domain'] or '[]')
    promotions = call('ir.module.module','search_count',[domain+[('to_buy','=',True)]])
    if not restore and promotions:
        raise RuntimeError('El catálogo todavía contiene promociones Enterprise')
    return {'port':port,'enterpriseInstalled':installed,'promotionsVisible':promotions,
        'restored':restore,'name':result['name'],'action':action_id,
        'applicationsVisible':call('ir.module.module','search_count',[domain+[('application','=',True)]])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--operator',action='store_true')
    parser.add_argument('--instance',help='Identidad local del cliente: 32 caracteres hexadecimales')
    parser.add_argument('--restore',action='store_true')
    args = parser.parse_args()
    if not args.operator and not args.instance:
        parser.error('Selecciona --operator o --instance')
    results = []
    if args.operator:
        private = json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
        results.append(configure(STATE/'a',private['admin_a'],args.restore))
    if args.instance:
        if not re.fullmatch('[a-f0-9]{32}',args.instance):
            parser.error('Identidad de cliente inválida')
        directory = STATE/'instances'/args.instance
        private = json.loads((directory/'credentials.json').read_text(encoding='utf-8'))
        results.append(configure(directory,private['admin'],args.restore))
    print(json.dumps(results,ensure_ascii=False))
