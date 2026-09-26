"""DI26-E.1: aplica español de Ecuador y zona America/Guayaquil a las bases existentes."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    api.Environment(cr, SUPERUSER_ID, {})['res.company']._ec_apply_locale_defaults()
