"""Homologación bancaria (nómina): genera el archivo plano de pago solo para los bancos cuya ficha
técnica oficial fue obtenida y verificada de fuente primaria (no por analogía ni con la plantilla
genérica descartada en docs/VALIDACION_ARCHIVOS_BANCARIOS.md).

Fuentes primarias (URL, versión/fecha y hash del PDF quedan en docs/VALIDACION_ARCHIVOS_BANCARIOS.md):
- Banco Pichincha: "Banca Electrónica Empresas · Formato de carga para pagos" (pichincha.com).
- Produbanco: "Formato de Entrada Pagos_Full", versión 1.1, 07/04/2022 (produbanco.com.ec).
- Banco General Rumiñahui: "Formato CM Full Pagos", 19/03/2015 (bgr.com.ec).
Banco Guayaquil tiene su catálogo de 20 campos identificado (centro de ayuda oficial) pero esa fuente
no declara el delimitador del archivo; su perfil queda sin confirmar y bloqueado para generar.

Alcance de este incremento: solo nómina y solo beneficiarios en el mismo banco del perfil (el propio
formato de Rumiñahui no admite otro banco; Pichincha y Produbanco si lo admiten pero su catálogo de
códigos de otras instituciones queda fuera de este alcance hasta confirmarlo con cada banco). Generar
el archivo no ejecuta ningún pago ni lo marca como pagado: la preparación, el pago contable, el
resultado del banco y la conciliación del extracto siguen siendo pasos separados.
"""
import base64
import hashlib

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

_TOKEN = object()


def require_treasury(env):
    if not env.su and not env.user.has_group('account.group_account_manager'):
        raise AccessError('Se requiere el permiso de responsable de contabilidad.')


def _cents(amount):
    return int(round(amount * 100))


def _split_identification(number):
    digits = ''.join(ch for ch in (number or '') if ch.isdigit())
    if len(digits) == 10:
        return 'C', digits
    if len(digits) == 13:
        return 'R', digits
    if digits:
        return 'P', digits
    raise ValidationError('Identificación del beneficiario requerida (cédula, RUC o pasaporte).')


def _pichincha_row(line, company_account):
    id_type, id_number = _split_identification(line.id_number)
    return ['PA', str(line.sequence), 'USD', str(_cents(line.amount)), 'CTA',
            line.account_type, line.account_number, (line.reference or '')[:200],
            id_type, id_number, line.beneficiary_name[:40], '']


def _produbanco_row(line, company_account):
    id_type, id_number = _split_identification(line.id_number)
    account = line.account_number.zfill(11)
    return ['PA', company_account.zfill(11), str(line.sequence), '', account, 'USD',
            str(_cents(line.amount)).zfill(13), 'CTA', '0036', line.account_type, account,
            id_type, id_number, line.beneficiary_name[:40], '', '', '', '', (line.reference or '')[:200], '']


def _ruminahui_row(line, company_account):
    id_type, id_number = _split_identification(line.id_number)
    return ['PA', company_account, str(line.sequence), '', 'EMP%s' % line.employee_id.id, 'USD',
            str(_cents(line.amount)), 'CTA', '0042', line.account_type, line.account_number,
            id_type, id_number, line.beneficiary_name[:40], '', '', '', '', (line.reference or '')[:200], '']


BANK_PROFILES = {
    'pichincha': {
        'label': 'Banco Pichincha',
        'bank_code': '0010',
        'confirmed': True,
        'delimiter': '\t',
        'row_builder': _pichincha_row,
        'source': 'Banca Electrónica Empresas · Formato de carga para pagos (pichincha.com)',
    },
    'produbanco': {
        'label': 'Produbanco',
        'bank_code': '0036',
        'confirmed': True,
        'delimiter': '\t',
        'row_builder': _produbanco_row,
        'source': 'Formato de Entrada Pagos_Full v1.1, 07/04/2022 (produbanco.com.ec)',
    },
    'ruminahui': {
        'label': 'Banco General Rumiñahui',
        'bank_code': '0042',
        'confirmed': True,
        'delimiter': '\t',
        'row_builder': _ruminahui_row,
        'source': 'Formato CM Full Pagos, 19/03/2015 (bgr.com.ec)',
    },
    'guayaquil': {
        'label': 'Banco Guayaquil (perfil sin confirmar)',
        'bank_code': '0017',
        'confirmed': False,
        'delimiter': None,
        'row_builder': None,
        'source': 'Centro de ayuda Banco Guayaquil, artículo 11032985670804 (24-09-2026): campos '
                   'identificados, delimitador del archivo no declarado en esa fuente.',
    },
}
BANK_SELECTION = [(key, value['label']) for key, value in BANK_PROFILES.items()]


