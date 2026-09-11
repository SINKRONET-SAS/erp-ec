"""Identifica documentos históricos de demo que no acreditan parámetros reales."""
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    erpec_legacy_demo_notice = fields.Text('Revisión de la demo histórica', compute='_compute_legacy_demo_notice')

    @api.depends('company_id')
    def _compute_legacy_demo_notice(self):
        legacy = [self.env.ref(xmlid, raise_if_not_found=False) for xmlid in
                  ['erpec_demo_seed.bill', 'erpec_demo_seed.invoice']]
        ids = {record.id for record in legacy if record}
        for move in self:
            move.erpec_legacy_demo_notice = (
                'Documento del ensayo inicial: incluye una retención ficticia y una configuración '
                'contable pendiente de saneamiento. No usarlo como evidencia de parámetros fiscales '
                'reales ni como modelo para registrar operaciones de una empresa.'
                if move.id in ids else False)
