"""Datos, agregador anual y XML de vista previa para el anexo RDEP del SRI.

Cubre los campos de datRetRelDepTyp del Esquema RDEP 2023.xsd (SRI), fuente
primaria descargada y leída el 13-09-2026 (addons/erpec_payroll/xsd/
Esquema_RDEP_2023.xsd). El significado de cada campo proviene, en este orden
de confianza: (1) la propia documentación XSD, (2) el Instructivo del
Formulario 107 del SRI (mismo concepto de retención, per relación de
dependencia) y (3) el nombre literal del campo cuando ninguna fuente lo
documenta explícitamente — estos últimos quedan marcados en el código y en
docs/ALCANCE_ATS_RDEP.md. No se inventan catálogos ni fórmulas legales.

Acumula los flujos contabilizados del motor mensual. Aplica annual_income_tax
a la base efectiva y gastos declarados del año; no copia proyecciones de un mes.
Las exenciones y regímenes sin oráculo aprobado impiden generar el XML. Los campos que el motor no puede calcular
(participación de utilidades, salario digno, ingresos/aportes con otros
empleadores, impuesto asumido por el empleador y deducciones desglosadas de
gastos personales) se capturan como novedades explícitas del período, igual
que wage/bonus/commission ya se capturan hoy; no se completan con ceros
salvo que el responsable de nómina realmente los declare así.

No genera un anexo homologado ni presentado ante el SRI: la vista previa XML
se valida contra el esquema oficial descargado, pero no hay firma, envío ni
autoridad SRI involucrados.

`deducEducartcult` corresponde a la categoría "Educación, arte y cultura"
que el SRI usa desde la reforma tributaria de 2023 para agrupar en una sola
categoría lo que antes eran gastos de educación y de arte/cultura por
separado. Confirmado directamente por el Boletín NAC-COM-26-006 del SRI
(06-02-2026), que lista "alimentación, educación, arte y cultura, salud,
vestimenta, vivienda y turismo nacional" como los rubros vigentes para la
proyección de gastos personales 2026. Los campos legados `deducEduca`/
`deducArtycult` (opcionales en el esquema) ya no se usan para períodos
corrientes y se omiten en la vista previa.

`benGalpg` corresponde al Régimen Especial de la Provincia de Galápagos
(LOREG). El mismo Boletín NAC-COM-26-006 confirma que, para el ejercicio
fiscal 2026, "en Galápagos el cálculo se ajusta con el Índice de Precios al
Consumidor Especial (IPCEG) de 1,803" sobre el tope de gastos personales.
Esto es vigente y activo para 2026, no derogado: una resolución anterior
específica de Galápagos (NAC-DGERCGC16-00000443, 2016) fue derogada en 2021
(NAC-DGERCGC21-00000049), pero el ajuste por IPCEG documentado en el
boletín de 2026 es el mecanismo actualmente vigente. El campo se declara
explícitamente por empleado ("NO" por defecto para quienes no tributan en
Galápagos) porque el ERP no determina automáticamente la residencia fiscal
del empleado en el régimen especial.

Importante: desde la reforma de 2023 el SRI ya NO aplica un tope individual
por categoría de gasto personal (el Instructivo del Formulario 107, de
origen anterior a esa reforma, describía topes por categoría que ya no
rigen). El tope vigente es único y total, expresado en canastas básicas
familiares (CBF) según las cargas familiares del empleado (7 canastas sin
cargas, hasta 20 con 5 o más), multiplicado por el factor IPCEG en
Galápagos. `parameters['expense_limit']` de la política de nómina ya
representa ese tope de 0 cargas (verificado: 5752.60 = 7 × 821.80, CBF de
enero de 2026); `erpec_payroll.engine.personal_expense_cap` es la única
implementación de esta regla, y tanto el cálculo mensual (`engine.calculate`,
vía `Line._inputs` que agrega `dependents_count`/`galapagos` del empleado) como
este agregador anual la reutilizan sin duplicarla.
"""
import json
import unicodedata
from pathlib import Path
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from .models import manager
from .engine import (personal_expense_cap, annual_income_tax, apply_personal_exemption, money, number,
                     resolve_exemption_claims, resolve_special_expense)

SPECIAL_EXPENSE = [('none', 'General · según cargas'), ('holder', '100 canastas · titular'), ('dependent', '100 canastas · carga familiar')]
DISABILITY_TYPES = [
    ('00', '00 (sin descripción en el esquema oficial SRI; confirmar en la ficha técnica antes de usar)'),
    ('01', '01 · Trabajador con discapacidad'),
    ('02', '02 · Actúa como sustituto de una persona con discapacidad'),
    ('03', '03 · Cónyuge, pareja en unión de hecho o hijo con discapacidad bajo su cuidado'),
    ('04', '04 · No aplica'),
]
DISABILITY_ID_TYPES = [('C', 'C · Cédula'), ('P', 'P · Pasaporte'), ('E', 'E · Extranjero'), ('N', 'N · No aplica')]
ID_TYPES = [('C', 'C · Cédula'), ('P', 'P · Pasaporte'), ('E', 'E · Extranjero')]
TREATY_APPLIES = [('SI', 'SI'), ('NO', 'NO'), ('NA', 'NA'), ('SD', 'SD · Sin dato')]
# residenciaTrab (resciTyp): el esquema solo documenta "Codigo de residencia del
# trabajador", sin describir 00/01/02; se listan como códigos crudos.
FISCAL_RESIDENCE = [('00', '00'), ('01', '01'), ('02', '02')]
BEN_GALPG = [('SI', 'SI'), ('NO', 'NO')]

