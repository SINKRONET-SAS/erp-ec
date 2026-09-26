"""DI26-D.2: las exclusiones comerciales guardadas en la columna antigua pasan a la lista negra de correo (una sola autoridad).
La columna queda sin uso; no se borra para conservar la historia hasta una limpieza explícita."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name='res_partner' AND column_name='ec_marketing_email_opt_out'")
    if not cr.fetchone():
        return
    cr.execute("SELECT id FROM res_partner WHERE ec_marketing_email_opt_out")
    ids = [row[0] for row in cr.fetchall()]
    if not ids:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for partner in env['res.partner'].browse(ids):
        if partner.email_normalized:
            env['mail.blacklist']._add(partner.email_normalized, message='Migrado desde la exclusión comercial del contacto (DI26-D.2).')
