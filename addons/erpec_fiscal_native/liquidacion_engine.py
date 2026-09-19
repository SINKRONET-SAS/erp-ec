"""Preparación XML local de liquidación de compra de bienes y prestación de servicios (codDoc 03,
versión 1.1.0); sin firma ni transmisión (eso lo hace erpec_fiscal_sri). Estructura confirmada contra
addons/erpec_fiscal_native/xsd/LiquidacionCompra_V1.1.0.xsd (ZIP oficial del SRI). Es el comprobante que
el comprador emite a un proveedor que no puede emitir factura; el proveedor puede ser persona natural
sin RUC (cédula o pasaporte)."""
from decimal import Decimal
from datetime import date
from pathlib import Path
import re
from lxml import etree

from .engine import access_key, money

DOC_TYPE = '03'


def generate(data):
    """`data` como engine.generate() pero con proveedor en lugar de comprador: provider_type ('04'..'08'),
    provider_vat/name/address. Sin propina; IVA 0 y 15."""
    key=access_key(data['date'],data['issuer_vat'],data['number'],data['numeric'],doc_type=DOC_TYPE,ambiente=data.get('ambiente','1'))
    if data.get('provider_type') not in ('04','05','06','08'):
        raise ValueError('Indica el tipo de identificación del proveedor.')
    if not (data.get('provider_vat') or '').strip():
        raise ValueError('Indica la identificación del proveedor.')
    if data['provider_type']=='04' and not re.fullmatch(r'[0-9]{13}',data['provider_vat']):
        raise ValueError('El RUC del proveedor debe tener 13 dígitos.')
    if data['provider_type']=='05' and not re.fullmatch(r'[0-9]{10}',data['provider_vat']):
        raise ValueError('La cédula del proveedor debe tener 10 dígitos.')
    if data['payment'] not in ('01','15','16','17','18','19','20','21'):
        raise ValueError('Selecciona una forma de pago válida del catálogo SRI.')
    for field in ('issuer_name','issuer_address','provider_name'):
        if not data.get(field):raise ValueError('Completa razón social y dirección del emisor y razón social del proveedor.')
    root=etree.Element('liquidacionCompra',id='comprobante',version='1.1.0')
    def add(parent,name,value):
        node=etree.SubElement(parent,name);node.text=str(value);return node
    tributary=etree.SubElement(root,'infoTributaria')
    establishment,point,sequence=data['number'].split('-')
    for name,value in [('ambiente',data.get('ambiente','1')),('tipoEmision','1'),('razonSocial',data['issuer_name']),('ruc',data['issuer_vat']),('claveAcceso',key),('codDoc',DOC_TYPE),('estab',establishment),('ptoEmi',point),('secuencial',sequence),('dirMatriz',data['issuer_address'])]:add(tributary,name,value)
    lines=[];groups={};discount_total=Decimal(0);base_total=Decimal(0);tax_total=Decimal(0)
    for item in data['items']:
        qty=Decimal(str(item['quantity']));unit=Decimal(str(item['unit']));discount=Decimal(str(item['discount']))
        if not all(n.is_finite() for n in (qty,unit,discount)) or qty<=0 or unit<0 or not 0<=discount<=100:
            raise ValueError('Revisa cantidades, precios y descuento.')
        rate=Decimal(str(item['rate']))
        if rate not in (0,15):raise ValueError('El incremento local admite IVA 0 y 15; otras tarifas requieren ampliar y validar el perfil.')
        reduction=money(qty*unit*discount/100);base=money(qty*unit-reduction);tax=money(base*rate/100)
        if base!=money(item['subtotal']) or tax!=money(item['tax']):
            raise ValueError('Los redondeos del XML no coinciden con la liquidación; revisar antes de continuar.')
        code='0' if rate==0 else '4'
        g=groups.setdefault(code,[rate,Decimal(0),Decimal(0)]);g[1]+=base;g[2]+=tax
        lines.append((item,qty,unit,reduction,base,rate,code,tax));discount_total+=reduction;base_total+=base;tax_total+=tax
    if not lines or base_total+tax_total<=0 or base_total+tax_total!=money(data['total']):
        raise ValueError('El total del XML no coincide con la liquidación positiva.')
    info=etree.SubElement(root,'infoLiquidacionCompra')
    for name,value in [('fechaEmision',date.fromisoformat(str(data['date'])).strftime('%d/%m/%Y')),('dirEstablecimiento',data.get('establishment_address') or data['issuer_address'])]:add(info,name,value)
    if data.get('accounting'):add(info,'obligadoContabilidad',data['accounting'])
    add(info,'tipoIdentificacionProveedor',data['provider_type']);add(info,'razonSocialProveedor',data['provider_name']);add(info,'identificacionProveedor',data['provider_vat'])
    if data.get('provider_address'):add(info,'direccionProveedor',data['provider_address'])
    add(info,'totalSinImpuestos',f'{base_total:.2f}');add(info,'totalDescuento',f'{discount_total:.2f}')
    totals=etree.SubElement(info,'totalConImpuestos')
    for code,(rate,base,tax) in groups.items():
        node=etree.SubElement(totals,'totalImpuesto')
        for name,value in [('codigo','2'),('codigoPorcentaje',code),('baseImponible',f'{base:.2f}'),('tarifa',format(rate,'f')),('valor',f'{tax:.2f}')]:add(node,name,value)
    add(info,'importeTotal',f'{base_total+tax_total:.2f}');add(info,'moneda','DOLAR')
    payment=etree.SubElement(etree.SubElement(info,'pagos'),'pago');add(payment,'formaPago',data['payment']);add(payment,'total',f'{base_total+tax_total:.2f}')
    details=etree.SubElement(root,'detalles')
    for item,qty,unit,reduction,base,rate,code,tax in lines:
        node=etree.SubElement(details,'detalle')
        for name,value in [('codigoPrincipal',item['code']),('descripcion',item['description']),('cantidad',format(qty,'f')),('precioUnitario',format(unit,'f')),('descuento',f'{reduction:.2f}'),('precioTotalSinImpuesto',f'{base:.2f}')]:add(node,name,value)
        vat=etree.SubElement(etree.SubElement(node,'impuestos'),'impuesto')
        for name,value in [('codigo','2'),('codigoPorcentaje',code),('tarifa',format(rate,'f')),('baseImponible',f'{base:.2f}'),('valor',f'{tax:.2f}')]:add(vat,name,value)
    schema=etree.XMLSchema(etree.parse(str(Path(__file__).parent/'xsd/LiquidacionCompra_V1.1.0.xsd'),etree.XMLParser(no_network=True,resolve_entities=False)))
    if not schema.validate(root):raise ValueError('XML incompatible con el esquema SRI: '+str(schema.error_log.last_error))
    return key,etree.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
