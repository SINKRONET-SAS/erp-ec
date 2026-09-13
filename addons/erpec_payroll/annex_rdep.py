"""Datos, agregador anual y XML de vista previa para el anexo RDEP del SRI.

Cubre los campos de datRetRelDepTyp del Esquema RDEP 2023.xsd (SRI), fuente
primaria descargada y leída el 13-09-2026 (addons/erpec_payroll/xsd/
Esquema_RDEP_2023.xsd). El significado de cada campo proviene, en este orden
de confianza: (1) la propia documentación XSD, (2) el Instructivo del
Formulario 107 del SRI (mismo concepto de retención, per relación de
dependencia) y (3) el nombre literal del campo cuando ninguna fuente lo
documenta explícitamente — estos últimos quedan marcados en el código y en
docs/ALCANCE_ATS_RDEP.md. No se inventan catálogos ni fórmulas legales.

Reutiliza exclusivamente los totales que ya calcula erpec_payroll.engine
(gross, salary, overtime, thirteenth, fourteenth, reserve_iess, personal_iess,
tax, annual_tax_caused, personal_expense_rebate, annual_tax_after_rebate); no
se duplica el motor de cálculo. Los campos que el motor no puede calcular
(participación de utilidades, salario digno, ingresos/aportes con otros
empleadores, impuesto asumido por el empleador y deducciones desglosadas de
gastos personales) se capturan como novedades explícitas del período, igual
que wage/bonus/commission ya se capturan hoy; no se completan con ceros
salvo que el responsable de nómina realmente los declare así.

No genera un anexo homologado ni presentado ante el SRI: la vista previa XML
se valida contra el esquema oficial descargado, pero no hay firma, envío ni
autoridad SRI involucrados. Dos campos del esquema quedan explícitamente sin
resolver por falta de fuente autorizada: `deducEducartcult` (nombre ambiguo,
no documentado en ninguna fuente consultada) y `benGalpg` (sin documentación
en el esquema ni en las guías del SRI revisadas); se envían en 0 y "NO"
respectivamente, marcados en el código, y deben confirmarse antes de usar el
anexo para un caso real.
"""
import json
import unicodedata
from pathlib import Path
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from .models import manager

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
# Tramo 0 de tax_brackets (from=0) es la fracción básica exenta del IR; los
# topes de gastos personales del Instructivo Formulario 107 se expresan como
# múltiplos suyos: vivienda/educación/alimentación/vestimenta 0.325 veces,
# salud 1.3 veces.
EXPENSE_CAP_RATES = {'expense_housing': 0.325, 'expense_education': 0.325, 'expense_food': 0.325, 'expense_clothing': 0.325, 'expense_health': 1.3}


def _basic_fraction(policy):
    params = json.loads(policy.parameters)
    brackets = [bracket for bracket in params['tax_brackets'] if bracket['from'] == 0]
    return brackets[0]['to']


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
        BEN_GALPG, string='Campo benGalpg (RDEP)',
        help='Campo benGalpg del esquema SRI, requerido pero sin documentación en el esquema ni en las guías revisadas el 13-09-2026. Confirmar su significado antes de presentar un anexo real.')
    ec_rdep_establishment = fields.Char('Establecimiento (RDEP)', help='Campo estab: 3 dígitos, código de establecimiento del RUC donde trabaja el empleado.')

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
    expense_housing = fields.Float('Gastos personales · vivienda (RDEP)', help='Campo deducVivienda; tope legal 0.325 veces la fracción básica exenta.')
    expense_health = fields.Float('Gastos personales · salud (RDEP)', help='Campo deducSalud; tope legal 1.3 veces la fracción básica exenta.')
    expense_education = fields.Float('Gastos personales · educación (RDEP)', help='Campo deducEduca; tope legal 0.325 veces la fracción básica exenta.')
    expense_food = fields.Float('Gastos personales · alimentación (RDEP)', help='Campo deducAliement; tope legal 0.325 veces la fracción básica exenta.')
    expense_clothing = fields.Float('Gastos personales · vestimenta (RDEP)', help='Campo deducVestim; tope legal 0.325 veces la fracción básica exenta.')
    expense_art_culture = fields.Float('Gastos personales · arte y cultura (RDEP)', help='Campo deducArtycult; tope legal no confirmado en las fuentes revisadas.')
    expense_tourism = fields.Float('Gastos personales · turismo (RDEP)', help='Campo deduccionTurismo; tope legal no confirmado en las fuentes revisadas.')

    def _copy_inputs(self):
        values = super()._copy_inputs()
        values.update({key: self[key] for key in RDEP_LINE_INPUT_KEYS})
        return values

    @api.constrains(*RDEP_LINE_INPUT_KEYS)
    def _check_rdep_inputs_not_negative(self):
        for line in self:
            if any(line[key] < 0 for key in RDEP_LINE_INPUT_KEYS):
                raise ValidationError('Las novedades del RDEP deben ser no negativas.')

    @api.constrains(*EXPENSE_CAP_RATES)
    def _check_expense_caps(self):
        for line in self:
            fraction = _basic_fraction(line.period_id.policy_id)
            for key, rate in EXPENSE_CAP_RATES.items():
                if line[key] > fraction * rate:
                    raise ValidationError('%s supera el tope legal (%.2f veces la fracción básica exenta) del Instructivo Formulario 107.' % (line._fields[key].string, rate))


