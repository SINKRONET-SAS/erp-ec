"""Normaliza los puntos de emisión existentes: crea el establecimiento (padre) a partir del nombre y la dirección
que antes se repetían en cada punto, sin tocar diarios ni comprobantes."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='erpec_fiscal_point' AND column_name IN ('establishment_name','establishment_address')")
    legacy = {row[0] for row in cr.fetchall()}
    if legacy != {'establishment_name', 'establishment_address'}:
        return
    cr.execute("SELECT id, company_id, establishment, establishment_name, establishment_address FROM erpec_fiscal_point WHERE establishment_id IS NULL ORDER BY id")
    Establishment = env['erpec.fiscal.establishment'].with_context(active_test=False)
    for point_id, company_id, code, name, address in cr.fetchall():
        establishment = Establishment.search([('company_id', '=', company_id), ('code', '=', code)], limit=1)
        if not establishment:
            establishment = Establishment.create({'company_id': company_id, 'code': code, 'name': name or 'Establecimiento %s' % code, 'address': address or '-'})
        cr.execute('UPDATE erpec_fiscal_point SET establishment_id=%s WHERE id=%s', [establishment.id, point_id])
    for column in ('establishment_name', 'establishment_address'):
        cr.execute('ALTER TABLE erpec_fiscal_point ALTER COLUMN %s DROP NOT NULL' % column)