RDEP_FLOW_KEYS = ('gross', 'salary', 'overtime', 'thirteenth', 'fourteenth', 'reserve_iess', 'personal_iess', 'tax', 'base')
RDEP_LINE_INPUT_KEYS = (
    'annual_profit_sharing', 'decent_wage_compensation', 'other_employer_taxable_income',
    'other_employer_iess', 'other_employer_withheld_tax', 'employer_assumed_tax',
    'other_general_interest_income', 'expense_housing', 'expense_health', 'expense_education',
    'expense_food', 'expense_clothing', 'expense_art_culture', 'expense_tourism',
)
EXPENSE_CATEGORY_KEYS = ('expense_housing', 'expense_health', 'expense_education', 'expense_art_culture', 'expense_food', 'expense_clothing', 'expense_tourism')
# Boletín NAC-COM-26-006 (SRI, 06-02-2026) y fuentes tributarias consistentes con él:
# desde la reforma de 2023 ya NO hay tope individual por categoría de gasto personal.
# Hay un solo tope anual total, expresado en canastas básicas familiares (CBF) de enero
# del año, que crece según las cargas familiares del contribuyente, y que se multiplica
# por el Índice de Precios al Consumidor Especial de Galápagos (IPCEG) para quienes
# tributan en ese régimen. La constante y el cálculo viven en erpec_payroll.engine
# (personal_expense_cap), reutilizados aquí sin duplicarlos: el motor mensual ya los
# aplica sobre expense_limit (engine.calculate) y el agregador RDEP los reutiliza
# para validar el mismo tope sobre el total anual declarado.


def _basic_fraction(policy):
    params = json.loads(policy.parameters)
    brackets = [bracket for bracket in params['tax_brackets'] if bracket['from'] == 0]
    return brackets[0]['to']


def _personal_expense_cap(policy, dependents_count, galapagos, special_expense=False):
    expense_limit = json.loads(policy.parameters)['expense_limit']
    return float(personal_expense_cap(expense_limit, dependents_count, galapagos, special_expense=special_expense))


def _ascii_name(value):
    # apeNombreTyp del esquema RDEP exige [A-Za-z\s]{2,100}; sin tildes ni Ñ.
    # Se transcribe el nombre real sin acentos solo para este XML; no se
    # modifica el nombre almacenado en hr.employee.
    normalized = unicodedata.normalize('NFKD', value or '')
    stripped = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return ''.join(ch if ch.isalpha() or ch.isspace() else ' ' for ch in stripped).strip() or 'S N'


def _split_name(value):
    words = (value or '').split()
    if len(words) < 2:
        return _ascii_name(value), _ascii_name(value)
    half = (len(words) + 1) // 2
    return _ascii_name(' '.join(words[:half])), _ascii_name(' '.join(words[half:]))


class Company(models.Model):
    _inherit = 'res.company'
    ec_rdep_employer_type = fields.Selection(
        [('PRIVADO_MIXTO', 'PRIVADO_MIXTO'), ('PUBLICO', 'PUBLICO')],
        string='Tipo de empleador (RDEP)',
        help='Campo tipoEmpleador del Esquema RDEP 2023.xsd del SRI.')
    ec_rdep_social_security_entity = fields.Selection(
        [('IESS', 'IESS'), ('ISSFA_ISSPOL', 'ISSFA_ISSPOL')],
        string='Ente de seguridad social (RDEP)',
        help='Campo enteSegSocial del Esquema RDEP 2023.xsd del SRI.')


