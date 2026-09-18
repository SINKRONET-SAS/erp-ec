"""Preparación XML local de nota de débito; sin firma ni transmisión (eso lo hace erpec_fiscal_sri).
Estructura confirmada contra addons/erpec_fiscal_native/xsd/NotaDebito_V1.0.0.xsd (ZIP oficial del
SRI): en lugar de detalles, la nota de débito lleva motivos (razon + valor) e impuestos agrupados."""
from decimal import Decimal
from datetime import date
from pathlib import Path
import re
from lxml import etree

from .engine import access_key, money

DOC_TYPE = '05'


def generate(data):
    """`data`: como notacredito_engine.generate() salvo que no hay `reason` global: cada línea
    de `items` es un motivo (`description` = razón, `subtotal` = valor sin impuesto). `payment`
    (opcional) agrega el bloque de pagos."""
    key=access_key(data['date'],data['issuer_vat'],data['number'],data['numeric'],doc_type=DOC_TYPE,ambiente=data.get('ambiente','1'))
    if data['buyer_type'] not in ('04','05') or not re.fullmatch(r'[0-9]{13}' if data['buyer_type']=='04' else r'[0-9]{10}',data['buyer_vat'] or ''):
        raise ValueError('Este incremento requiere comprador identificado con RUC o cédula.')
    if not re.fullmatch(r'[0-9]{2}',data.get('modified_type') or ''):
        raise ValueError('Indica el código del tipo de comprobante que se modifica.')
    if not re.fullmatch(r'[0-9]{3}-[0-9]{3}-[0-9]{9}',data.get('modified_number') or ''):
        raise ValueError('Indica establecimiento-punto-secuencial (3-3-9) del documento que se modifica.')
    if data.get('payment') and data['payment'] not in ('01','15','16','17','18','19','20','21'):
        raise ValueError('Selecciona una forma de pago válida del catálogo SRI.')
    for field in ('issuer_name','issuer_address','buyer_name','buyer_address'):
        if not data.get(field):raise ValueError('Completa razón social y direcciones de emisor y comprador.')
    root=etree.Element('notaDebito',id='comprobante',version='1.0.0')
    def add(parent,name,value):
        node=etree.SubElement(parent,name);node.text=str(value);return node
    tributary=etree.SubElement(root,'infoTributaria')
    establishment,point,sequence=data['number'].split('-')
    for name,value in [('ambiente',data.get('ambiente','1')),('tipoEmision','1'),('razonSocial',data['issuer_name']),('ruc',data['issuer_vat']),('claveAcceso',key),('codDoc',DOC_TYPE),('estab',establishment),('ptoEmi',point),('secuencial',sequence),('dirMatriz',data['issuer_address'])]:add(tributary,name,value)
    reasons=[];groups={};base_total=Decimal(0);tax_total=Decimal(0)
    for item in data['items']:
        reason=(item.get('description') or '').strip()
        if not reason:raise ValueError('Cada motivo de la nota de débito requiere una razón.')
        base=money(item['subtotal']);rate=Decimal(str(item['rate']))
        if rate not in (0,15):raise ValueError('El incremento local admite IVA 0 y 15; otras tarifas requieren ampliar y validar el perfil.')
        if base<=0 or money(base*rate/100)!=money(item['tax']):
            raise ValueError('Los redondeos del XML no coinciden con la nota de débito; revisar antes de continuar.')
        code='0' if rate==0 else '4'
        g=groups.setdefault(code,[rate,Decimal(0),Decimal(0)]);g[1]+=base;g[2]+=money(item['tax'])
        reasons.append((reason[:300],base));base_total+=base;tax_total+=money(item['tax'])
    if not reasons or base_total+tax_total!=money(data['total']):
        raise ValueError('El total del XML no coincide con la nota de débito positiva.')
    info=etree.SubElement(root,'infoNotaDebito')
    for name,value in [('fechaEmision',date.fromisoformat(str(data['date'])).strftime('%d/%m/%Y')),('dirEstablecimiento',data.get('establishment_address') or data['issuer_address']),('tipoIdentificacionComprador',data['buyer_type']),('razonSocialComprador',data['buyer_name']),('identificacionComprador',data['buyer_vat'])]:add(info,name,value)
    if data.get('accounting'):add(info,'obligadoContabilidad',data['accounting'])
    add(info,'codDocModificado',data['modified_type']);add(info,'numDocModificado',data['modified_number'])
    add(info,'fechaEmisionDocSustento',date.fromisoformat(str(data['modified_date'])).strftime('%d/%m/%Y'))
    add(info,'totalSinImpuestos',f'{base_total:.2f}')
    taxes=etree.SubElement(info,'impuestos')
    for code,(rate,base,tax) in groups.items():
        node=etree.SubElement(taxes,'impuesto')
        for name,value in [('codigo','2'),('codigoPorcentaje',code),('tarifa',format(rate,'f')),('baseImponible',f'{base:.2f}'),('valor',f'{tax:.2f}')]:add(node,name,value)
    add(info,'valorTotal',f'{base_total+tax_total:.2f}')
    if data.get('payment'):
        payment=etree.SubElement(etree.SubElement(info,'pagos'),'pago')
        add(payment,'formaPago',data['payment']);add(payment,'total',f'{base_total+tax_total:.2f}')
    motives=etree.SubElement(root,'motivos')
    for reason,base in reasons:
        node=etree.SubElement(motives,'motivo');add(node,'razon',reason);add(node,'valor',f'{base:.2f}')
    schema=etree.XMLSchema(etree.parse(str(Path(__file__).parent/'xsd/NotaDebito_V1.0.0.xsd'),etree.XMLParser(no_network=True,resolve_entities=False)))
    if not schema.validate(root):raise ValueError('XML incompatible con el esquema SRI: '+str(schema.error_log.last_error))
    return key,etree.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