class CompanyBankAccount(models.Model):
    """Cuenta propia de la empresa en cada banco homologado (para 'Cuenta Empresa' del archivo)."""
    _name = 'erpec.bank.company.account'
    _description = 'Cuenta propia de la empresa por banco homologado'
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    bank = fields.Selection(BANK_SELECTION, required=True)
    account_number = fields.Char('Número de cuenta', required=True)
    _sql_constraints = [('company_bank_unique', 'unique(company_id,bank)', 'Ya existe una cuenta para este banco en esta empresa.')]


class PartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    erpec_bank_key = fields.Selection(BANK_SELECTION, string='Banco (perfil de pago homologado)',
        help='Solo se usa para generar archivos de pago homologados; no cambia el banco real de la cuenta.')
    erpec_account_type = fields.Selection([('AHO', 'Ahorros'), ('CTE', 'Corriente')], string='Tipo de cuenta (Ecuador)')


class BankExportBatch(models.Model):
    _name = 'erpec.bank.export.batch'
    _description = 'Lote congelado de archivo de pago bancario (nómina)'
    _rec_name = 'name'
    _order = 'id desc'
    name = fields.Char(required=True, readonly=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True)
    bank = fields.Selection(BANK_SELECTION, required=True, readonly=True)
    period_id = fields.Many2one('erpec.payroll.period', string='Período de nómina', required=True, readonly=True, ondelete='restrict')
    line_ids = fields.One2many('erpec.bank.export.line', 'batch_id', readonly=True)
    total_amount = fields.Monetary(compute='_compute_total', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    file = fields.Binary(readonly=True, attachment=True)
    filename = fields.Char(readonly=True)
    checksum = fields.Char('SHA-256', readonly=True)
    create_uid_name = fields.Char(related='create_uid.name', string='Generado por')

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped('amount'))

    def unlink(self):
        raise ValidationError('El lote congelado es inmutable; conserva la evidencia de exportación.')

    def write(self, values):
        if self.env.context.get('_erpec_bank_export_token') is not _TOKEN:
            raise AccessError('El lote es inmutable una vez generado.')
        return super().write(values)


class BankExportLine(models.Model):
    _name = 'erpec.bank.export.line'
    _description = 'Registro congelado de un archivo de pago bancario'
    _order = 'sequence'
    batch_id = fields.Many2one('erpec.bank.export.batch', required=True, ondelete='restrict')
    disbursement_id = fields.Many2one('erpec.payroll.disbursement', required=True, ondelete='restrict')
    sequence = fields.Integer(required=True)
    employee_id = fields.Many2one(related='disbursement_id.employee_id', store=True)
    id_number = fields.Char(required=True)
    account_number = fields.Char(required=True)
    account_type = fields.Selection([('AHO', 'Ahorros'), ('CTE', 'Corriente')], required=True)
    beneficiary_name = fields.Char(required=True)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related='batch_id.currency_id')
    reference = fields.Char()
    _sql_constraints = [('disbursement_unique', 'unique(disbursement_id)',
        'Este pago de nómina ya está incluido en otro lote de exportación bancaria.')]

    def unlink(self):
        raise ValidationError('El registro es inmutable una vez generado.')

    def write(self, values):
        if self.env.context.get('_erpec_bank_export_token') is not _TOKEN:
            raise AccessError('El registro es inmutable una vez generado.')
        return super().write(values)