class Employee(models.Model):
    _inherit = 'hr.employee'
    ec_rdep_disability_type = fields.Selection(
        DISABILITY_TYPES, string='Discapacidad (RDEP)',
        help='Campo discapTyp del Esquema RDEP 2023.xsd; etiquetas 01-04 tomadas de la documentación del propio esquema.')
    ec_rdep_disability_percentage = fields.Integer('Porcentaje de discapacidad (RDEP)')
    ec_rdep_disability_id_type = fields.Selection(DISABILITY_ID_TYPES, string='Identificación del titular de la discapacidad (RDEP)')
    ec_rdep_disability_id = fields.Char('Número de identificación del titular de la discapacidad (RDEP)')
    ec_rdep_dependents_count = fields.Integer(
        'Cargas para rebaja de gastos personales (RDEP)',
        help='Campo numCargRebGastPers del esquema SRI; admite de 0 a 5.')
    ec_rdep_treaty_applies = fields.Selection(TREATY_APPLIES, string='Aplica convenio doble imposición (RDEP)')
    ec_rdep_id_type = fields.Selection(ID_TYPES, string='Tipo de identificación (RDEP)', help='Campo tipIdRet del esquema SRI.')
    ec_rdep_fiscal_residence = fields.Selection(
        FISCAL_RESIDENCE, string='Código de residencia (RDEP)',
        help='Campo residenciaTrab del esquema SRI; el esquema no documenta el significado de cada código, confirmar con la ficha técnica antes de usar.')
    ec_rdep_residence_country = fields.Char(
        'País de residencia (RDEP)', default='593',
        help='Campo paisResidencia: código SRI de 3 dígitos. 593 = Ecuador. Catálogo completo de países en addons/erpec_fiscal_native/ats_catalog.py (COUNTRY_CODES).')
    ec_rdep_ben_galpg = fields.Selection(
        BEN_GALPG, string='Beneficiario Régimen Especial de Galápagos (RDEP)', default='NO',
        help='Campo benGalpg del esquema SRI: indica si el empleado tributa bajo el Régimen Especial de la Provincia de Galápagos (LOREG). Confirmado vigente para 2026 por el Boletín NAC-COM-26-006 del SRI (06-02-2026): en Galápagos, el tope de gastos personales se multiplica por el Índice de Precios al Consumidor Especial de Galápagos (IPCEG), 1.803. Marcar SI aplica el factor 1.803 al tope de gastos personales de este empleado; "NO" es el valor por defecto para empleados fuera de Galápagos.')
    ec_rdep_establishment = fields.Char('Establecimiento (RDEP)', help='Campo estab: 3 dígitos, código de establecimiento del RUC donde trabaja el empleado.')
    # Acreditación de exenciones personales (LRTI art. 9 num. 12; Reglamento LRTI arts. 49-50).
    # Se guarda solo la referencia del documento, nunca su contenido médico.
    ec_rdep_exemption_year = fields.Integer(
        'Año de la acreditación de exención', groups='erpec_payroll.group_payroll_manager',
        help='Ejercicio fiscal para el que se entregó el documento de edad o discapacidad. Sin coincidir con el año del cálculo no se aplica la exención.')
    ec_rdep_exemption_ref = fields.Char(
        'Referencia del documento de exención', groups='erpec_payroll.group_payroll_manager',
        help='Número o código del documento entregado; no registrar diagnósticos ni copias del documento.')
    ec_rdep_exemption_date = fields.Date(
        'Fecha de entrega al empleador', groups='erpec_payroll.group_payroll_manager',
        help='El Reglamento LRTI, art. 50, fija el 15 de enero del ejercicio. Una entrega posterior requiere regularización documentada y ajuste futuro; no permite reabrir nóminas contabilizadas.')
    ec_rdep_exemption_months = fields.Integer(
        'Meses de ejercicio como sustituto', default=12, groups='erpec_payroll.group_payroll_manager',
        help='Solo para el tipo 02 (sustituto): proporción del año en que ejerció esa calidad.')
    ec_rdep_special_expense = fields.Selection(
        SPECIAL_EXPENSE, string='Tope de gastos personales', default='none',
        groups='erpec_payroll.group_payroll_manager',
        help='100 canastas por discapacidad o enfermedad catastrófica, rara o huérfana del contribuyente o de una carga. La referencia aislada no lo habilita: requiere acreditación verificable y validación del vínculo.')
    ec_rdep_special_expense_year = fields.Integer('Año del documento del tope especial', groups='erpec_payroll.group_payroll_manager')
    ec_rdep_special_expense_ref = fields.Char('Referencia del documento del tope especial', groups='erpec_payroll.group_payroll_manager')

    def _rdep_personal_status(self, year):
        """Exenciones y tope especial acreditados para el año, con sus incidencias y avisos."""
        self.ensure_one()
        claims, issues, notes = resolve_exemption_claims(
            year, self.birthday, self.ec_rdep_disability_type, self.ec_rdep_disability_percentage,
            self.ec_rdep_disability_id_type, self.ec_rdep_disability_id, self.ec_rdep_exemption_year,
            self.ec_rdep_exemption_ref, self.ec_rdep_exemption_date, self.ec_rdep_exemption_months)
        special, special_issues = resolve_special_expense(
            year, self.ec_rdep_special_expense, self.ec_rdep_special_expense_year,
            self.ec_rdep_special_expense_ref, self.ec_rdep_dependents_count)
        return {'claims': claims, 'special_expense': special, 'issues': issues+special_issues, 'notes': notes}

    @api.constrains('ec_rdep_exemption_months')
    def _check_ec_rdep_exemption_months(self):
        for employee in self:
            if not 1 <= employee.ec_rdep_exemption_months <= 12:
                raise ValidationError('Los meses de ejercicio como sustituto van de 1 a 12.')

    @api.constrains('ec_rdep_disability_percentage')
    def _check_ec_rdep_disability_percentage(self):
        for employee in self:
            if employee.ec_rdep_disability_percentage and not 0 <= employee.ec_rdep_disability_percentage <= 100:
                raise ValidationError('El porcentaje de discapacidad del RDEP debe estar entre 0 y 100.')

    @api.constrains('ec_rdep_dependents_count')
    def _check_ec_rdep_dependents_count(self):
        for employee in self:
            if employee.ec_rdep_dependents_count and not 0 <= employee.ec_rdep_dependents_count <= 5:
                raise ValidationError('Las cargas para rebaja de gastos personales del RDEP van de 0 a 5.')

    @api.constrains('ec_rdep_establishment')
    def _check_ec_rdep_establishment(self):
        for employee in self:
            if employee.ec_rdep_establishment and not (len(employee.ec_rdep_establishment) == 3 and employee.ec_rdep_establishment.isdigit()):
                raise ValidationError('El establecimiento del RDEP debe tener 3 dígitos.')

    @api.constrains('ec_rdep_residence_country')
    def _check_ec_rdep_residence_country(self):
        for employee in self:
            if employee.ec_rdep_residence_country and not (len(employee.ec_rdep_residence_country) == 3 and employee.ec_rdep_residence_country.isdigit()):
                raise ValidationError('El país de residencia del RDEP debe ser un código SRI de 3 dígitos (593 = Ecuador).')


