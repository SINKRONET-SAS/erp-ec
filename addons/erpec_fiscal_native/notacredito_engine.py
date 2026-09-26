"""Preparación XML local de nota de crédito; sin firma ni transmisión (eso lo hace
erpec_fiscal_sri, igual que con factura). Reutiliza money()/modulo11()/access_key() de
engine.py -- no se duplica la fórmula del módulo 11 ni el redondeo. Estructura y nombres de
elemento confirmados contra addons/erpec_fiscal_native/xsd/NotaCredito_V1.1.0.xsd (fuente
primaria, descargada del ZIP oficial del SRI: XML y XSD Nota de Crédito, versión 1.0.0-1.1.0);
no se inventa ningún campo."""
from decimal import Decimal
from datetime import date
from pathlib import Path
import re
from lxml import etree

from .engine import access_key, money, append_info_adicional

DOC_TYPE = '04'


def generate(data):
    """`data` espera las mismas claves que engine.generate() (date/number/issuer_*/buyer_*/
    payment no se usa aquí/total/items) MÁS: modified_type (código del comprobante que se
    modifica, ej. '01' factura), modified_number (est-ptoemi-secuencial de ese documento),
    modified_date (fecha de emisión de ese documento), reason (motivo de la nota de crédito).
    El esquema de notaCredito no tiene bloque de pagos (a diferencia de factura)."""
    key=access_key(data['date'],data['issuer_vat'],data['number'],data['numeric'],doc_type=DOC_TYPE,ambiente=data.get('ambiente','1'))
    if data['buyer_type'] not in ('04','05') or not re.fullmatch(r'[0-9]{13}' if data['buyer_type']=='04' else r'[0-9]{10}',data['buyer_vat'] or ''):
        raise ValueError('Este incremento requiere comprador identificado con RUC o cédula.')
    if not re.fullmatch(r'[0-9]{2}',data.get('modified_type') or ''):
        raise ValueError('Indica el código del tipo de comprobante que se modifica.')
    if not re.fullmatch(r'[0-9]{3}-[0-9]{3}-[0-9]{9}',data.get('modified_number') or ''):
        raise ValueError('Indica establecimiento-punto-secuencial (3-3-9) del documento que se modifica.')
    if not (data.get('reason') or '').strip():
        raise ValueError('Indica el motivo de la nota de crédito.')
    for field in ('issuer_name','issuer_address','buyer_name','buyer_address'):
        if not data.get(field):raise ValueError('Completa razón social y direcciones de emisor y comprador.')
    root=etree.Element('notaCredito',id='comprobante',version='1.1.0')
    def add(parent,name,value):
        node=etree.SubElement(parent,name);node.text=str(value);return node
    tributary=etree.SubElement(root,'infoTributaria')
    establishment,point,sequence=data['number'].split('-')
    for name,value in [('ambiente',data.get('ambiente','1')),('tipoEmision','1'),('razonSocial',data['issuer_name']),('ruc',data['issuer_vat']),('claveAcceso',key),('codDoc',DOC_TYPE),('estab',establishment),('ptoEmi',point),('secuencial',sequence),('dirMatriz',data['issuer_address'])]:add(tributary,name,value)
    lines=[];groups={};base_total=Decimal(0);tax_total=Decimal(0)
    for item in data['items']:
        qty=Decimal(str(item['quantity']));unit=Decimal(str(item['unit']));discount=Decimal(str(item['discount']))
        if not all(n.is_finite() for n in (qty,unit,discount)) or qty<=0 or unit<0 or not 0<=discount<=100:
            raise ValueError('Revisa cantidades, precios y descuento.')
        rate=Decimal(str(item['rate']))
        if rate not in (0,15):raise ValueError('El incremento local admite IVA 0 y 15; otras tarifas requieren ampliar y validar el perfil.')
        reduction=money(qty*unit*discount/100);base=money(qty*unit-reduction);tax=money(base*rate/100)
        if base!=money(item['subtotal']) or tax!=money(item['tax']):
            raise ValueError('Los redondeos del XML no coinciden con la nota de crédito; revisar antes de continuar.')
        code='0' if rate==0 else '4'
        g=groups.setdefault(code,[Decimal(0),Decimal(0)]);g[0]+=base;g[1]+=tax
        lines.append((item,qty,unit,reduction,base,rate,code,tax));base_total+=base;tax_total+=tax
    if not lines or base_total+tax_total<=0 or base_total+tax_total!=money(data['total']):
        raise ValueError('El total del XML no coincide con la nota de crédito positiva.')
    info=etree.SubElement(root,'infoNotaCredito')
    for name,value in [('fechaEmision',date.fromisoformat(str(data['date'])).strftime('%d/%m/%Y')),('dirEstablecimiento',data.get('establishment_address') or data['issuer_address']),('tipoIdentificacionComprador',data['buyer_type']),('razonSocialComprador',data['buyer_name']),('identificacionComprador',data['buyer_vat'])]:add(info,name,value)
    if data.get('accounting'):add(info,'obligadoContabilidad',data['accounting'])
    add(info,'codDocModificado',data['modified_type']);add(info,'numDocModificado',data['modified_number'])
    add(info,'fechaEmisionDocSustento',date.fromisoformat(str(data['modified_date'])).strftime('%d/%m/%Y'))
    add(info,'totalSinImpuestos',f'{base_total:.2f}')
    add(info,'valorModificacion',f'{base_total+tax_total:.2f}')
    add(info,'moneda','DOLAR')
    totals=etree.SubElement(info,'totalConImpuestos')
    for code,(base,tax) in groups.items():
        node=etree.SubElement(totals,'totalImpuesto')
        for name,value in [('codigo','2'),('codigoPorcentaje',code),('baseImponible',f'{base:.2f}'),('valor',f'{tax:.2f}')]:add(node,name,value)
    add(info,'motivo',data['reason'])
    details=etree.SubElement(root,'detalles')
    for item,qty,unit,reduction,base,rate,code,tax in lines:
        node=etree.SubElement(details,'detalle')
        for name,value in [('descripcion',item['description']),('cantidad',format(qty,'f')),('precioUnitario',format(unit,'f')),('descuento',f'{reduction:.2f}'),('precioTotalSinImpuesto',f'{base:.2f}')]:add(node,name,value)
        vat=etree.SubElement(etree.SubElement(node,'impuestos'),'impuesto')
        for name,value in [('codigo','2'),('codigoPorcentaje',code),('tarifa',format(rate,'f')),('baseImponible',f'{base:.2f}'),('valor',f'{tax:.2f}')]:add(vat,name,value)
    append_info_adicional(root,data.get('info_adicional'))
    schema=etree.XMLSchema(etree.parse(str(Path(__file__).parent/'xsd/NotaCredito_V1.1.0.xsd'),etree.XMLParser(no_network=True,resolve_entities=False)))
    if not schema.validate(root):raise ValueError('XML incompatible con el esquema SRI: '+str(schema.error_log.last_error))
    return key,etree.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
