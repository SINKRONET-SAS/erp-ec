"""Homologación bancaria (nómina): genera el archivo plano de pago solo para los bancos cuya ficha
técnica oficial fue obtenida y verificada de fuente primaria (no por analogía ni con la plantilla
genérica descartada en docs/VALIDACION_ARCHIVOS_BANCARIOS.md).

Fuentes primarias (URL, versión/fecha y hash del PDF quedan en docs/VALIDACION_ARCHIVOS_BANCARIOS.md):
- Banco Pichincha: "Banca Electrónica Empresas · Formato de carga para pagos" (pichincha.com).
- Produbanco: "Formato de Entrada Pagos_Full", versión 1.1, 07/04/2022 (produbanco.com.ec).
- Banco General Rumiñahui: "Formato CM Full Pagos", 19/03/2015 (bgr.com.ec).
Banco Guayaquil tiene su catálogo de 20 campos identificado (centro de ayuda oficial) pero esa fuente
no declara el delimitador del archivo; su perfil queda sin confirmar y bloqueado para generar.

Alcance: solo nómina y solo beneficiarios en el mismo banco del perfil (el propio formato de Rumiñahui no
admite otro banco). La cuenta propia de la empresa sale de la cuenta bancaria del diario de nómina (una sola
autoridad, DI26-B.3) y la identificación del beneficiario del tipo declarado en el empleado (DI26-B.2).
Generar el archivo no ejecuta ningún pago ni lo marca como pagado: la preparación, el pago contable, el
resultado del banco y la conciliación del extracto siguen siendo pasos separados.
"""
import base64
import hashlib
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

_TOKEN = object()


def require_treasury(env):
    """El archivo de pago de nómina expone salarios y cuentas: exige responsable de nómina (que implica contabilidad)."""
    if env.su:
        return
    if not env.user.has_group('erpec_payroll.group_payroll_manager'):
        raise AccessError('Generar el archivo de pago de nómina requiere los permisos de responsable de contabilidad y de nómina.')


def _cents(amount):
    return int(round(amount * 100))


def beneficiary_identification(employee, profile):
    """Tipo (C/R/P) y número del beneficiario según el tipo declarado en el empleado.

    El pasaporte se conserva alfanumérico; la cédula exige 10 dígitos y el RUC 13. Si el empleado no declara
    tipo, solo se acepta una cédula o un RUC numéricos; nunca se recortan caracteres para "hacerlos caber"."""
    raw = re.sub(r'[\s\-.]', '', (employee.identification_id or '')).upper()
    if not raw:
        raise ValidationError('%s no tiene número de identificación.' % employee.name)
    declared = employee.ec_rdep_id_type or ''
    if declared in ('P', 'E') or not raw.isdigit():
        if not raw.isalnum():
            raise ValidationError('El pasaporte de %s contiene caracteres no válidos: %s.' % (employee.name, raw))
        limit = profile.get('passport_max')
        if limit and len(raw) > limit:
            raise ValidationError('El pasaporte de %s supera los %s caracteres que admite %s.' % (employee.name, limit, profile['label']))
        return 'P', raw
    if len(raw) == 10:
        return 'C', raw
    if len(raw) == 13:
        return 'R', raw
    raise ValidationError('La identificación de %s no es una cédula de 10 dígitos ni un RUC de 13: revisa el número o '
                          'declara el tipo de identificación en el empleado.' % employee.name)


def _pichincha_row(line, company_account):
    return ['PA', str(line.sequence), 'USD', str(_cents(line.amount)), 'CTA',
            line.account_type, line.account_number, (line.reference or '')[:200],
            line.id_type, line.id_number, line.beneficiary_name[:40], '']


def _produbanco_row(line, company_account):
    account = line.account_number.zfill(11)
    return ['PA', company_account.zfill(11), str(line.sequence), '', account, 'USD',
            str(_cents(line.amount)).zfill(13), 'CTA', '0036', line.account_type, account,
            line.id_type, line.id_number, line.beneficiary_name[:40], '', '', '', '', (line.reference or '')[:200], '']