class Line(models.Model):
    _inherit = 'erpec.payroll.line'
    annual_profit_sharing = fields.Float('Participación de utilidades del año (RDEP)', help='Campo partUtil. Valor real distribuido, no calculado por este motor: la utilidad depende del resultado anual de la empresa.')
    decent_wage_compensation = fields.Float('Compensación salario digno (RDEP)', help='Campo salarioDigno. Compensación real pagada, no calculada por este motor.')
    other_employer_taxable_income = fields.Float('Ingresos gravados con otros empleadores (RDEP)', help='Campo otrosIngRenGrav; casillero 307 del Formulario 107. Declarado por el empleado con base en su F107 anterior.')
    other_employer_iess = fields.Float('Aporte IESS con otros empleadores (RDEP)', help='Campo aporPerIessConOtrosEmpls.')
    other_employer_withheld_tax = fields.Float('Impuesto asumido/retenido por otros empleadores (RDEP)', help='Campo valRetAsuOtrosEmpls.')
    employer_assumed_tax = fields.Float('Impuesto a la renta asumido por este empleador (RDEP)', help='Campos impRentEmpl/valImpAsuEsteEmpl; solo aplica a contratos de ingreso neto (casillero 381 del F107).')
    other_general_interest_income = fields.Float('Otros intereses/ingresos gravados generales (RDEP)', help='Campo intGrabGen del esquema SRI; su significado no está confirmado por ninguna fuente primaria revisada el 13-09-2026. Completar solo tras validar con el contador o la ficha técnica.')
    expense_housing = fields.Float('Gastos personales · vivienda (RDEP)', help='Campo deducVivienda. No tiene tope individual; el tope es único y total (ver la categoría "Educación, arte y cultura" para la referencia normativa completa).')
    expense_health = fields.Float('Gastos personales · salud (RDEP)', help='Campo deducSalud. No tiene tope individual; comparte el tope único y total con las demás categorías.')
    expense_education = fields.Float('Gastos personales · educación (RDEP)', help='Parte de la categoría "Educación, arte y cultura" (campo deducEducartcult); se suma con expense_art_culture. Desde la reforma de 2023 no hay tope por categoría: el Boletín NAC-COM-26-006 del SRI fija un tope único anual según cargas familiares (7 a 20 canastas básicas familiares), multiplicado por 1.803 en Galápagos (IPCEG).')
    expense_food = fields.Float('Gastos personales · alimentación (RDEP)', help='Campo deducAliement. No tiene tope individual; comparte el tope único y total con las demás categorías.')
    expense_clothing = fields.Float('Gastos personales · vestimenta (RDEP)', help='Campo deducVestim. No tiene tope individual; comparte el tope único y total con las demás categorías.')
    expense_art_culture = fields.Float('Gastos personales · arte y cultura (RDEP)', help='Parte de la categoría "Educación, arte y cultura" (campo deducEducartcult); se suma con expense_education. Ver esa ayuda para el tope único total vigente.')
    expense_tourism = fields.Float('Gastos personales · turismo nacional (RDEP)', help='Campo deduccionTurismo. No tiene tope individual; comparte el tope único y total con las demás categorías.')

    def _copy_inputs(self):
        values = super()._copy_inputs()
        values.update({key: self[key] for key in RDEP_LINE_INPUT_KEYS})
        return values

    def _inputs(self):
        # Solo para calculate(): dependents_count/galapagos no son campos de
        # erpec.payroll.line (vienen del empleado), así que no pueden ir en
        # _copy_inputs(), que además se usa para duplicar la línea en
        # action_correct(). Sin esto, engine.calculate() no podía escalar el
        # tope de gastos personales por cargas familiares ni por Galápagos.
        data = super()._inputs()
        data['dependents_count'] = self.employee_id.ec_rdep_dependents_count
        data['galapagos'] = self.employee_id.ec_rdep_ben_galpg or 'NO'
        # Solo lo acreditado para el año del período; lo inconsistente no se aplica y el anexo lo bloquea.
        status = self.employee_id.sudo()._rdep_personal_status(self.period_id.year)
        data['exemptions'] = status['claims']
        data['special_expense'] = status['special_expense']
        return data

    @api.constrains(*RDEP_LINE_INPUT_KEYS)
    def _check_rdep_inputs_not_negative(self):
        for line in self:
            if any(line[key] < 0 for key in RDEP_LINE_INPUT_KEYS):
                raise ValidationError('Las novedades del RDEP deben ser no negativas.')

    @api.constrains(*EXPENSE_CATEGORY_KEYS)
    def _check_expense_caps(self):
        # Boletín NAC-COM-26-006 (SRI): un solo tope anual total según cargas
        # familiares, no un tope por categoría (ver constante DEPENDENTS_BASKETS).
        for line in self:
            total = sum(line[key] for key in EXPENSE_CATEGORY_KEYS)
            special = line.employee_id.sudo()._rdep_personal_status(line.period_id.year)['special_expense']
            cap = _personal_expense_cap(line.period_id.policy_id, line.employee_id.ec_rdep_dependents_count, line.employee_id.ec_rdep_ben_galpg, special)
            if total > cap:
                raise ValidationError('El total de gastos personales (%.2f) supera el tope anual (%.2f) según las cargas familiares declaradas.' % (total, cap))


