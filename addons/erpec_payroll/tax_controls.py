"""Controles automáticos DI25-03: bloqueos objetivos, sin homologación implícita."""
import hashlib
import json
from calendar import monthrange
from datetime import date
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from . import engine, parameters_seal
from .models import manager


class Employee(models.Model):
    _inherit = 'hr.employee'

    ec_rdep_validation_notice = fields.Text(
        'Validación automática del ejercicio', compute='_compute_tax_validation',
        groups='erpec_payroll.group_payroll_manager')

    @api.depends(lambda self: ['birthday', 'identification_id'] + [
        key for key, field in self._fields.items()
        if key.startswith('ec_rdep_') and field.store and not field.compute])
    def _compute_tax_validation(self):
        for employee in self:
            year = employee.ec_rdep_exemption_year or employee.ec_rdep_special_expense_year or fields.Date.today().year
            status = employee._rdep_personal_status(year)
            employee.ec_rdep_validation_notice = '\n'.join(status['issues'] + status['notes']) or (
                'Sin incidencias documentales detectadas para %s. Esto no valida la autenticidad del soporte ni homologa el RDEP.' % year)

    def _rdep_personal_status(self, year, as_of=None):
        status = super()._rdep_personal_status(year, as_of)
        dossiers = self.env['erpec.payroll.exemption.dossier']
        # Un texto libre no acredita autoridad, vigencia, vínculo ni unicidad (D4/D7): hace falta un expediente verificado.
        if self.ec_rdep_special_expense not in (False, 'none'):
            kind = {'holder': 'special_holder', 'dependent': 'special_dependent'}.get(self.ec_rdep_special_expense)
            verified = dossiers.verified_for(self, year, [kind]) if kind else dossiers
            if not (verified and dossiers.covers_year(verified, year)):
                status['special_expense'] = False
                status['issues'].append(
                    'D7 · 100 canastas bloqueadas: falta un expediente verificado que cubra todo el ejercicio '
                    '(autoridad, identidad, vigencia y, para una carga, vínculo y dependencia). '
                    'La referencia aislada no acredita la condición. No registrar diagnósticos.')
        if self.ec_rdep_disability_type == '02':
            accredited = [claim for claim in status['claims'] if claim['kind'] == 'substitute']
            status['claims'] = [claim for claim in status['claims'] if claim['kind'] != 'substitute']
            verified = dossiers.verified_for(self, year, ['substitute'])
            if verified:
                if self.ec_rdep_disability_id and any(item.person_id != self.ec_rdep_disability_id for item in verified):
                    status['issues'].append('D4 · La persona sustituida de la ficha no coincide con la del expediente verificado.')
                elif accredited:
                    claim, problems = dossiers.substitution_claim(verified, year)
                    if claim:
                        status['claims'].append(claim)
                    status['issues'].extend(problems)
            else:
                status['issues'].append(
                    'D4 · Sustituto bloqueado: falta un expediente verificado con inicio/fin y control de '
                    'solapamientos. El número de meses y una referencia no prueban unicidad.')
                if self.ec_rdep_disability_id:
                    duplicates = self.sudo().search_count([
                        ('id', '!=', self.id), ('ec_rdep_disability_type', '=', '02'),
                        ('ec_rdep_disability_id', '=', self.ec_rdep_disability_id),
                        ('ec_rdep_exemption_year', '=', year)])
                    if duplicates:
                        status['issues'].append(
                            'D4 · Conflicto: otra ficha declara a la misma persona sustituida en el ejercicio. '
                            'Debe conciliarse la vigencia sin revelar datos de otras empresas.')
        return status


