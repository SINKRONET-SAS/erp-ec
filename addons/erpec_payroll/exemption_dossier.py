"""Expediente verificado de exención personal (DI25-03, D4 sustituto y D7 tope de 100 canastas).

El pronunciamiento no acepta una referencia aislada: exige identificar a la persona, el documento y su
autoridad, las fechas de vigencia, impedir solapamientos y doble uso, y una validación documental previa.
El sistema no emite diagnósticos ni guarda datos de salud: solo registra la referencia, la autoridad y la
vigencia. La verificación la hace otra persona con rol de nómina (segregación de funciones); no equivale
a la consulta a la fuente oficial, que sigue siendo externa, y por eso el expediente lo deja dicho.
"""
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .engine import DISABILITY_BENEFIT_SCALE
from .models import _INTERNAL, manager

KINDS = [('substitute', 'Sustituto de persona con discapacidad'), ('special_holder', '100 canastas · titular'),
         ('special_dependent', '100 canastas · carga')]
ID_TYPES = [('C', 'Cédula'), ('P', 'Pasaporte')]
# El pronunciamiento (D7) exige rutas documentales separadas: cada condición tiene su propia autoridad y documento.
CONDITIONS = [('disability', 'Discapacidad'), ('catastrophic', 'Enfermedad catastrófica'), ('rare', 'Enfermedad rara'), ('orphan', 'Enfermedad huérfana')]
FROZEN = {'company_id', 'employee_id', 'year', 'kind', 'condition', 'document_ref', 'authority', 'issue_date', 'valid_from', 'valid_to',
          'person_id_type', 'person_id', 'relationship', 'disability_percentage'}