class RdepAnnex(models.Model):
    _name = 'erpec.payroll.rdep'
    _description = 'Agregador anual de nómina para el anexo RDEP (vista previa, no presentable)'
    _inherit = ['mail.thread']
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    year = fields.Integer('Año fiscal', required=True)
    state = fields.Selection([('draft', 'Borrador'), ('generated', 'XML generado')], default='draft', readonly=True)
    line_ids = fields.One2many('erpec.payroll.rdep.line', 'annex_id', readonly=True)
    xml_file = fields.Binary('XML de vista previa', readonly=True, attachment=False)
    filename = fields.Char(readonly=True)
    digest = fields.Char('SHA256 del XML', readonly=True)
    pending_notice = fields.Text('Pendiente', readonly=True, default=(
        'Vista previa interna del anexo RDEP; no se presenta ante el SRI ni se homologa. '
        'Dos campos del esquema (deducEducartcult y benGalpg) se completan con un valor neutro '
        'porque ninguna fuente primaria revisada confirma su significado; revisar antes de un caso real. '
        'Revisa docs/ALCANCE_ATS_RDEP.md antes de continuar.'))
    _sql_constraints = [('company_year_unique', 'unique(company_id,year)', 'Ya existe un agregador para esta empresa y año.')]

    def action_build(self):
        self.ensure_one()
        manager(self.env)
        self.check_access('write')
        if not self.company_id.ec_rdep_employer_type or not self.company_id.ec_rdep_social_security_entity:
            raise ValidationError('Completa el tipo de empleador y el ente de seguridad social de la empresa antes de agregar.')
        periods = self.env['erpec.payroll.period'].search([
            ('company_id', '=', self.company_id.id), ('year', '=', self.year), ('state', '=', 'posted')], order='id')
        if not periods:
            raise ValidationError('No hay períodos contabilizados de nómina para esta empresa y año.')
        totals = {}
        last_result = {}
        for period in periods:
            for line in period.line_ids:
                result = json.loads(line.result or '{}')
                entry = totals.setdefault(line.employee_id.id, dict.fromkeys(RDEP_FLOW_KEYS + RDEP_LINE_INPUT_KEYS + ('bonus_commission',), 0.0))
                entry['months'] = entry.get('months', 0) + 1
                for key in RDEP_FLOW_KEYS:
                    entry[key] += result.get(key, 0.0)
                for key in RDEP_LINE_INPUT_KEYS:
                    entry[key] += line[key]
                entry['bonus_commission'] += line.bonus + line.commission
                # annual_tax_caused/rebate/after_rebate son proyecciones anuales, no flujos
                # mensuales: se toma el último período contabilizado, no se suman.
                last_result[line.employee_id.id] = result
        self.line_ids.unlink()
        records = []
        for employee_id, values in totals.items():
            result = last_result[employee_id]
            records.append({
                'annex_id': self.id, 'employee_id': employee_id, **values,
                'annual_tax_caused': result.get('annual_tax_caused', 0.0),
                'personal_expense_rebate': result.get('personal_expense_rebate', 0.0),
                'annual_tax_after_rebate': result.get('annual_tax_after_rebate', 0.0),
            })
        self.env['erpec.payroll.rdep.line'].create(records)
        return True

    def action_generate_xml(self):
        self.ensure_one()
        manager(self.env)
        self.check_access('write')
        if not self.line_ids:
            raise ValidationError('Agrega los períodos contabilizados antes de generar la vista previa XML.')
        if not (self.company_id.vat and len(self.company_id.vat) == 13):
            raise ValidationError('La empresa requiere un RUC real de 13 dígitos para el campo numRuc; no se inventa en la demo.')
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
        reference_period = self.env['erpec.payroll.period'].search([
            ('company_id', '=', self.company_id.id), ('year', '=', self.year), ('state', '=', 'posted')], limit=1)
        fraction = _basic_fraction(reference_period.policy_id)
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
            disability_relief = round(3 * fraction, 2) if employee.ec_rdep_disability_percentage >= 30 else 0
            elderly_relief = round(2 * fraction, 2) if employee.birthday and (self.year - employee.birthday.year) >= 65 else 0
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
            if line.expense_education:
                add(detail, 'deducEduca', round(line.expense_education, 2))
            # deducEducartcult: nombre ambiguo sin documentación en ninguna fuente
            # primaria revisada (distinto de deducArtycult, que sí está definido);
            # se envía en 0 hasta confirmar su significado real.
            add(detail, 'deducEducartcult', 0)
            add(detail, 'deducAliement', round(line.expense_food, 2))
            add(detail, 'deducVestim', round(line.expense_clothing, 2))
            if line.expense_art_culture:
                add(detail, 'deducArtycult', round(line.expense_art_culture, 2))
            if line.expense_tourism:
                add(detail, 'deduccionTurismo', round(line.expense_tourism, 2))
            add(detail, 'exoDiscap', disability_relief)
            add(detail, 'exoTerEd', elderly_relief)
            add(detail, 'basImp', round(line.base - line.personal_iess, 2))
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
    employee_id = fields.Many2one('hr.employee', required=True, readonly=True)
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
    expense_education = fields.Float('Gastos personales · educación (deducEduca)', readonly=True)
    expense_food = fields.Float('Gastos personales · alimentación (deducAliement)', readonly=True)
    expense_clothing = fields.Float('Gastos personales · vestimenta (deducVestim)', readonly=True)
    expense_art_culture = fields.Float('Gastos personales · arte y cultura (deducArtycult)', readonly=True)
    expense_tourism = fields.Float('Gastos personales · turismo (deduccionTurismo)', readonly=True)
