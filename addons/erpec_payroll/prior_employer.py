"""Comprobantes de retenciones del empleador anterior: registro idempotente y versionado (DI25-03, D8).

El pronunciamiento exige que la importación sea idempotente por trabajador, empleador de origen,
ejercicio y documento; que conserve versión y huella del archivo; y que una rectificación legítima
sustituya a la versión anterior con bitácora, sin duplicarla. Un comprobante nunca se edita ni se
elimina: registrar de nuevo la misma clave con otros importes crea la versión siguiente.
"""
import base64
import hashlib
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .models import _INTERNAL, manager

AMOUNT_FIELDS = ('taxable_income', 'iess', 'withheld_tax')
KEY_FIELDS = ('company_id', 'employee_id', 'year', 'origin_ruc', 'document_number')
PROTECTED_FIELDS = {'state', 'version', 'supersedes_id', 'change_log', 'file_hash', 'hash_origin'}
TOLERANCE = 0.005


def _money(value):
    return round(float(value or 0), 2)


class PriorEmployerCertificate(models.Model):
    _name = 'erpec.payroll.prior.employer'
    _description = 'Comprobante de retenciones del empleador anterior (versionado)'
    _inherit = ['mail.thread']
    _order = 'year desc, employee_id, origin_ruc, document_number, version desc'

    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company, index=True)
    employee_id = fields.Many2one('hr.employee', 'Trabajador', required=True, index=True)
    year = fields.Integer('Ejercicio fiscal', required=True)
    origin_ruc = fields.Char('RUC del empleador de origen', required=True, size=13)
    origin_name = fields.Char('Razón social del empleador de origen')
    document_number = fields.Char('Documento (Formulario 107 o comprobante)', required=True)
    issued_date = fields.Date('Fecha de emisión del comprobante', required=True)
    received_date = fields.Date('Fecha de recepción', required=True, default=fields.Date.today)
    document_file = fields.Binary('Archivo del comprobante', attachment=True,
                                  help='Opcional. Con archivo, la huella es la de su contenido; sin archivo, la de los valores capturados.')
    file_hash = fields.Char('Huella SHA-256', readonly=True, copy=False)
    hash_origin = fields.Selection([('file', 'Archivo'), ('values', 'Valores capturados')], 'Origen de la huella', readonly=True, copy=False)
    taxable_income = fields.Float('Ingresos gravados (otrosIngRenGrav)', digits=(16, 2), required=True)
    iess = fields.Float('Aporte personal IESS (aporPerIessConOtrosEmpls)', digits=(16, 2))
    withheld_tax = fields.Float('Impuesto retenido (valRetAsuOtrosEmpls)', digits=(16, 2))
    version = fields.Integer('Versión', readonly=True, default=1, copy=False)
    state = fields.Selection([('active', 'Vigente'), ('superseded', 'Sustituido')], 'Estado', readonly=True, default='active', copy=False, index=True)
    supersedes_id = fields.Many2one('erpec.payroll.prior.employer', 'Sustituye a', readonly=True, copy=False)
    change_log = fields.Text('Bitácora de cambios', readonly=True, copy=False)

    _sql_constraints = [
        ('version_unique', 'unique(company_id, employee_id, year, origin_ruc, document_number, version)',
         'Esta versión del comprobante ya existe.'),
    ]

    def init(self):
        # Una sola versión vigente por clave; la anterior queda sustituida, nunca duplicada.
        self.env.cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS erpec_prior_employer_active_unique ON erpec_payroll_prior_employer "
            "(company_id, employee_id, year, origin_ruc, document_number) WHERE state = 'active'")

    @api.depends('employee_id', 'year', 'origin_ruc', 'document_number', 'version')
    def _compute_display_name(self):
        for record in self:
            record.display_name = '%s · %s · %s · v%s' % (record.employee_id.name or '', record.year or '', record.document_number or '', record.version or '')

    # ── Registro idempotente ────────────────────────────────────────────────
    @api.model
    def _normalized(self, values):
        employee = self.env['hr.employee'].browse(values.get('employee_id'))
        if not employee.exists():
            raise ValidationError('El trabajador del comprobante no existe.')
        company = self.env['res.company'].browse(values.get('company_id') or employee.company_id.id or self.env.company.id)
        if employee.company_id != company:
            raise ValidationError('El trabajador pertenece a otra empresa.')
        year = int(values.get('year') or 0)
        if not 2000 <= year <= 2100:
            raise ValidationError('El ejercicio fiscal del comprobante no es válido.')
        ruc = (values.get('origin_ruc') or '').strip()
        if len(ruc) != 13 or not ruc.isdigit():
            raise ValidationError('El RUC del empleador de origen debe tener 13 dígitos.')
        if company.vat and ruc == company.vat:
            raise ValidationError('El comprobante debe provenir de un empleador distinto de esta empresa.')
        document = (values.get('document_number') or '').strip()
        if not document:
            raise ValidationError('Indica el número del documento.')
        amounts = {key: _money(values.get(key)) for key in AMOUNT_FIELDS}
        if min(amounts.values()) < 0:
            raise ValidationError('Los importes del comprobante deben ser no negativos.')
        if amounts['iess'] > amounts['taxable_income']:
            raise ValidationError('El aporte IESS no puede superar los ingresos gravados del comprobante.')
        issued = fields.Date.to_date(values.get('issued_date'))
        received = fields.Date.to_date(values.get('received_date')) or fields.Date.today()
        if not issued or issued > received or received > fields.Date.today():
            raise ValidationError('Las fechas de emisión y recepción del comprobante no son coherentes.')
        return dict(values, company_id=company.id, employee_id=employee.id, year=year, origin_ruc=ruc,
                    document_number=document, issued_date=issued, received_date=received, **amounts)

    @api.model
    def _fingerprint(self, values):
        content = values.get('document_file')
        if content:
            raw = base64.b64decode(content) if isinstance(content, (str, bytes)) else b''
            return hashlib.sha256(raw).hexdigest(), 'file'
        canonical = json.dumps({key: values[key] if key not in AMOUNT_FIELDS else _money(values[key]) for key in
                                (*KEY_FIELDS, *AMOUNT_FIELDS, 'issued_date')}, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest(), 'values'

    @api.model
    def _register_certificate(self, values):
        forbidden = PROTECTED_FIELDS & set(values)
        if forbidden:
            raise ValidationError('La versión, el estado y la huella los define el registro, no el usuario.')
        values = self._normalized(values)
        digest, origin = self._fingerprint(values)
        current = self.sudo().search([(name, '=', values[name]) for name in KEY_FIELDS] + [('state', '=', 'active')])
        if current:
            same_amounts = all(abs(current[key] - values[key]) <= TOLERANCE for key in AMOUNT_FIELDS)
            if current.file_hash == digest and same_amounts:
                return current.with_env(self.env)  # idempotente: el mismo insumo no crea otra versión
            differences = ', '.join('%s: %.2f → %.2f' % (key, current[key], values[key]) for key in AMOUNT_FIELDS
                                    if abs(current[key] - values[key]) > TOLERANCE) or 'sin cambio de importes (nueva huella)'
            log = 'v%s → v%s por %s el %s. Cambios: %s.' % (
                current.version, current.version + 1, self.env.user.name, fields.Datetime.now(), differences)
            token = self.with_context(_erpec_payroll_token=_INTERNAL).sudo()
            previous = token.browse(current.id)
            previous.write({'state': 'superseded', 'change_log': ((current.change_log or '') + '\n' + log).strip()})
            # El índice único admite una sola versión vigente: la anterior debe quedar sustituida en la base antes del INSERT.
            previous.flush_recordset(['state', 'change_log'])
            new = token.create(dict(values, version=current.version + 1, supersedes_id=current.id, file_hash=digest,
                                    hash_origin=origin, change_log=log))
            new.message_post(body='Rectificación registrada: ' + log)
            return new.with_env(self.env)
        return self.with_context(_erpec_payroll_token=_INTERNAL).sudo().create(
            dict(values, version=1, file_hash=digest, hash_origin=origin)).with_env(self.env)

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_payroll_token') is _INTERNAL:
            return super().create(values_list)
        manager(self.env)
        records = self.browse()
        for values in values_list:
            records |= self._register_certificate(values)
        return records

    def write(self, values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL and set(values) - {'message_follower_ids', 'message_ids'}:
            raise ValidationError('Un comprobante no se edita: registra de nuevo la misma clave con los importes corregidos para crear la versión siguiente.')
        return super().write(values)

    def unlink(self):
        raise ValidationError('Los comprobantes del empleador anterior no se eliminan; la rectificación crea una nueva versión.')

    def action_new_version(self):
        self.ensure_one()
        manager(self.env)
        keys = ('employee_id', 'year', 'origin_ruc', 'origin_name', 'document_number', 'issued_date', 'taxable_income', 'iess', 'withheld_tax')
        context = {'default_' + key: (self[key].id if isinstance(self[key], models.BaseModel) else self[key]) for key in keys}
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'view_mode': 'form', 'target': 'current', 'context': context,
                'name': 'Nueva versión del comprobante'}

    # ── Conciliación con las novedades de nómina ───────────────────────────
    @api.model
    def active_totals(self, company, employee, year):
        records = self.sudo().search([('company_id', '=', company.id), ('employee_id', '=', employee.id), ('year', '=', year), ('state', '=', 'active')])
        return {'count': len(records), **{key: _money(sum(records.mapped(key))) for key in AMOUNT_FIELDS}}

    @api.model
    def reconciliation_issues(self, company, year, lines, blocking_only=False):
        """D8: los valores de otros empleadores que declaran las novedades deben conciliar con los comprobantes vigentes.

        `lines` son todas las novedades del ejercicio que se consideran (contabilizadas más la del período en curso)."""
        issues = []
        for employee in lines.employee_id.sudo():
            own = lines.filtered(lambda line, employee=employee: line.employee_id.id == employee.id)
            declared = {key: _money(sum(own.mapped('other_employer_' + key))) for key in AMOUNT_FIELDS}
            certified = self.active_totals(company, employee, year)
            if not any(declared.values()):
                if certified['count'] and any(certified[key] for key in AMOUNT_FIELDS) and not blocking_only:
                    issues.append('%s: D8 · Hay comprobante vigente del empleador anterior (ingresos %.2f) que las novedades del ejercicio no incorporan.'
                                  % (employee.name, certified['taxable_income']))
                continue
            if not certified['count']:
                issues.append('%s: D8 · Otros empleadores: falta registrar el comprobante versionado del empleador anterior; '
                              'los importes de las novedades no se aceptan sin él.' % employee.name)
                continue
            gaps = [key for key in AMOUNT_FIELDS if abs(declared[key] - certified[key]) > TOLERANCE]
            if gaps:
                issues.append('%s: D8 · Las novedades declaran %s y los comprobantes vigentes suman %s: no concilian (%s).' % (
                    employee.name, ', '.join('%s %.2f' % (key, declared[key]) for key in AMOUNT_FIELDS),
                    ', '.join('%s %.2f' % (key, certified[key]) for key in AMOUNT_FIELDS), ', '.join(gaps)))
        return issues