class Line(models.Model):
    _inherit = 'erpec.payroll.line'

    def _accumulated_history(self):
        """Meses anteriores contabilizados del mismo ejercicio: base gravable sin IESS y retención ya efectuada (D6)."""
        self.ensure_one()
        period = self.period_id
        prior = self.env['erpec.payroll.line'].sudo().search([
            ('employee_id', '=', self.employee_id.id), ('period_id.state', '=', 'posted'), ('period_id.company_id', '=', period.company_id.id),
            ('period_id.year', '=', period.year), ('period_id.month', '<', period.month), ('period_id', '!=', period.id)])
        base = tax = 0.0
        for line in prior:
            result = json.loads(line.result or '{}')
            base += result.get('base', 0.0) - result.get('personal_iess', 0.0)
            tax += result.get('tax', 0.0)
        return {'months': len(prior), 'base': round(base, 2), 'tax': round(tax, 2)}

    def _inputs(self):
        data = super()._inputs()
        history = self._accumulated_history()
        if history['months']:
            data.update({'prior_months': history['months'], 'prior_base': history['base'], 'prior_tax': history['tax']})
        period = self.period_id
        certified = self.env['erpec.payroll.prior.employer'].active_totals(period.company_id, self.employee_id, period.year)
        if certified['count']:
            data.update({'other_income': certified['taxable_income'], 'other_iess': certified['iess'], 'other_withheld': certified['withheld_tax']})
        return data


