"""Carreras reales con conexiones independientes, restringidas a bases de ensayo."""
import threading,uuid
from concurrent.futures import ThreadPoolExecutor
from psycopg2.errors import SerializationFailure
from odoo import api,SUPERUSER_ID,Command,fields
from odoo.exceptions import AccessError
from odoo.addons.erpec_entitlements.capabilities import CAPABILITIES


def run(env):
    if not (env.cr.dbname.startswith(('ec_integrated_test_','ec_restore_drill_cm28')) or env.cr.dbname=='linux_test'):
        raise AssertionError('Solo se permite una base aislada de ensayo.')
    registry=env.registry
    context={'no_reset_password':True,'allowed_company_ids':[env.company.id]}
    def local(cr):return api.Environment(cr,SUPERUSER_ID,context)
    def race(operation):
        barrier=threading.Barrier(2)
        def worker(index):
            for attempt in range(4):
                try:
                    with registry._db.cursor() as cr:
                        current=local(cr)
                        cr.execute('SELECT count(*) FROM res_users')
                        if attempt==0:barrier.wait(timeout=20)
                        try:result=operation(current,index)
                        except AccessError:return 'rejected'
                        cr.commit();return result
                except SerializationFailure:
                    if attempt==3:raise
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending=[pool.submit(worker,index) for index in range(2)]
            return [future.result(timeout=90) for future in pending]
    marker='cm28race'+uuid.uuid4().hex[:12]
    checks=[]
    with registry._db.cursor() as cr:
        current=local(cr)
        assert not current['erpec.tenant.entitlement'].search_count([]),'No sobrescribir derechos existentes'
        used=current['res.users'].search_count([('active','=',True),('share','=',False),('id','!=',1)])
        companies=current['res.company'].search_count([])
        current['erpec.tenant.entitlement']._sync(marker,marker,{'users':used+1,'max_companies':companies,'capabilities':list(CAPABILITIES)},'2099-01-01')
        cr.commit()
    try:
        def create_user(current,index):
            current['res.users'].create({'name':'Usuario sintético concurrente','login':marker+str(index),'groups_id':[Command.set(current.ref('base.group_user').ids)]})
            return 'created'
        assert sorted(race(create_user))==['created','rejected']
        checks.append('Dos altas simultáneas para un cupo: una creada y otra rechazada tras reintento')
    finally:
        with registry._db.cursor() as cr:
            cr.execute('DELETE FROM erpec_tenant_entitlement WHERE customer_reference=%s',[marker])
            current=local(cr)
            current['res.users'].with_context(active_test=False).search([('login','in',[marker+'0',marker+'1'])]).unlink()
            cr.commit()
    if 'erpec.provision' in env:
        with registry._db.cursor() as cr:
            current=local(cr)
            plan=current['erpec.plan'].create({'name':'Concurrencia sintética','code':marker,'erp':True,'terms':'Ensayo'})
            plan_id=plan.id;cr.commit()
        customers=[]
        try:
            def create_customer(current,index):
                customer=current['erpec.customer'].create({'name':marker+str(index)})
                contract=current['erpec.subscription'].create({'name':marker+str(index),'customer_id':customer.id,'plan_id':plan_id,'ends_on':'2099-01-01','billing_owner':'manual','billing_reference':'Ensayo','authorization':'Ensayo'})
                contract.action_activate()
                job=current['erpec.provision']._request(contract)
                return (customer.id,contract.id,job.name)
            result=race(create_customer)
            assert len({row[0] for row in result})==2 and len({row[1] for row in result})==2 and len({row[2] for row in result})==2
            checks.append('Dos clientes concurrentes del mismo operador obtienen contratos e instancias distintos')
        finally:
            with registry._db.cursor() as cr:
                current=local(cr)
                contracts=current['erpec.subscription'].search([('plan_id','=',plan_id)])
                customers=contracts.customer_id
                current['erpec.provision'].search([('subscription_id','in',contracts.ids)]).unlink()
                contracts.unlink();customers.unlink();current['erpec.plan'].browse(plan_id).unlink();cr.commit()
    if 'erpec.asset' in env:
        with registry._db.cursor() as cr:
            current=local(cr)
            accounts=[]
            for index,kind in enumerate(['asset_fixed','asset_fixed','expense','equity','expense','income_other']):
                accounts.append(current['account.account'].create({'name':marker+str(index),'code':marker+str(index),'account_type':kind}))
            journal=current['account.journal'].create({'name':marker,'code':marker[-5:],'type':'general'})
            category=current['erpec.asset.category'].create(dict(name=marker,journal_id=journal.id,**dict(zip(['asset_account_id','accumulated_account_id','expense_account_id','clearing_account_id','loss_account_id','gain_account_id'],[a.id for a in accounts]))))
            asset=current['erpec.asset'].create({'name':marker,'category_id':category.id,'cost':100,'months':1,'acquisition_date':'2025-01-01','service_date':'2025-01-01'})
            asset.action_confirm();asset_id=asset.id;category_id=category.id;journal_id=journal.id;account_ids=[a.id for a in accounts];cr.commit()
        try:
            def depreciate(current,index):
                current['erpec.asset'].browse(asset_id).action_depreciate();return 'completed'
            assert race(depreciate)==['completed','completed']
            with registry._db.cursor() as cr:
                current=local(cr);asset=current['erpec.asset'].browse(asset_id)
                assert len(asset.move_ids)==2 and asset.accumulated==100
            checks.append('Dos depreciaciones concurrentes producen un único asiento de cuota')
        finally:
            # Limpieza exacta de filas sintéticas del ensayo, jamás de una base operativa.
            with registry._db.cursor() as cr:
                current=local(cr);asset=current['erpec.asset'].browse(asset_id);moves=asset.move_ids
                cr.execute('UPDATE erpec_asset_line SET move_id=NULL WHERE asset_id=%s',[asset_id])
                cr.execute('UPDATE account_move SET erpec_asset_id=NULL,erpec_asset_kind=NULL WHERE erpec_asset_id=%s',[asset_id])
                cr.execute("UPDATE erpec_asset SET state='draft' WHERE id=%s",[asset_id]);current.invalidate_all()
                asset.unlink();moves.button_draft();moves.with_context(force_delete=True).unlink()
                current['erpec.asset.category'].browse(category_id).unlink();current['account.journal'].browse(journal_id).unlink();current['account.account'].browse(account_ids).unlink();cr.commit()
    print('CM28_CONCURRENCY_OK: '+ ' | '.join(checks))
