"""Vista previa, recálculo y reversión de saldos derivados; no altera cuotas ni asientos."""
import hashlib
import json

from odoo.exceptions import ValidationError
from .models import manager, _INTERNAL


def _fingerprint(advance):
    payload = [advance.id, advance.amount_total, [
        (item.id, item.line_id.id, item.amount, item.line_id.period_id.state)
        for item in advance.deduction_ids.sorted('id')]]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()


def preview(env):
    manager(env)
    records = env['erpec.payroll.advance'].search([])
    records.check_access('write')
    return {'database': env.cr.dbname, 'rows': [{
        'id': item.id, 'before_balance': item.balance, 'before_settled': item.settled,
        'after_balance': item.amount_total - sum(
            item.deduction_ids.filtered(lambda row: row.line_id.period_id.state != 'reversed').mapped('amount')),
        'source_hash': _fingerprint(item),
    } for item in records]}


def apply(env, snapshot, restore=False):
    manager(env)
    if snapshot.get('database') != env.cr.dbname:
        raise ValidationError('El respaldo de saldos pertenece a otra base.')
    ids = [row['id'] for row in snapshot['rows']]
    records = env['erpec.payroll.advance'].browse(ids).exists()
    records.check_access('write')
    if len(records) != len(ids) or len(ids) != len(set(ids)):
        raise ValidationError('El respaldo contiene anticipos ausentes o duplicados.')
    for item in records.sorted('id'):
        item._lock()
    for row in snapshot['rows']:
        item = records.browse(row['id'])
        if _fingerprint(item) != row['source_hash']:
            raise ValidationError('Las cuotas o sus períodos cambiaron; no se puede aplicar ni revertir el saldo.')
    for row in snapshot['rows']:
        balance = row['before_balance'] if restore else row['after_balance']
        settled = row['before_settled'] if restore else balance <= 0
        records.browse(row['id']).with_context(_erpec_payroll_token=_INTERNAL).write({
            'balance': balance, 'settled': settled})
    return len(records)
