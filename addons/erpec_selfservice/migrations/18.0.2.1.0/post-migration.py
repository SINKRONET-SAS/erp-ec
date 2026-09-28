"""Retirada explícita de SS-DEMO; no altera contratos ni precios históricos."""
from odoo import api,SUPERUSER_ID

def migrate(cr,version):
    api.Environment(cr,SUPERUSER_ID,{})['erpec.plan']._retire_demo_offer()