class Period(models.Model):
    _inherit = 'erpec.payroll.period'

    tax_validation_notice = fields.Text('Controles tributarios automáticos', compute='_compute_tax_validation')
    tax_validation_hash = fields.Char('Huella tributaria revisada', readonly=True, copy=False)

    def _tax_control_payload(self):
        self.ensure_one()
        employees = self.line_ids.employee_id.sudo().sorted('id')
        keys = ['birthday', 'identification_id'] + [
            key for key, field in employees._fields.items()
            if key.startswith('ec_rdep_') and field.store and not field.compute]
        return {
            'control_revision': 'DI25-03-controles-18.0.1.13.0',
            'year': self.year, 'month': self.month, 'policy': self.policy_id.parameters,
            'employees': employees.read(sorted(keys)),
            'lines': [(line.id, line._copy_inputs(), line.result) for line in self.line_ids.sorted('id')],
            'prior_employer': self.env['erpec.payroll.prior.employer'].sudo().search([
                ('company_id', '=', self.company_id.id), ('year', '=', self.year), ('state', '=', 'active')]).sorted('id').read(['employee_id', 'version', 'file_hash']),
            'history': self.env['erpec.payroll.period'].search([
                ('company_id', '=', self.company_id.id), ('year', '=', self.year),
                ('id', '!=', self.id), ('state', '=', 'posted')]).sorted('id').read(['id', 'month', 'write_date']),
        }

    def _tax_signature(self):
        return hashlib.sha256(json.dumps(self._tax_control_payload(), sort_keys=True, default=str).encode('utf-8')).hexdigest()

    def _seal_issues(self):
        """Parámetros oficiales sellados frente a la política y las constantes del motor (bloquean el cálculo)."""
        self.ensure_one()
        try:
            parameters = json.loads(self.policy_id.parameters or '{}')
        except ValueError:
            parameters = {}
        return parameters_seal.verify_policy_parameters(self.year, parameters) + parameters_seal.verify_engine_constants(self.year, engine)

    def _tax_control_issues(self, blocking_only=False):
        self.ensure_one()
        issues = ['Parámetros oficiales · %s' % message for message in self._seal_issues()]
        if not blocking_only:
            issues.extend(parameters_seal.year_notice(self.year))
        for line in self.line_ids:
            employee = line.employee_id.sudo()
            status = employee._rdep_personal_status(self.year, date(self.year, self.month, monthrange(self.year, self.month)[1]))
            issues.extend('%s: %s' % (employee.name, message) for message in status['issues'])
            if line.other_employer_iess > line.other_employer_taxable_income:
                issues.append('D8 · El IESS de otro empleador supera sus ingresos gravados.')
            if employee.ec_rdep_ben_galpg == 'SI':
                issues.append('Caso 11 · Galápagos requiere elegibilidad acreditada; el factor 1,803 no la demuestra.')
            if employee.ec_rdep_treaty_applies == 'SI' or employee.ec_rdep_residence_country not in (False, '593'):
                issues.append('Caso 11 · Residencia extranjera o convenio sin regla aprobada: cierre bloqueado.')
            if line.employer_assumed_tax or line.other_general_interest_income:
                issues.append('Caso 11 · Impuesto asumido u otros ingresos sin regla aprobada: cierre bloqueado.')
            if line.benefit_line_ids and not blocking_only:
                issues.append(
                    'Caso 3 · Beneficios propios: falta matriz aprobada de incidencia por concepto '
                    '(IR, IESS, décimos, vacaciones, reserva, contabilidad y RDEP).')
        # D8: los importes de otros empleadores concilian con el comprobante vigente (registro versionado e idempotente).
        posted = self.env['erpec.payroll.line'].search([
            ('employee_id', 'in', self.line_ids.employee_id.ids), ('period_id', '!=', self.id), ('period_id.state', '=', 'posted'),
            ('period_id.company_id', '=', self.company_id.id), ('period_id.year', '=', self.year)])
        issues.extend(self.env['erpec.payroll.prior.employer'].reconciliation_issues(
            self.company_id, self.year, self.line_ids | posted, blocking_only=blocking_only))
        if self.state in ('calculated', 'closed') and not self.tax_validation_hash:
            issues.append('Cálculo anterior sin huella tributaria: recalcula las novedades abiertas o tramita una corrección del cierre.')
        if self.tax_validation_hash and self.tax_validation_hash != self._tax_signature():
            issues.append('Los datos tributarios o períodos contabilizados cambiaron después del cálculo; vuelve a calcular antes del cierre.')
        return list(dict.fromkeys(issues))

    @api.depends(lambda self: ['state', 'tax_validation_hash', 'policy_id.parameters', 'line_ids.result',
        'line_ids.benefit_line_ids.amount', 'line_ids.employee_id.birthday',
        'line_ids.other_employer_taxable_income', 'line_ids.other_employer_iess',
        'line_ids.other_employer_withheld_tax', 'line_ids.employer_assumed_tax',
        'line_ids.other_general_interest_income'] + [
        'line_ids.employee_id.' + key for key, field in self.env['hr.employee']._fields.items()
        if key.startswith('ec_rdep_') and field.store and not field.compute])
    def _compute_tax_validation(self):
        for period in self:
            issues = period._tax_control_issues()
            period.tax_validation_notice = '\n'.join(issues) or (
                'Controles estructurales sin incidencias. La retención mensual continúa siendo una '
                'proyección: falta reliquidación acumulada y conciliación anual para aceptación tributaria.')

    def action_calculate(self):
        seal = self._seal_issues() if len(self) == 1 else [m for period in self for m in period._seal_issues()]
        if seal:
            raise ValidationError('Cálculo bloqueado: los parámetros no coinciden con los oficiales sellados.\n' + '\n'.join(seal))
        result = super().action_calculate()
        self._update({'tax_validation_hash': self._tax_signature()})
        return result

    def action_close(self):
        self._lock()
        issues = self._tax_control_issues(blocking_only=True)
        if issues:
            raise ValidationError('Cierre bloqueado por validación automática.\n' + '\n'.join(issues))
        return super().action_close()

    def action_post(self):
        # También se revalida entre cierre y contabilización. Un asiento existente es idempotente.
        if not self.move_id:
            self._lock()
            issues = self._tax_control_issues(blocking_only=True)
            if issues:
                raise ValidationError('Contabilización bloqueada por validación automática.\n' + '\n'.join(issues))
        return super().action_post()

    @api.model_create_multi
    def create(self, values_list):
        if any('tax_validation_hash' in values for values in values_list):
            raise ValidationError('La huella de validación solo se genera al calcular.')
        return super().create(values_list)

    def write(self, values):
        from .models import _INTERNAL
        if 'tax_validation_hash' in values and self.env.context.get('_erpec_payroll_token') is not _INTERNAL:
            raise ValidationError('La huella de validación solo se genera al calcular.')
        return super().write(values)

    def action_validate_tax_controls(self):
        self.ensure_one()
        manager(self.env)
        self.check_access('read')
        issues = self._tax_control_issues()
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Validación tributaria automática',
                           'message': '\n'.join(issues) if issues else 'Sin incidencias estructurales. Aceptación tributaria pendiente.',
                           'type': 'warning' if issues else 'info', 'sticky': True}}