def _ruminahui_row(line, company_account):
    return ['PA', company_account, str(line.sequence), '', 'EMP%s' % line.employee_id.id, 'USD',
            str(_cents(line.amount)), 'CTA', '0042', line.account_type, line.account_number,
            line.id_type, line.id_number, line.beneficiary_name[:40], '', '', '', '', (line.reference or '')[:200], '']


BANK_PROFILES = {
    'pichincha': {
        'label': 'Banco Pichincha',
        'bank_code': '0010',
        'confirmed': True,
        'delimiter': '\t',
        'passport_max': None,
        'row_builder': _pichincha_row,
        'source': 'Banca Electrónica Empresas · Formato de carga para pagos (pichincha.com)',
    },
    'produbanco': {
        'label': 'Produbanco',
        'bank_code': '0036',
        'confirmed': True,
        'delimiter': '\t',
        'passport_max': 13,
        'row_builder': _produbanco_row,
        'source': 'Formato de Entrada Pagos_Full v1.1, 07/04/2022 (produbanco.com.ec)',
    },
    'ruminahui': {
        'label': 'Banco General Rumiñahui',
        'bank_code': '0042',
        'confirmed': True,
        'delimiter': '\t',
        'passport_max': 14,
        'row_builder': _ruminahui_row,
        'source': 'Formato CM Full Pagos, 19/03/2015 (bgr.com.ec)',
    },
    'guayaquil': {
        'label': 'Banco Guayaquil (perfil sin confirmar)',
        'bank_code': '0017',
        'confirmed': False,
        'delimiter': None,
        'passport_max': None,
        'row_builder': None,
        'source': 'Centro de ayuda Banco Guayaquil, artículo 11032985670804 (24-09-2026): campos '
                   'identificados, delimitador del archivo no declarado en esa fuente.',
    },
}
BANK_SELECTION = [(key, value['label']) for key, value in BANK_PROFILES.items()]
ACCOUNT_TYPES = [('AHO', 'Ahorros'), ('CTE', 'Corriente')]


class PartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    erpec_bank_key = fields.Selection(BANK_SELECTION, string='Perfil de archivo de pago',
        help='Formato de archivo de pago homologado que acepta el banco de esta cuenta. Es el formato del archivo, '
             'no reemplaza al banco registrado en la cuenta.')
    erpec_account_type = fields.Selection(ACCOUNT_TYPES, string='Tipo de cuenta (Ecuador)')


