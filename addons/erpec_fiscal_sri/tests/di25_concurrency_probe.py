"""Concurrencia PostgreSQL real sobre datos sintéticos exclusivos del ejecutor aislado."""
import threading
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from psycopg2.errors import SerializationFailure
from odoo import api, SUPERUSER_ID
from odoo.exceptions import ValidationError

from odoo.addons.erpec_fiscal_connector.connector import _INTERNAL as EXTERNAL
from ..models import _INTERNAL as NATIVE


class FiscalConcurrencyCheck(unittest.TestCase):
    def __init__(self, env):
        super().__init__()
        self.env = env
        self.registry = env.registry

    def check_both_orders(self):
        if not (self.env.cr.dbname.startswith('ec_integrated_test_') or self.env.cr.dbname == 'linux_test'):
            raise AssertionError('Este ensayo requiere la base desechable del ejecutor integrado.')
        for winner in ('native', 'external'):
            with self.subTest(winner=winner):
                self._race(winner)

    def _race(self, winner):
        # Se evita registry.cursor(): en TransactionCase sería un proxy de la misma transacción.
        with self.registry._db.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            company = env['res.company'].create({'name': 'DI25 concurrencia ' + uuid.uuid4().hex})
            journal = env['account.journal'].create({'name': 'Ensayo DI25', 'code': 'DI25', 'type': 'general', 'company_id': company.id})
            move = env['account.move'].create({'journal_id': journal.id, 'company_id': company.id, 'move_type': 'entry'})
            connection = env['erpec.fiscal.connection'].create({
                'company_id': company.id, 'base_url': 'http://127.0.0.1:3099', 'organization_ref': 'ensayo',
                'empresa_ref': 1, 'workspace_ref': 1, 'emission_point_ref': 1})
            ids = company.id, journal.id, move.id, connection.id
            cr.commit()
        barrier = threading.Barrier(2)
        written, attempting = threading.Event(), threading.Event()

        def create(env, authority):
            if authority == 'native':
                return env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=NATIVE).create({
                    'move_id': ids[2], 'state': 'signed', 'access_key': '1' * 49})
            return env['erpec.fiscal.job'].with_context(_fiscal_internal=EXTERNAL).create({
                'move_id': ids[2], 'connection_id': ids[3], 'external_reference': uuid.uuid4().hex,
                'correlation_id': uuid.uuid4().hex, 'payload': {}})

        def worker(authority):
            try:
                with self.registry._db.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    cr.execute('SELECT id FROM account_move WHERE id=%s', [ids[2]])
                    barrier.wait(timeout=15)
                    if authority == winner:
                        create(env, authority)
                        written.set()
                        if not attempting.wait(15):
                            raise AssertionError('La segunda transacción no comenzó.')
                    else:
                        if not written.wait(15):
                            raise AssertionError('La primera transacción no escribió.')
                        attempting.set()
                        create(env, authority)
                    cr.commit()
                    return 'created'
            except SerializationFailure:
                # El reintento abre una instantánea nueva, como el servicio de Odoo.
                with self.registry._db.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    try:
                        create(env, authority)
                    except ValidationError:
                        return 'rejected'
                    raise AssertionError('El reintento aceptó una segunda autoridad.')

        try:
            with patch.object(type(self.env['ir.cron']), '_trigger'):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(worker, authority) for authority in ('native', 'external')]
                    self.assertCountEqual([future.result(timeout=40) for future in futures], ['created', 'rejected'])
            with self.registry._db.cursor() as cr:
                cr.execute('SELECT (SELECT count(*) FROM erpec_fiscal_emission WHERE move_id=%s) + (SELECT count(*) FROM erpec_fiscal_job WHERE move_id=%s)', [ids[2], ids[2]])
                self.assertEqual(cr.fetchone()[0], 1)
        finally:
            # Solo filas identificadas creadas por este ensayo; nunca comprobantes operativos.
            with self.registry._db.cursor() as cr:
                cr.execute('DELETE FROM erpec_fiscal_emission WHERE move_id=%s', [ids[2]])
                cr.execute('DELETE FROM erpec_fiscal_job WHERE move_id=%s', [ids[2]])
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['account.move'].browse(ids[2]).unlink()
                env['erpec.fiscal.connection'].browse(ids[3]).unlink()
                env['account.journal'].browse(ids[1]).unlink()
                env['res.company'].browse(ids[0]).unlink()
                cr.commit()


def run(env):
    FiscalConcurrencyCheck(env).check_both_orders()
    print("DI25_CONCURRENCY_OK: ambos órdenes, dos transacciones y una autoridad")
