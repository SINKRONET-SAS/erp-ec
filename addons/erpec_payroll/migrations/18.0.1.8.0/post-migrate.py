"""Recalcula saldos derivados al actualizar; mantiene cuotas históricas y asientos."""
import logging
from odoo import api, SUPERUSER_ID
from odoo.addons.erpec_payroll.balance_migration import preview, apply

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    count = apply(env, preview(env))
    _logger.info('Saldos de anticipos recalculados: %s code=NOMINA_SALDOS_DI25 statusCode=200 correlationId=migracion-di25-03 userId=%s', count, SUPERUSER_ID)
