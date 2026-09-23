"""DI25-04.4: matriz fiscal aprobada por responsable (tipo de contribuyente, obligación contable,
IVA/IR/ICE/ISD y exclusiones). No hay una matriz genérica válida para cualquier empresa: cada
aplicabilidad depende del RUC real, del régimen y de la actividad económica, así que este modelo
no precarga ningún código ni tasa de ICE/ISD -- no existe todavía una fuente oficial transcrita
para ellos en este repositorio (ver docs/ALCANCE_ATS_RDEP.md). El responsable tributario declara,
con su propia fuente documentada, qué impuestos aplican y qué excepciones existen; el campo
`approved` empieza en falso y solo lo cambia quien registra la aprobación explícitamente -- nunca
se marca automáticamente. Reutiliza `ec_tax_regime`/`ec_native_accounting` (ya en res.company,
erpec_fiscal_native/models.py) como el tipo de contribuyente y la obligación contable en vez de
duplicarlos."""
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TaxMatrix(models.Model):
    _name = 'erpec.fiscal.tax.matrix'
    _description = 'Matriz fiscal aprobada por responsable (DI25-04): IVA/IR/ICE/ISD y exclusiones'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    vat_applies = fields.Boolean('Aplica IVA', default=True)
    income_tax_applies = fields.Boolean('Aplica Impuesto a la Renta', default=True)
    ice_applies = fields.Boolean('Aplica ICE (Impuesto a los Consumos Especiales)')
    isd_applies = fields.Boolean('Aplica ISD (Impuesto a la Salida de Divisas)')
    exclusions = fields.Text('Exclusiones', help='Actividades, productos o transacciones excluidas de alguno de los impuestos anteriores, con su motivo.')
    reference = fields.Text('Fuente normativa', required=True, help='Cita exacta de la norma, resolución o criterio del responsable tributario que sustenta esta matriz. No se registra sin fuente.')
    approved = fields.Boolean('Aprobada por el responsable tributario', default=False, help='Permanece en falso hasta que el responsable tributario registre expresamente su aprobación; ningún proceso automático la marca.')
    approved_by = fields.Many2one('res.users', 'Aprobada por', readonly=True)
    approved_at = fields.Datetime('Fecha de aprobación', readonly=True)
    note = fields.Text('Notas')
    _sql_constraints = [('company_unique', 'unique(company_id)', 'Ya existe una matriz fiscal registrada para esta empresa.')]

    @api.constrains('reference')
    def _check_reference(self):
        for matrix in self:
            if not (matrix.reference or '').strip():
                raise ValidationError('La matriz fiscal requiere la fuente normativa exacta; no se registra sin ella.')

    @api.constrains('ice_applies', 'isd_applies', 'exclusions')
    def _check_special_taxes_need_a_reason(self):
        # ICE/ISD no tienen catálogo de códigos transcrito todavía (ver docstring del módulo); marcar
        # que aplican sin una nota que lo sustente sería fabricar la regla, no declararla.
        for matrix in self:
            if (matrix.ice_applies or matrix.isd_applies) and not (matrix.note or '').strip():
                raise ValidationError('ICE/ISD no tienen catálogo de códigos verificado en este sistema todavía: registra en "Notas" el sustento exacto (norma, tarifa, hecho generador) antes de marcarlos como aplicables.')

    def action_approve(self):
        for matrix in self:
            if not matrix.reference.strip():
                raise ValidationError('No se puede aprobar una matriz sin fuente normativa.')
            matrix.write({'approved': True, 'approved_by': self.env.user.id, 'approved_at': fields.Datetime.now()})

    def action_revoke_approval(self):
        self.write({'approved': False, 'approved_by': False, 'approved_at': False})

    def write(self, values):
        # Cualquier cambio de contenido revoca una aprobación previa: no debe quedar "aprobada"
        # una matriz que ya no es la que el responsable revisó.
        content_fields = {'vat_applies', 'income_tax_applies', 'ice_applies', 'isd_applies', 'exclusions', 'reference'}
        if content_fields & set(values) and 'approved' not in values:
            approved_matrices = self.filtered('approved')
            if approved_matrices:
                approved_matrices.write({'approved': False, 'approved_by': False, 'approved_at': False})
        return super().write(values)
