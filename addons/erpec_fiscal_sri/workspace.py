"""Estado fiscal del Inicio derivado de lo instalado y configurado (DI25-14), sin afirmar capacidades que
no existen ni ocultar bloqueos reales: separa alcance técnico, configuración de la empresa, ambiente y
validación externa."""
from odoo import models


class Workspace(models.Model):
    _inherit = 'erpec.workspace'

    def _compute_company_readiness(self):
        super()._compute_company_readiness()
        for workspace in self:
            workspace.fiscal_scope = workspace._native_fiscal_scope() + '\n\n' + (workspace.fiscal_scope or '')

    def _native_fiscal_scope(self):
        self.ensure_one()
        company = self.company_id
        # sudo solo para leer banderas de estado: nunca se lee ni muestra material de firma.
        certificate = self.env['erpec.fiscal.certificate'].sudo().search([('company_id', '=', company.id)], limit=1)
        points = self.env['erpec.fiscal.point'].sudo().search([('company_id', '=', company.id)])
        production = points.filtered(lambda point: point.ambiente == '2')
        missing = []
        if not company.vat:
            missing.append('RUC de la empresa')
        if not certificate:
            missing.append('cargar el certificado de firma electrónica')
        elif not certificate.verified:
            missing.append('verificar el certificado de firma electrónica')
        if not points:
            missing.append('registrar el establecimiento y el punto de emisión')
        lines = [
            'Alcance instalado: firma electrónica, envío directo al SRI, consulta de autorización y RIDE (emisión nativa).',
            ('Falta configurar en esta empresa: ' + ', '.join(missing) + '.') if missing
            else 'Configuración de esta empresa completa: RUC, certificado verificado y punto de emisión.',
        ]
        if production:
            lines.append('Producción habilitada en %d punto(s) de emisión: los comprobantes emitidos allí tienen efectos tributarios reales.' % len(production))
        elif points:
            lines.append('Ambiente actual: pruebas en todos los puntos de emisión.')
        lines.append('Validación externa: solo el SRI acredita una autorización; una factura contabilizada o pagada no la garantiza. Revisa el resultado en Emisiones.')
        return '\n'.join(lines)