class RdepAnnex(models.Model):
    _name = 'erpec.payroll.rdep'
    _description = 'Agregador anual de nómina para el anexo RDEP (vista previa, no presentable)'
    _inherit = ['mail.thread']
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    year = fields.Integer('Año fiscal', required=True)
    state = fields.Selection([('draft', 'Borrador'), ('generated', 'XML generado')], default='draft', readonly=True)
    line_ids = fields.One2many('erpec.payroll.rdep.line', 'annex_id', readonly=True)
    xml_file = fields.Binary('XML de vista previa', readonly=True, attachment=False)
    filename = fields.Char(readonly=True)
    digest = fields.Char('SHA256 del XML', readonly=True)
    pending_notice = fields.Text('Pendiente', readonly=True, default=(
        'Vista previa interna del RDEP; no se presenta ante el SRI ni se homologa. DI25-03: se aplica la tarifa a acumulados efectivos. '
        'El tope de gastos personales usado aquí es único y total según cargas familiares '
        '(Boletín NAC-COM-26-006 del SRI), con el factor IPCEG 1.803 para empleados de Galápagos '
        '(campo benGalpg); el motor mensual de nómina aplica el mismo tope (erpec_payroll.engine.'
        'personal_expense_cap). '
        'El cierre anual, las retenciones mensuales y las bases laborales requieren aceptación tributaria independiente. Revisa los bloqueos antes de generar XML.'))
    _sql_constraints = [('company_year_unique', 'unique(company_id,year)', 'Ya existe un agregador para esta empresa y año.')]


    policy_id = fields.Many2one('erpec.payroll.policy', 'Política del cálculo anual', readonly=True)
    source_hash = fields.Char('Huella de períodos y datos revisados', readonly=True)
    calculation_method = fields.Char('Método del consolidado', readonly=True)
    review_notice = fields.Text('Revisión pendiente', compute='_compute_review_notice')

    @api.depends('year', 'company_id.name')
    def _compute_display_name(self):
        for annex in self:
            annex.display_name = 'RDEP %s · %s' % (annex.year or '', annex.company_id.name or '')

    def _posted_periods(self):
        self.ensure_one()
        return self.env['erpec.payroll.period'].search([
            ('company_id', '=', self.company_id.id), ('year', '=', self.year),
            ('state', '=', 'posted')], order='month,version,id')

    def _source_signature(self, periods):
        self.ensure_one()
        import hashlib
        employees = periods.line_ids.employee_id
        employee_fields = ['birthday', 'identification_id', 'name'] + [
            key for key, field in employees._fields.items() if key.startswith('ec_rdep_') and field.store and not field.compute]
        payload = {
            'calculation_revision': 'DI25-03-controles-18.0.1.13.0',
            'prior_employer': self.env['erpec.payroll.prior.employer'].sudo().search([
                ('company_id', '=', self.company_id.id), ('year', '=', self.year), ('state', '=', 'active')]).sorted('id').read(['employee_id', 'version', 'file_hash']),
            'company': [self.company_id.id, self.company_id.vat, self.company_id.ec_rdep_employer_type,
                        self.company_id.ec_rdep_social_security_entity], 'year': self.year,
            'periods': [(period.id, period.month, period.version, period.policy_id.id,
                         period.policy_id.parameters,
                         [(line.id, line.employee_id.id, line.result, line._copy_inputs())
                          for line in period.line_ids.sorted('id')]) for period in periods],
            'employees': employees.sudo().sorted('id').read(sorted(employee_fields)),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()

    def _coverage_issues(self, periods):
        """Explicita casos sin oráculo aprobado; no inventa reglas de exención."""
        issues = []
        special_inputs = ('annual_profit_sharing', 'decent_wage_compensation',
                          'employer_assumed_tax', 'other_general_interest_income')
        if any(any(line[key] for key in special_inputs) for line in periods.line_ids):
            issues.append('Ingresos especiales o impuesto asumido: falta conciliación independiente aprobada.')
        # D8: otros empleadores se concilian con los comprobantes versionados del empleador anterior.
        issues.extend(self.env['erpec.payroll.prior.employer'].reconciliation_issues(self.company_id, self.year, periods.line_ids))
        for employee in periods.line_ids.employee_id:
            for message in employee.sudo()._rdep_personal_status(self.year)['issues']:
                issues.append('Empleado %s: %s' % (employee.name, message))
        if any(employee.ec_rdep_ben_galpg == 'SI' for employee in periods.line_ids.employee_id):
            issues.append('Galápagos: falta validar el régimen completo, además del tope de gastos.')
        if any(employee.ec_rdep_treaty_applies == 'SI' or
               (employee.ec_rdep_residence_country and employee.ec_rdep_residence_country != '593')
               for employee in periods.line_ids.employee_id):
            issues.append('Residencia extranjera o convenio: falta oráculo aprobado para este régimen.')
        if len(periods.policy_id) > 1:
            issues.append('Hay varias políticas en el año; concilia su equivalencia antes de consolidar.')
        return issues

    def _compute_review_notice(self):
        for annex in self:
            periods = annex._posted_periods()
            issues = annex._coverage_issues(periods)
            issues.append('D5 · Compatibilidad RDEP 2026 pendiente: el portal publica programa 2026, pero ficha y catálogo visibles para 2025. El XML sigue siendo una vista previa interna.')
            issues += ['Aviso, %s: %s' % (employee.name, note) for employee in periods.line_ids.employee_id
                       for note in employee.sudo()._rdep_personal_status(annex.year)['notes']]
            if annex.source_hash and annex.source_hash != annex._source_signature(periods):
                issues.insert(0, 'Los datos cambiaron: vuelve a agregar los períodos antes de generar XML.')
            annex.review_notice = '\n'.join(issues) or (
                'Vista previa técnica. Pendiente aceptación del responsable tributario; '
                'el acumulado incluye solo los períodos contabilizados y no regulariza retenciones mensuales.')

    def action_build(self):
        self.ensure_one()
        manager(self.env)
        self.check_access('write')
        if not self.company_id.ec_rdep_employer_type or not self.company_id.ec_rdep_social_security_entity:
            raise ValidationError('Completa el tipo de empleador y el ente de seguridad social de la empresa antes de agregar.')
        periods = self._posted_periods()
        if not periods:
            raise ValidationError('No hay períodos contabilizados de nómina para esta empresa y año.')
        if len(periods.policy_id) != 1:
            raise ValidationError('Hay varias políticas en el año; concilia su equivalencia antes de consolidar.')
        policy = periods.policy_id
        parameters = json.loads(policy.parameters)
        totals = {}
        for period in periods:
            for line in period.line_ids:
                result = json.loads(line.result or '{}')
                entry = totals.setdefault(line.employee_id.id, dict.fromkeys(
                    RDEP_FLOW_KEYS + RDEP_LINE_INPUT_KEYS + ('bonus_commission',), 0.0))
                entry['months'] = entry.get('months', 0) + 1
                for key in RDEP_FLOW_KEYS:
                    entry[key] += result.get(key, 0.0)
                for key in RDEP_LINE_INPUT_KEYS:
                    entry[key] += line[key]
                # Incluye beneficios gravados que ya están en el resultado inmutable.
                entry['bonus_commission'] += result.get('base', 0) - result.get('salary', 0) - result.get('overtime', 0)
        records = []
        for employee_id, values in totals.items():
            employee = self.env['hr.employee'].browse(employee_id)
            status = employee.sudo()._rdep_personal_status(self.year)
            exemption_kind, exemption, annual_base = apply_personal_exemption(
                max(0, values['base'] - values['personal_iess']), parameters, status['claims'])
            actual_expenses = sum(values[key] for key in EXPENSE_CATEGORY_KEYS)
            caused, rebate, after_rebate = annual_income_tax(
                annual_base, actual_expenses, parameters, employee.ec_rdep_dependents_count,
                employee.ec_rdep_ben_galpg or 'NO', special_expense=status['special_expense'])
            records.append({
                'annex_id': self.id, 'employee_id': employee_id, **values,
                'annual_base': float(annual_base),
                'personal_exemption': float(exemption), 'personal_exemption_kind': exemption_kind,
                'annual_tax_caused': float(money(caused)),
                'personal_expense_rebate': float(money(min(caused, rebate))),
                'annual_tax_after_rebate': float(money(after_rebate)),
                'tax_difference': float(money(after_rebate - number(values['tax']))),
            })
        self.line_ids.unlink()
        self.env['erpec.payroll.rdep.line'].create(records)
        self.write({'policy_id': policy.id, 'source_hash': self._source_signature(periods),
                    'calculation_method': 'DI25-03 v2 · tarifa sobre acumulados efectivos, exención personal acreditada y tope especial; vista previa limitada',
                    'state': 'draft', 'xml_file': False, 'filename': False, 'digest': False})
        return True

    def action_generate_xml(self):
        self.ensure_one()
        manager(self.env)
        self.check_access('write')
        if not self.line_ids:
            raise ValidationError('Agrega los períodos contabilizados antes de generar la vista previa XML.')
        if not (self.company_id.vat and len(self.company_id.vat) == 13):
            raise ValidationError('La empresa requiere un RUC real de 13 dígitos para el campo numRuc; no se inventa en la demo.')
        periods = self._posted_periods()
        if not self.source_hash or self.source_hash != self._source_signature(periods):
            raise ValidationError('Los datos cambiaron o proceden de una versión anterior; vuelve a agregar los períodos.')
        issues = self._coverage_issues(periods)
        if issues:
            raise ValidationError('XML bloqueado. ' + ' '.join(issues) + ' Solicita la revisión del responsable tributario.')
        root = etree.Element('rdep')

        def add(parent, name, value):
            node = etree.SubElement(parent, name)
            node.text = str(value)
            return node
        add(root, 'numRuc', self.company_id.vat)
        add(root, 'anio', self.year)
        add(root, 'tipoEmpleador', self.company_id.ec_rdep_employer_type)
        add(root, 'enteSegSocial', self.company_id.ec_rdep_social_security_entity)
        ret = etree.SubElement(root, 'retRelDep')
        for line in self.line_ids:
            employee = line.employee_id
            missing = [label for field, label in (
                ('ec_rdep_id_type', 'tipo de identificación'), ('identification_id', 'número de identificación'),
                ('ec_rdep_establishment', 'establecimiento'), ('ec_rdep_fiscal_residence', 'código de residencia'),
                ('ec_rdep_residence_country', 'país de residencia'), ('ec_rdep_treaty_applies', 'convenio doble imposición'),
                ('ec_rdep_disability_type', 'discapacidad'),
            ) if not employee[field]]
            if missing:
                raise ValidationError('Empleado %s: completa %s antes de generar la vista previa.' % (employee.name, ', '.join(missing)))
            detail = etree.SubElement(ret, 'datRetRelDep')
            emp = etree.SubElement(detail, 'empleado')
            add(emp, 'benGalpg', employee.ec_rdep_ben_galpg or 'NO')
            if employee.ec_rdep_dependents_count:
                add(emp, 'numCargRebGastPers', employee.ec_rdep_dependents_count)
            add(emp, 'tipIdRet', employee.ec_rdep_id_type)
            add(emp, 'idRet', employee.identification_id)
            given, surname = _split_name(employee.name)
            add(emp, 'apellidoTrab', surname)
            add(emp, 'nombreTrab', given)
            add(emp, 'estab', employee.ec_rdep_establishment)
            add(emp, 'residenciaTrab', employee.ec_rdep_fiscal_residence)
            add(emp, 'paisResidencia', employee.ec_rdep_residence_country)
            add(emp, 'aplicaConvenio', employee.ec_rdep_treaty_applies)
            add(emp, 'tipoTrabajDiscap', employee.ec_rdep_disability_type)
            add(emp, 'porcentajeDiscap', employee.ec_rdep_disability_percentage or 0)
            add(emp, 'tipIdDiscap', employee.ec_rdep_disability_id_type or 'N')
            if employee.ec_rdep_disability_id:
                add(emp, 'idDiscap', employee.ec_rdep_disability_id)
            # Exención acreditada y aplicada al agregar; el valor coincide con la base imponible.
            disability_relief = line.personal_exemption if line.personal_exemption_kind in ('disability', 'substitute') else 0
            elderly_relief = line.personal_exemption if line.personal_exemption_kind == 'elderly' else 0
            add(detail, 'suelSal', round(line.salary, 2))
            add(detail, 'sobSuelComRemu', round(line.overtime + line.bonus_commission, 2))
            add(detail, 'partUtil', round(line.annual_profit_sharing, 2))
            add(detail, 'intGrabGen', round(line.other_general_interest_income, 2))
            add(detail, 'impRentEmpl', round(line.employer_assumed_tax, 2))
            add(detail, 'decimTer', round(line.thirteenth, 2))
            add(detail, 'decimCuar', round(line.fourteenth, 2))
            add(detail, 'fondoReserva', round(line.reserve_iess, 2))
            add(detail, 'salarioDigno', round(line.decent_wage_compensation, 2))
            add(detail, 'otrosIngRenGrav', round(line.other_employer_taxable_income, 2))
            add(detail, 'ingGravConEsteEmpl', round(line.base, 2))
            add(detail, 'sisSalNet', 2 if line.employer_assumed_tax else 1)
            add(detail, 'apoPerIess', round(line.personal_iess, 2))
            add(detail, 'aporPerIessConOtrosEmpls', round(line.other_employer_iess, 2))
            add(detail, 'deducVivienda', round(line.expense_housing, 2))
            add(detail, 'deducSalud', round(line.expense_health, 2))
            # deducEducartcult es la categoría "Educación, arte y cultura" que el SRI
            # reporta fusionada desde la reforma tributaria de 2023; deducEduca y
            # deducArtycult son campos legados (opcionales) de las categorías separadas
            # previas y ya no se emiten para períodos corrientes.
            add(detail, 'deducEducartcult', round(line.expense_education + line.expense_art_culture, 2))
            add(detail, 'deducAliement', round(line.expense_food, 2))
            add(detail, 'deducVestim', round(line.expense_clothing, 2))
            if line.expense_tourism:
                add(detail, 'deduccionTurismo', round(line.expense_tourism, 2))
            add(detail, 'exoDiscap', round(disability_relief, 2))
            add(detail, 'exoTerEd', round(elderly_relief, 2))
            add(detail, 'basImp', round(line.annual_base, 2))
            add(detail, 'impRentCaus', round(line.annual_tax_caused, 2))
            if line.personal_expense_rebate:
                add(detail, 'rebajaGastosPersonales', round(line.personal_expense_rebate, 2))
                add(detail, 'impuestoRentaRebajaGastosPersonales', round(line.annual_tax_after_rebate, 2))
            add(detail, 'valRetAsuOtrosEmpls', round(line.other_employer_withheld_tax, 2))
            add(detail, 'valImpAsuEsteEmpl', round(line.employer_assumed_tax, 2))
            add(detail, 'valRet', round(line.tax, 2))
        schema = etree.XMLSchema(etree.parse(str(Path(__file__).parent / 'xsd/Esquema_RDEP_2023.xsd'), etree.XMLParser(no_network=True, resolve_entities=False)))
        if not schema.validate(root):
            raise ValidationError('XML incompatible con el esquema RDEP oficial: ' + str(schema.error_log.last_error))
        import hashlib
        import base64
        xml_bytes = etree.tostring(root, encoding='UTF-8', xml_declaration=True, pretty_print=True)
        self.write({'xml_file': base64.b64encode(xml_bytes), 'filename': 'RDEP-VISTA-PREVIA-%s-%s.xml' % (self.company_id.id, self.year), 'digest': hashlib.sha256(xml_bytes).hexdigest(), 'state': 'generated'})
        return True


class RdepAnnexLine(models.Model):
    _name = 'erpec.payroll.rdep.line'
    _description = 'Totales anuales por empleado para el agregador RDEP'
    annex_id = fields.Many2one('erpec.payroll.rdep', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='annex_id.company_id', store=True)
    employee_id = fields.Many2one('hr.employee', 'Empleado', required=True, readonly=True)
    months = fields.Integer('Períodos contabilizados', readonly=True)
    gross = fields.Float('Ingresos gravados acumulados', readonly=True)
    salary = fields.Float('Sueldo/salario acumulado (suelSal)', readonly=True)
    overtime = fields.Float('Horas suplementarias/extraordinarias acumuladas', readonly=True)
    bonus_commission = fields.Float('Bonificaciones y comisiones acumuladas (parte de sobSuelComRemu)', readonly=True)
    base = fields.Float('Base gravada con este empleador acumulada (ingGravConEsteEmpl)', readonly=True)
    thirteenth = fields.Float('Décimo tercero acumulado (decimTer)', readonly=True)
    fourteenth = fields.Float('Décimo cuarto acumulado (decimCuar)', readonly=True)
    reserve_iess = fields.Float('Fondo de reserva acumulado (fondoReserva)', readonly=True)
    personal_iess = fields.Float('Aporte personal IESS acumulado (apoPerIess)', readonly=True)
    tax = fields.Float('Impuesto a la renta retenido acumulado (valRet)', readonly=True)
    annual_base = fields.Float('Base imponible anual efectiva (después de la exención)', readonly=True)
    personal_exemption = fields.Float('Exención personal aplicada (exoDiscap o exoTerEd)', readonly=True)
    personal_exemption_kind = fields.Selection(
        [('none', 'Sin exención'), ('elderly', 'Adulto mayor'), ('disability', 'Discapacidad'), ('substitute', 'Sustituto')],
        string='Tipo de exención aplicada', readonly=True, default='none')
    tax_difference = fields.Float('Impuesto anual menos retenciones (sin ajuste automático)', readonly=True)
    annual_tax_caused = fields.Float('Impuesto a la renta causado (impRentCaus)', readonly=True)
    personal_expense_rebate = fields.Float('Rebaja por gastos personales (rebajaGastosPersonales)', readonly=True)
    annual_tax_after_rebate = fields.Float('Impuesto después de la rebaja (impuestoRentaRebajaGastosPersonales)', readonly=True)
    annual_profit_sharing = fields.Float('Participación de utilidades (partUtil)', readonly=True)
    decent_wage_compensation = fields.Float('Compensación salario digno (salarioDigno)', readonly=True)
    other_employer_taxable_income = fields.Float('Ingresos gravados con otros empleadores (otrosIngRenGrav)', readonly=True)
    other_employer_iess = fields.Float('Aporte IESS con otros empleadores (aporPerIessConOtrosEmpls)', readonly=True)
    other_employer_withheld_tax = fields.Float('Impuesto asumido/retenido por otros empleadores (valRetAsuOtrosEmpls)', readonly=True)
    employer_assumed_tax = fields.Float('Impuesto asumido por este empleador (valImpAsuEsteEmpl)', readonly=True)
    other_general_interest_income = fields.Float('Otros intereses/ingresos gravados generales (intGrabGen)', readonly=True)
    expense_housing = fields.Float('Gastos personales · vivienda (deducVivienda)', readonly=True)
    expense_health = fields.Float('Gastos personales · salud (deducSalud)', readonly=True)
    expense_education = fields.Float('Gastos personales · educación (parte de deducEducartcult)', readonly=True)
    expense_food = fields.Float('Gastos personales · alimentación (deducAliement)', readonly=True)
    expense_clothing = fields.Float('Gastos personales · vestimenta (deducVestim)', readonly=True)
    expense_art_culture = fields.Float('Gastos personales · arte y cultura (parte de deducEducartcult)', readonly=True)
    expense_tourism = fields.Float('Gastos personales · turismo (deduccionTurismo)', readonly=True)
