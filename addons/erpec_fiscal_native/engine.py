"""Preparación XML local de factura ordinaria; sin firma ni transmisión."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from pathlib import Path
import re
from lxml import etree


def money(value):
    number=Decimal(str(value))
    if not number.is_finite():
        raise ValueError('Importe no finito.')
    return number.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)


def modulo11(digits):
    if not re.fullmatch(r'[0-9]+',digits):
        raise ValueError('El módulo 11 requiere dígitos.')
    digit=11-sum(int(n)*(2+i%6) for i,n in enumerate(reversed(digits)))%11
    return 0 if digit==11 else 1 if digit==10 else digit


def access_key(day,ruc,number,numeric,doc_type='01'):
    if not re.fullmatch(r'[0-9]{13}',ruc or ''):
        raise ValueError('Completa el RUC real del emisor (13 dígitos); no se inventa en la demo.')
    if not re.fullmatch(r'[0-9]{3}-[0-9]{3}-[0-9]{9}',number or '') or any(int(x)==0 for x in number.split('-')):
        raise ValueError('Revisa establecimiento, punto y secuencial del documento contabilizado.')
    if not re.fullmatch(r'[0-9]{8}',numeric):
        raise ValueError('El código numérico requiere ocho dígitos.')
    if not re.fullmatch(r'[0-9]{2}',doc_type or ''):
        raise ValueError('El código del tipo de comprobante requiere dos dígitos.')
    base=date.fromisoformat(str(day)).strftime('%d%m%Y')+doc_type+ruc+'1'+number.replace('-','')+numeric+'1'
    return base+str(modulo11(base))


def generate(data):
    key=access_key(data['date'],data['issuer_vat'],data['number'],data['numeric'])
    if data['buyer_type'] not in ('04','05') or not re.fullmatch(r'[0-9]{13}' if data['buyer_type']=='04' else r'[0-9]{10}',data['buyer_vat'] or ''):
        raise ValueError('Este incremento requiere comprador identificado con RUC o cédula.')
    if data['payment'] not in ('01','15','16','17','18','19','20','21'):
        raise ValueError('Selecciona una forma de pago válida del catálogo SRI.')
    for field in ('issuer_name','issuer_address','buyer_name','buyer_address'):
        if not data.get(field):raise ValueError('Completa razón social y direcciones de emisor y comprador.')
    root=etree.Element('factura',id='comprobante',version='2.1.0')
    def add(parent,name,value):
        node=etree.SubElement(parent,name);node.text=str(value);return node
    tributary=etree.SubElement(root,'infoTributaria')
    establishment,point,sequence=data['number'].split('-')
    for name,value in [('ambiente','1'),('tipoEmision','1'),('razonSocial',data['issuer_name']),('ruc',data['issuer_vat']),('claveAcceso',key),('codDoc','01'),('estab',establishment),('ptoEmi',point),('secuencial',sequence),('dirMatriz',data['issuer_address'])]:add(tributary,name,value)
    lines=[];groups={};discount_total=Decimal(0);base_total=Decimal(0);tax_total=Decimal(0)
    for item in data['items']:
        qty=Decimal(str(item['quantity']));unit=Decimal(str(item['unit']));discount=Decimal(str(item['discount']))
        if not all(n.is_finite() for n in (qty,unit,discount)) or qty<=0 or unit<0 or not 0<=discount<=100:
            raise ValueError('Revisa cantidades, precios y descuento.')
        rate=Decimal(str(item['rate']))
        if rate not in (0,15):raise ValueError('El incremento local admite IVA 0 y 15; otras tarifas requieren ampliar y validar el perfil.')
        reduction=money(qty*unit*discount/100);base=money(qty*unit-reduction);tax=money(base*rate/100)
        if base!=money(item['subtotal']) or tax!=money(item['tax']):
            raise ValueError('Los redondeos del XML no coinciden con la factura; revisar antes de continuar.')
        code='0' if rate==0 else '4'
        g=groups.setdefault(code,[Decimal(0),Decimal(0)]);g[0]+=base;g[1]+=tax
        lines.append((item,qty,unit,reduction,base,rate,code,tax));discount_total+=reduction;base_total+=base;tax_total+=tax
    if not lines or base_total+tax_total<=0 or base_total+tax_total!=money(data['total']):
        raise ValueError('El total del XML no coincide con la factura positiva.')
    info=etree.SubElement(root,'infoFactura')
    for name,value in [('fechaEmision',date.fromisoformat(str(data['date'])).strftime('%d/%m/%Y')),('dirEstablecimiento',data['issuer_address']),('obligadoContabilidad',data['accounting']),('tipoIdentificacionComprador',data['buyer_type']),('razonSocialComprador',data['buyer_name']),('identificacionComprador',data['buyer_vat']),('direccionComprador',data['buyer_address']),('totalSinImpuestos',f'{base_total:.2f}'),('totalDescuento',f'{discount_total:.2f}')]:add(info,name,value)
    totals=etree.SubElement(info,'totalConImpuestos')
    for code,(base,tax) in groups.items():
        node=etree.SubElement(totals,'totalImpuesto')
        for name,value in [('codigo','2'),('codigoPorcentaje',code),('baseImponible',f'{base:.2f}'),('valor',f'{tax:.2f}')]:add(node,name,value)
    add(info,'propina','0.00');add(info,'importeTotal',f'{base_total+tax_total:.2f}');add(info,'moneda','DOLAR')
    payment=etree.SubElement(etree.SubElement(info,'pagos'),'pago');add(payment,'formaPago',data['payment']);add(payment,'total',f'{base_total+tax_total:.2f}')
    details=etree.SubElement(root,'detalles')
    for item,qty,unit,reduction,base,rate,code,tax in lines:
        node=etree.SubElement(details,'detalle')
        for name,value in [('codigoPrincipal',item['code']),('descripcion',item['description']),('cantidad',format(qty,'f')),('precioUnitario',format(unit,'f')),('descuento',f'{reduction:.2f}'),('precioTotalSinImpuesto',f'{base:.2f}')]:add(node,name,value)
        vat=etree.SubElement(etree.SubElement(node,'impuestos'),'impuesto')
        for name,value in [('codigo','2'),('codigoPorcentaje',code),('tarifa',format(rate,'f')),('baseImponible',f'{base:.2f}'),('valor',f'{tax:.2f}')]:add(vat,name,value)
    schema=etree.XMLSchema(etree.parse(str(Path(__file__).parent/'xsd/factura_V2.1.0.xsd'),etree.XMLParser(no_network=True,resolve_entities=False)))
    if not schema.validate(root):raise ValueError('XML incompatible con el esquema SRI: '+str(schema.error_log.last_error))
    return key,etree.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
