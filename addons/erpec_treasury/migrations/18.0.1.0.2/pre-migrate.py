"""DI26-B.3: se retira erpec.bank.company.account (la cuenta propia sale de la cuenta del diario bancario de nómina).

Si la tabla tiene registros, se detiene la actualización con una instrucción en lugar de perderlos en silencio.
Reversión: restaurar el respaldo previo a la actualización y volver a la versión 18.0.1.0.1 del módulo."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT to_regclass('erpec_bank_company_account')")
    if not cr.fetchone()[0]:
        return
    cr.execute('SELECT count(*) FROM erpec_bank_company_account')
    count = cr.fetchone()[0]
    if count:
        raise RuntimeError('Hay %s cuenta(s) propia(s) registradas en erpec.bank.company.account. Asígnalas como cuenta '
                           'del diario bancario de nómina (con su perfil de archivo de pago) y elimínalas antes de '
                           'actualizar erpec_treasury.' % count)
    _logger.info('DI26-B.3: erpec.bank.company.account sin registros; se retira el modelo.')