class BankExportWizard(models.TransientModel):
    _name = 'erpec.bank.export.wizard'
    _description = 'Generar archivo de pago bancario de nómina'
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    bank = fields.Selection(BANK_SELECTION, required=True)
    period_id = fields.Many2one('erpec.payroll.period', string='Período de nómina', required=True,
        domain="[('company_id','=',company_id),('state','=','posted')]")

    def action_generate(self):
        self.ensure_one()
        require_treasury(self.env)
        profile = BANK_PROFILES[self.bank]
        if not profile['confirmed']:
            raise ValidationError('El perfil de %s todavía no tiene confirmado el delimitador del '
                'archivo con el banco; no se genera un archivo sobre un formato incierto.' % profile['label'])
        if self.period_id.company_id != self.company_id:
            raise ValidationError('El período debe pertenecer a la empresa seleccionada.')
        if self.company_id.currency_id.name != 'USD':
            raise ValidationError('Este perfil solo cubre pagos en dólares (USD).')
        company_account = self.env['erpec.bank.company.account'].search(
            [('company_id', '=', self.company_id.id), ('bank', '=', self.bank)], limit=1)
        if not company_account:
            raise ValidationError('Configura la cuenta propia de la empresa en %s antes de generar el archivo.' % profile['label'])
        disbursements = self.period_id.disbursement_ids.filtered(
            lambda d: d.status in ('open', 'partial') and not d.currency_id.is_zero(d.residual))
        if not disbursements:
            raise ValidationError('No hay pagos de nómina pendientes en este período.')
        already = self.env['erpec.bank.export.line'].search([('disbursement_id', 'in', disbursements.ids)])
        if already:
            raise ValidationError('%s de estos pagos ya están en otro lote de exportación bancaria.' % len(already))
        rows, line_values = [], []
        for sequence, disbursement in enumerate(disbursements, start=1):
            employee = disbursement.employee_id
            account = employee.bank_account_id
            if not account or not account.acc_number or account.erpec_bank_key != self.bank or not account.erpec_account_type:
                raise ValidationError('%s no tiene una cuenta en %s con tipo (ahorros/corriente) configurada.'
                    % (employee.name, profile['label']))
            id_type, id_number = _split_identification(employee.identification_id)
            line = self.env['erpec.bank.export.line'].new({
                'sequence': sequence, 'disbursement_id': disbursement.id, 'id_number': id_number,
                'account_number': account.acc_number, 'account_type': account.erpec_account_type,
                'beneficiary_name': employee.name, 'amount': disbursement.residual,
                'reference': 'NOMINA %s' % self.period_id.name,
            })
            rows.append(profile['row_builder'](line, company_account.account_number))
            line_values.append({'sequence': sequence, 'disbursement_id': disbursement.id,
                'id_number': id_number, 'account_number': account.acc_number,
                'account_type': account.erpec_account_type, 'beneficiary_name': employee.name,
                'amount': disbursement.residual, 'reference': 'NOMINA %s' % self.period_id.name})
        content = '\n'.join(profile['delimiter'].join(row) for row in rows) + '\n'
        payload = content.encode('utf-8')
        checksum = hashlib.sha256(payload).hexdigest()
        name = 'PAGO-NOMINA-%s-%s-%s' % (self.period_id.name, self.bank.upper(), checksum[:8])
        batch = self.env['erpec.bank.export.batch'].with_context(_erpec_bank_export_token=_TOKEN).create({
            'name': name, 'company_id': self.company_id.id, 'bank': self.bank, 'period_id': self.period_id.id,
            'file': base64.b64encode(payload), 'filename': '%s.txt' % name, 'checksum': checksum,
        })
        for values in line_values:
            values['batch_id'] = batch.id
        self.env['erpec.bank.export.line'].with_context(_erpec_bank_export_token=_TOKEN).create(line_values)
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.bank.export.batch', 'res_id': batch.id,
                'view_mode': 'form', 'target': 'current'}