class ExemptionDossier(models.Model):
    _name = 'erpec.payroll.exemption.dossier'
    _description = 'Expediente verificado de exención personal'
    _inherit = ['mail.thread']
    _order = 'year desc, employee_id, kind, valid_from'

    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company, index=True)
    employee_id = fields.Many2one('hr.employee', 'Trabajador beneficiario', required=True, index=True)
    year = fields.Integer('Ejercicio fiscal', required=True)
    kind = fields.Selection(KINDS, 'Tipo', required=True)
    document_ref = fields.Char('Referencia del documento acreditante', required=True,
                               help='Número o código; no registrar diagnósticos ni copias del documento.')
    authority = fields.Char('Autoridad que lo emite', required=True)
    issue_date = fields.Date('Fecha de emisión', required=True)
    valid_from = fields.Date('Vigente desde', required=True)
    valid_to = fields.Date('Vigente hasta', required=True)
    condition = fields.Selection(CONDITIONS, 'Condición acreditada (100 canastas)',
                                 help='Discapacidad y enfermedad catastrófica, rara o huérfana se acreditan por rutas documentales distintas; no se mezclan.')
    person_id_type = fields.Selection(ID_TYPES, 'Tipo de identificación de la persona')
    person_id = fields.Char('Identificación de la persona sustituida o a cargo')
    relationship = fields.Char('Relación o dependencia económica declarada')
    disability_percentage = fields.Integer('Grado de discapacidad de la persona sustituida (%)')
    state = fields.Selection([('draft', 'Borrador'), ('verified', 'Verificado'), ('revoked', 'Revocado')], 'Estado',
                             default='draft', readonly=True, copy=False, index=True)
    verified_by = fields.Many2one('res.users', 'Verificado por', readonly=True, copy=False)
    verified_at = fields.Datetime('Verificado el', readonly=True, copy=False)
    verification_scope = fields.Text('Alcance de la verificación', readonly=True, copy=False)
    revoked_reason = fields.Text('Motivo de la revocación', copy=False, help='Se captura antes de revocar; queda en la bitácora.')

    # ── Validaciones estructurales ─────────────────────────────────────────
    @api.constrains('year', 'valid_from', 'valid_to', 'issue_date', 'kind', 'condition', 'person_id', 'person_id_type', 'relationship', 'disability_percentage')
    def _check_dossier(self):
        for dossier in self:
            if not 2000 <= dossier.year <= 2100:
                raise ValidationError('El ejercicio del expediente no es válido.')
            if dossier.valid_from > dossier.valid_to:
                raise ValidationError('La vigencia del expediente termina antes de empezar.')
            if dossier.valid_from < date(dossier.year, 1, 1) or dossier.valid_to > date(dossier.year, 12, 31):
                raise ValidationError('La vigencia debe estar dentro del ejercicio %s; para otro ejercicio registra otro expediente.' % dossier.year)
            if dossier.issue_date > fields.Date.today():
                raise ValidationError('La fecha de emisión del documento no puede ser futura.')
            if dossier.kind in ('substitute', 'special_dependent') and not (dossier.person_id and dossier.person_id.strip()):
                raise ValidationError('Este tipo de expediente requiere la identificación de la persona.')
            if dossier.kind == 'substitute':
                if not dossier.person_id_type:
                    raise ValidationError('Indica el tipo de identificación de la persona sustituida.')
                if not DISABILITY_BENEFIT_SCALE[0][0] <= dossier.disability_percentage <= 100:
                    raise ValidationError('El sustituto requiere el grado de discapacidad (desde %s %%) de la persona sustituida.' % DISABILITY_BENEFIT_SCALE[0][0])
            if dossier.kind in ('special_holder', 'special_dependent'):
                if not dossier.condition:
                    raise ValidationError('Indica la condición acreditada: discapacidad, enfermedad catastrófica, rara o huérfana.')
                if dossier.condition == 'disability' and not DISABILITY_BENEFIT_SCALE[0][0] <= dossier.disability_percentage <= 100:
                    raise ValidationError('La discapacidad exige el grado (desde %s %%) que consta en el documento.' % DISABILITY_BENEFIT_SCALE[0][0])
            elif dossier.condition:
                raise ValidationError('La condición solo aplica a los expedientes de 100 canastas.')
            if dossier.kind == 'special_dependent' and not (dossier.relationship and dossier.relationship.strip()):
                raise ValidationError('Indica la relación o dependencia económica de la carga.')
            if dossier.employee_id.company_id != dossier.company_id:
                raise ValidationError('El trabajador pertenece a otra empresa.')

    # ── Inmutabilidad ─────────────────────────────────────────────────────
    def write(self, values):
        if self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            if any(dossier.state != 'draft' for dossier in self) and (set(values) & FROZEN or 'state' in values):
                raise ValidationError('Un expediente verificado o revocado no se edita: revócalo y registra uno nuevo.')
            guarded = {'state', 'verified_by', 'verified_at', 'verification_scope'}
            if not all(dossier.state == 'verified' for dossier in self):
                guarded.add('revoked_reason')  # el motivo solo se captura mientras el expediente está verificado
            if set(values) & guarded:
                raise ValidationError('El estado y la verificación se cambian solo con sus acciones.')
        return super().write(values)

    @api.model_create_multi
    def create(self, values_list):
        manager(self.env)
        if any(set(values) & {'state', 'verified_by', 'verified_at', 'verification_scope', 'revoked_reason'} for values in values_list):
            raise ValidationError('El estado y la verificación se cambian solo con sus acciones.')
        return super().create(values_list)

    def unlink(self):
        if any(dossier.state != 'draft' for dossier in self):
            raise ValidationError('Un expediente verificado o revocado no se elimina; revócalo con su motivo.')
        return super().unlink()

    # ── Verificación ─────────────────────────────────────────────────────
    def _conflicts(self):
        """Solapamientos y doble uso frente a otros expedientes verificados (sin revelar datos ajenos)."""
        self.ensure_one()
        others = self.sudo().search([('id', '!=', self.id), ('state', '=', 'verified'), ('year', '=', self.year)])
        problems = []
        for other in others:
            overlap = other.valid_from <= self.valid_to and self.valid_from <= other.valid_to
            if self.kind == 'substitute' and other.kind == 'substitute':
                if other.person_id == self.person_id and overlap:
                    problems.append('La misma persona sustituida ya tiene un sustituto verificado en el período (no puede haber dos a la vez).')
                if other.employee_id == self.employee_id and other.person_id != self.person_id:
                    problems.append('Este trabajador ya usa el beneficio de sustituto para otra persona en el ejercicio (solo se usa una vez).')
            elif self.kind == 'special_dependent' and other.kind == 'special_dependent' and other.person_id == self.person_id and overlap:
                problems.append('La misma carga ya figura en otro expediente verificado del ejercicio (doble uso).')
            elif self.kind == 'special_holder' and other.kind == 'special_holder' and other.employee_id == self.employee_id and overlap:
                problems.append('El titular ya tiene un expediente verificado que se solapa.')
        return list(dict.fromkeys(problems))

    def action_verify(self):
        manager(self.env)
        for dossier in self:
            if dossier.state != 'draft':
                raise ValidationError('Solo se verifica un expediente en borrador.')
            if dossier.create_uid == self.env.user:
                raise ValidationError('La verificación la hace otra persona distinta de quien registró el expediente (segregación de funciones).')
            problems = dossier._conflicts()
            if problems:
                raise ValidationError('No se puede verificar:\n' + '\n'.join(problems))
            dossier.with_context(_erpec_payroll_token=_INTERNAL).write({
                'state': 'verified', 'verified_by': self.env.user.id, 'verified_at': fields.Datetime.now(),
                'verification_scope': 'Validación documental interna de referencia, autoridad, identidad, vigencia y unicidad. '
                                      'No sustituye la consulta a la autoridad competente ni emite diagnósticos.'})
            dossier.message_post(body='Expediente verificado por %s.' % self.env.user.name)
        return True

    def action_revoke(self):
        manager(self.env)
        for dossier in self:
            if dossier.state != 'verified':
                raise ValidationError('Solo se revoca un expediente verificado.')
            reason = (dossier.revoked_reason or '').strip() or 'Revocado por %s.' % self.env.user.name
            dossier.with_context(_erpec_payroll_token=_INTERNAL).write({'state': 'revoked', 'revoked_reason': reason})
            dossier.message_post(body='Expediente revocado: ' + reason)
        return True

    # ── Consulta para el motor ───────────────────────────────────────────
    @api.model
    def verified_for(self, employee, year, kinds):
        return self.sudo().search([('employee_id', '=', employee.id), ('year', '=', year), ('kind', 'in', list(kinds)), ('state', '=', 'verified')])

    @api.model
    def covers_year(self, dossiers, year):
        """True si los expedientes verificados cubren el ejercicio completo sin huecos."""
        days = set()
        for dossier in dossiers:
            current = dossier.valid_from
            while current <= dossier.valid_to:
                days.add(current)
                current = date.fromordinal(current.toordinal() + 1)
        total = (date(year, 12, 31) - date(year, 1, 1)).days + 1
        return len(days) == total

    @api.model
    def substitution_claim(self, dossiers, year):
        """Reclamo de sustituto proporcional al tiempo acreditado (días → meses, redondeo al mes más cercano)."""
        if not dossiers:
            return None, ['D4 · Sustituto: no existe expediente verificado con vigencia.']
        percentages = set(dossiers.mapped('disability_percentage'))
        people = set(dossiers.mapped('person_id'))
        if len(people) > 1:
            return None, ['D4 · El sustituto solo puede usar el beneficio una vez: hay expedientes de más de una persona.']
        if len(percentages) > 1:
            return None, ['D4 · Los expedientes de la misma persona sustituida declaran grados de discapacidad distintos.']
        ordered = dossiers.sorted('valid_from')
        for left, right in zip(ordered, ordered[1:]):
            if right.valid_from <= left.valid_to:
                return None, ['D4 · Los expedientes del sustituto se solapan.']
        covered = sum((dossier.valid_to - dossier.valid_from).days + 1 for dossier in ordered)
        total = (date(year, 12, 31) - date(year, 1, 1)).days + 1
        months = max(1, min(12, round(covered * 12 / total)))
        return {'kind': 'substitute', 'percentage': percentages.pop(), 'months': months}, []