class RdepAnnex(models.Model):
    _inherit = 'erpec.payroll.rdep'

    def _ledger_issues(self, periods):
        """Caso 10: cada período contabilizado debe conciliar con su asiento (importes recalculados desde el resultado inmutable)."""
        from .models import CONCEPTS
        issues = []
        currency = self.company_id.currency_id
        for period in periods:
            move = period.move_id
            if not move or move.state != 'posted':
                issues.append('Conciliación · %s/%s: el período figura contabilizado, pero su asiento no existe o no está publicado.' % (period.month, period.year))
                continue
            expected = {'debit': 0.0, 'credit': 0.0}
            for line in period.line_ids:
                result = json.loads(line.result or '{}')
                for concept, _label in CONCEPTS:
                    mapping = period.policy_id.mapping_ids.filtered(lambda item, concept=concept: item.concept == concept)
                    amount = result.get(concept, 0)
                    if amount and mapping:
                        expected['debit'] += amount if mapping.debit_id else 0.0
                        expected['credit'] += amount if mapping.credit_id else 0.0
            actual = {'debit': sum(move.line_ids.mapped('debit')), 'credit': sum(move.line_ids.mapped('credit'))}
            for side, label in (('debit', 'débitos'), ('credit', 'créditos')):
                if currency.compare_amounts(expected[side], actual[side]):
                    issues.append('Conciliación · %s/%s: los %s del asiento (%.2f) no coinciden con la nómina (%.2f).' % (
                        period.month, period.year, label, actual[side], expected[side]))
        return issues

    def _settlement_notes(self, periods):
        """Caso 4: devengo y pago de cada período frente a su asiento. Son avisos: la conciliación contable la acepta contabilidad."""
        notes = []
        for period in periods:
            move = period.move_id
            if not move:
                continue
            label = '%s/%s' % (period.month, period.year)
            if (move.date.year, move.date.month) != (period.year, period.month):
                notes.append('Aviso de conciliación · devengo %s: el asiento está fechado el %s, fuera del mes de la nómina.' % (label, move.date))
            account = period.policy_id.mapping_ids.filtered(lambda item: item.concept == 'net').credit_id
            if not account:
                continue
            lines = move.line_ids.filtered(lambda line, account=account: line.account_id == account)
            payable = sum(lines.mapped('credit'))
            if not account.reconcile:
                notes.append('Aviso de conciliación · pago %s: la cuenta %s no es conciliable; no puede verificarse el pago de %.2f.' % (label, account.code, payable))
                continue
            pending = abs(sum(lines.mapped('amount_residual')))
            if pending > 0.005:
                notes.append('Aviso de conciliación · pago %s: por pagar %.2f, pagado %.2f, pendiente %.2f.' % (label, payable, payable - pending, pending))
        return notes

    def _coverage_issues(self, periods):
        issues = super()._coverage_issues(periods)
        issues.extend(self._ledger_issues(periods))
        return issues

    def _compute_review_notice(self):
        super()._compute_review_notice()
        for annex in self:
            gaps = []
            for line in annex.line_ids:
                if line.months_remaining == 0 and abs(line.tax_difference) > 0.01:
                    gaps.append('Conciliación D6 · %s: el ejercicio cierra con una diferencia de %.2f entre el impuesto anual y lo retenido; '
                                'requiere regularización en la declaración anual.' % (line.employee_id.name, line.tax_difference))
                elif line.months_remaining and line.future_monthly_retention > 0.005:
                    gaps.append('Conciliación D6 · %s: saldo proyectado por retener de %.2f al mes durante los %s meses que faltan; '
                                'la reliquidación lo aplica en cada cálculo y no reabre nóminas contabilizadas.' % (
                                    line.employee_id.name, line.future_monthly_retention, line.months_remaining))
            gaps += annex._settlement_notes(annex._posted_periods())
            if gaps:
                annex.review_notice = ((annex.review_notice or '') + '\n' + '\n'.join(gaps)).strip()
