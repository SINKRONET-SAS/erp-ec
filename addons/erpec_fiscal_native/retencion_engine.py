"""Preparación XML local del comprobante de retención (codDoc 07, versión 2.0.0 ATS); sin firma ni
transmisión (eso lo hace erpec_fiscal_sri). Estructura confirmada contra
addons/erpec_fiscal_native/xsd/ComprobanteRetencion_V2.0.0.xsd (ZIP oficial del SRI). Códigos de
retención de IVA según Tabla 20 de la Ficha Técnica 2.34 del SRI."""
from decimal import Decimal
from datetime import date
from pathlib import Path
import re
from lxml import etree

from .engine import access_key, money, append_info_adicional
from .retention_catalog import INCOME

DOC_TYPE = '07'
TAX_CODES = {'income': '1', 'vat': '2'}
VAT_RETENTION_CODES = {Decimal('10'): '9', Decimal('20'): '10', Decimal('30'): '1', Decimal('50'): '11',
                       Decimal('70'): '2', Decimal('100'): '3', Decimal('0'): '7'}


def _fmt(day):
    return date.fromisoformat(str(day)).strftime('%d/%m/%Y')


def generate(data):
    """`data`: date, number (est-pto-sec), numeric, issuer_vat/name/address, accounting, agent_resolution
    (opcional), subject_type ('04'|'05'|'06'|'08'), subject_vat/name, subject_kind ('01'|'02', solo se envía con tipo 08),
    related_party ('SI'|'NO'), support: {sustento_code, doc_type ('01'), doc_number (3-3-9), doc_date,
    doc_authorization (opcional), untaxed, total, taxes:[{code:'2', percent_code, base, rate, amount}],
    payment ('01'..'21')} y lines: [{kind:'income'|'vat', sri_code, base, rate, amount}]."""
    key=access_key(data['date'],data['issuer_vat'],data['number'],data['numeric'],doc_type=DOC_TYPE,ambiente=data.get('ambiente','1'))
    if data['subject_type'] not in ('04','05','06','08') or not (data.get('subject_vat') or '').strip():
        raise ValueError('Indica tipo e identificación del sujeto retenido.')
    if data['subject_type']=='04' and not re.fullmatch(r'[0-9]{13}',data['subject_vat']):
        raise ValueError('El RUC del sujeto retenido debe tener 13 dígitos.')
    if data['subject_type']=='05' and not re.fullmatch(r'[0-9]{10}',data['subject_vat']):
        raise ValueError('La cédula del sujeto retenido debe tener 10 dígitos.')
    for field in ('issuer_name','issuer_address','subject_name'):
        if not data.get(field):raise ValueError('Completa razón social y dirección del emisor y razón social del sujeto retenido.')
    support=data['support']
    if not re.fullmatch(r'[0-9]{2}',support.get('sustento_code') or ''):
        raise ValueError('Indica el código de sustento tributario (2 dígitos).')
    if not re.fullmatch(r'[0-9]{3}-[0-9]{3}-[0-9]{9}',support.get('doc_number') or ''):
        raise ValueError('El comprobante de sustento requiere establecimiento-punto-secuencial (3-3-9).')
    if support.get('payment') not in ('01','15','16','17','18','19','20','21'):
        raise ValueError('Selecciona una forma de pago válida del catálogo SRI.')
    if not data.get('lines'):
        raise ValueError('La retención requiere al menos un concepto.')
    root=etree.Element('comprobanteRetencion',id='comprobante',version='2.0.0')
    def add(parent,name,value):
        node=etree.SubElement(parent,name);node.text=str(value);return node
    tributary=etree.SubElement(root,'infoTributaria')
    establishment,point,sequence=data['number'].split('-')
    items=[('ambiente',data.get('ambiente','1')),('tipoEmision','1'),('razonSocial',data['issuer_name']),('ruc',data['issuer_vat']),('claveAcceso',key),('codDoc',DOC_TYPE),('estab',establishment),('ptoEmi',point),('secuencial',sequence),('dirMatriz',data['issuer_address'])]
    if data.get('agent_resolution'):items.append(('agenteRetencion',data['agent_resolution']))
    for name,value in items:add(tributary,name,value)
    info=etree.SubElement(root,'infoCompRetencion')
    items=[('fechaEmision',_fmt(data['date'])),('dirEstablecimiento',data.get('establishment_address') or data['issuer_address'])]
    for name,value in items:add(info,name,value)
    if data.get('accounting'):add(info,'obligadoContabilidad',data['accounting'])
    add(info,'tipoIdentificacionSujetoRetenido',data['subject_type'])
    # Regla del SRI (no del XSD): el tipo de sujeto solo se informa si la identificación es del exterior.
    if data['subject_type']=='08' and data.get('subject_kind'):add(info,'tipoSujetoRetenido',data['subject_kind'])
    add(info,'parteRel',data.get('related_party') or 'NO')
    add(info,'razonSocialSujetoRetenido',data['subject_name']);add(info,'identificacionSujetoRetenido',data['subject_vat'])
    add(info,'periodoFiscal',date.fromisoformat(str(data['date'])).strftime('%m/%Y'))
    docs=etree.SubElement(root,'docsSustento');doc=etree.SubElement(docs,'docSustento')
    add(doc,'codSustento',support['sustento_code']);add(doc,'codDocSustento',support.get('doc_type') or '01')
    add(doc,'numDocSustento',support['doc_number'].replace('-',''));add(doc,'fechaEmisionDocSustento',_fmt(support['doc_date']))
    add(doc,'fechaRegistroContable',_fmt(support.get('accounting_date') or support['doc_date']))
    if support.get('doc_authorization'):add(doc,'numAutDocSustento',support['doc_authorization'])
    add(doc,'pagoLocExt','01')
    add(doc,'totalSinImpuestos',f"{money(support['untaxed']):.2f}");add(doc,'importeTotal',f"{money(support['total']):.2f}")
    taxes=etree.SubElement(doc,'impuestosDocSustento')
    for tax in support['taxes']:
        node=etree.SubElement(taxes,'impuestoDocSustento')
        for name,value in [('codImpuestoDocSustento',tax['code']),('codigoPorcentaje',tax['percent_code']),('baseImponible',f"{money(tax['base']):.2f}"),('tarifa',f"{Decimal(str(tax['rate'])):.2f}"),('valorImpuesto',f"{money(tax['amount']):.2f}")]:add(node,name,value)
    withheld=etree.SubElement(doc,'retenciones');total=Decimal(0)
    for line in data['lines']:
        kind=line.get('kind')
        if kind not in TAX_CODES:raise ValueError('El tipo de impuesto retenido debe ser renta o IVA.')
        rate=Decimal(str(line['rate']));base=money(line['base']);amount=money(line['amount'])
        if base<=0 or amount<=0 or not 0<rate<=100 or money(base*rate/100)!=amount:
            raise ValueError('Los importes de la retención no coinciden con base y porcentaje; revisar antes de continuar.')
        code=(line.get('sri_code') or '').strip()
        if not re.fullmatch(r'[0-9A-Za-z]{1,5}',code):raise ValueError('Cada concepto requiere su código SRI de retención (hasta 5 caracteres).')
        if kind=='income':
            if code not in INCOME:raise ValueError('El código %s no está en el catálogo vigente de retención de renta.'%code)
            if float(rate) not in INCOME[code]['rates']:
                raise ValueError('La tarifa %s%% no corresponde al código %s; vigente: %s.'%(rate,code,', '.join('%s%%'%item for item in INCOME[code]['rates'])))
        if kind=='vat' and VAT_RETENTION_CODES.get(rate)!=code:
            raise ValueError('El código de retención de IVA no corresponde al porcentaje (Tabla 20 del SRI).')
        node=etree.SubElement(withheld,'retencion')
        for name,value in [('codigo',TAX_CODES[kind]),('codigoRetencion',code),('baseImponible',f'{base:.2f}'),('porcentajeRetener',f'{rate:.2f}'),('valorRetenido',f'{amount:.2f}')]:add(node,name,value)
        total+=amount
    if total<=0:raise ValueError('El total retenido debe ser positivo.')
    payments=etree.SubElement(doc,'pagos');payment=etree.SubElement(payments,'pago')
    add(payment,'formaPago',support['payment']);add(payment,'total',f"{money(support['total']):.2f}")
    append_info_adicional(root,data.get('info_adicional'))
    schema=etree.XMLSchema(etree.parse(str(Path(__file__).parent/'xsd/ComprobanteRetencion_V2.0.0.xsd'),etree.XMLParser(no_network=True,resolve_entities=False)))
    if not schema.validate(root):raise ValueError('XML incompatible con el esquema SRI: '+str(schema.error_log.last_error))
    return key,etree.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