class BankExportBatch(models.Model):
    _name = 'erpec.bank.export.batch'
    _description = 'Lote congelado de archivo de pago bancario (nómina)'
    _rec_name = 'name'
    _order = 'id desc'
    name = fields.Char('Nombre del lote', required=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Empresa', required=True, readonly=True)
    bank = fields.Selection(BANK_SELECTION, string='Banco', required=True, readonly=True)
    period_id = fields.Many2one('erpec.payroll.period', string='Período de nómina', required=True, readonly=True, ondelete='restrict')
    line_ids = fields.One2many('erpec.bank.export.line', 'batch_id', string='Registros', readonly=True)
    total_amount = fields.Monetary('Total del lote', compute='_compute_total', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Moneda')
    file = fields.Binary('Archivo', readonly=True, attachment=True)
    filename = fields.Char('Nombre del archivo', readonly=True)
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
    batch_id = fields.Many2one('erpec.bank.export.batch', string='Lote', required=True, ondelete='restrict')
    disbursement_id = fields.Many2one('erpec.payroll.disbursement', string='Pago de nómina', required=True, ondelete='restrict')
    sequence = fields.Integer('Secuencial', required=True)
    employee_id = fields.Many2one(related='disbursement_id.employee_id', string='Empleado', store=True)
    id_type = fields.Selection([('C', 'Cédula'), ('R', 'RUC'), ('P', 'Pasaporte')], string='Tipo de identificación', required=True)
    id_number = fields.Char('Identificación', required=True)
    account_number = fields.Char('Número de cuenta', required=True)
    account_type = fields.Selection(ACCOUNT_TYPES, string='Tipo de cuenta', required=True)
    beneficiary_name = fields.Char('Beneficiario', required=True)
    amount = fields.Monetary('Monto', required=True)
    currency_id = fields.Many2one(related='batch_id.currency_id', string='Moneda')
    reference = fields.Char('Referencia')
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
    company_id = fields.Many2one('res.company', string='Empresa', required=True, default=lambda self: self.env.company)
    bank = fields.Selection(BANK_SELECTION, string='Banco', required=True)
    period_id = fields.Many2one('erpec.payroll.period', string='Período de nómina', required=True,
        domain="[('company_id','=',company_id),('state','=','posted')]")

    def _company_account(self, profile):
        journal = self.company_id.erpec_payroll_bank_journal_id
        account = journal.bank_account_id
        if not account or not account.acc_number or account.erpec_bank_key != self.bank:
            raise ValidationError('La cuenta bancaria del diario de nómina (%s) debe ser de %s: asígnale la cuenta y su '
                                  'perfil de archivo de pago antes de generar el archivo.'
                                  % (journal.display_name or 'sin diario configurado', profile['label']))
        return account.acc_number

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
        company_account = self._company_account(profile)
        disbursements = self.period_id.disbursement_ids.filtered(
            lambda d: d.status in ('open', 'partial') and not d.currency_id.is_zero(d.residual))
        if not disbursements:
            raise ValidationError('No hay pagos de nómina pendientes en este período.')
        already = self.env['erpec.bank.export.line'].search([('disbursement_id', 'in', disbursements.ids)])
        if already:
            raise ValidationError('%s de estos pagos ya están en otro lote de exportación bancaria.' % len(already))
        rows, line_values = [], []
        reference = 'NOMINA %s' % self.period_id.name
        for sequence, disbursement in enumerate(disbursements, start=1):
            employee = disbursement.employee_id
            account = employee.bank_account_id
            if not account or not account.acc_number or account.erpec_bank_key != self.bank or not account.erpec_account_type:
                raise ValidationError('%s no tiene una cuenta en %s con tipo (ahorros/corriente) configurada.'
                    % (employee.name, profile['label']))
            id_type, id_number = beneficiary_identification(employee, profile)
            values = {'sequence': sequence, 'disbursement_id': disbursement.id, 'id_type': id_type, 'id_number': id_number,
                      'account_number': account.acc_number, 'account_type': account.erpec_account_type,
                      'beneficiary_name': employee.name, 'amount': disbursement.residual, 'reference': reference}
            rows.append(profile['row_builder'](self.env['erpec.bank.export.line'].new(values), company_account))
            line_values.append(values)
        content = '\n'.join(profile['delimiter'].join(row) for row in rows) + '\n'
        payload = content.encode('utf-8')
        checksum = hashlib.sha256(payload).hexdigest()
        name = 'PAGO-NOMINA-%s-%s-%s' % (self.period_id.name, self.bank.upper(), checksum[:8])
        batch = self.env['erpec.bank.export.batch'].with_context(_erpec_bank_export_token=_TOKEN).create({
            'name': name, 'company_id': self.company_id.id, 'bank': self.bank, 'period_id': self.period_id.id,
            'file': base64.b64encode(payload), 'filename': '%s.txt' % name, 'checksum': checksum,
        })
        self.env['erpec.bank.export.line'].with_context(_erpec_bank_export_token=_TOKEN).create(
            [dict(values, batch_id=batch.id) for values in line_values])
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.bank.export.batch', 'res_id': batch.id,
                'view_mode': 'form', 'target': 'current'}
