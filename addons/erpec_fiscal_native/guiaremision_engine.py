"""Preparación XML local de guía de remisión (codDoc 06); sin firma ni transmisión (eso lo hace
erpec_fiscal_sri). Estructura confirmada contra addons/erpec_fiscal_native/xsd/GuiaRemision_V1.1.0.xsd
(ZIP oficial del SRI). La guía no lleva valores ni impuestos: solo transportista, destinatario y bienes."""
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from lxml import etree

from .engine import access_key, append_info_adicional

DOC_TYPE = '06'


def _fmt(day):
    return date.fromisoformat(str(day)).strftime('%d/%m/%Y')


def generate(data):
    """`data`: date (emisión), number, numeric, ambiente, issuer_*, establishment_address, accounting,
    origin_address, carrier_type ('04'..'08'), carrier_vat/name, plate, date_start, date_end,
    recipient_vat/name/address, reason, support (opcional: {doc_type, doc_number, doc_date,
    doc_authorization}) e items [{code, description, quantity}]."""
    key=access_key(data['date'],data['issuer_vat'],data['number'],data['numeric'],doc_type=DOC_TYPE,ambiente=data.get('ambiente','1'))
    for field in ('issuer_name','issuer_address','origin_address','carrier_name','carrier_vat','plate','recipient_vat','recipient_name','recipient_address','reason'):
        if not (data.get(field) or '').strip():
            raise ValueError('Completa emisor, dirección de partida, transportista, placa, destinatario y motivo del traslado.')
    if data.get('carrier_type') not in ('04','05','06','07','08'):
        raise ValueError('Indica el tipo de identificación del transportista.')
    if data['carrier_type']=='04' and not re.fullmatch(r'[0-9]{13}',data['carrier_vat']):
        raise ValueError('El RUC del transportista debe tener 13 dígitos.')
    if data['carrier_type']=='05' and not re.fullmatch(r'[0-9]{10}',data['carrier_vat']):
        raise ValueError('La cédula del transportista debe tener 10 dígitos.')
    if date.fromisoformat(str(data['date_end']))<date.fromisoformat(str(data['date_start'])):
        raise ValueError('La fecha de fin de transporte no puede ser anterior a la de inicio.')
    if date.fromisoformat(str(data['date_start']))<date.fromisoformat(str(data['date'])):
        raise ValueError('La guía debe emitirse antes de iniciar el traslado.')
    if not data.get('items'):
        raise ValueError('La guía requiere al menos un bien a trasladar.')
    support=data.get('support') or {}
    if support and not re.fullmatch(r'[0-9]{3}-[0-9]{3}-[0-9]{9}',support.get('doc_number') or ''):
        raise ValueError('El comprobante de sustento requiere establecimiento-punto-secuencial (3-3-9).')
    root=etree.Element('guiaRemision',id='comprobante',version='1.1.0')
    def add(parent,name,value):
        node=etree.SubElement(parent,name);node.text=str(value);return node
    tributary=etree.SubElement(root,'infoTributaria')
    establishment,point,sequence=data['number'].split('-')
    for name,value in [('ambiente',data.get('ambiente','1')),('tipoEmision','1'),('razonSocial',data['issuer_name']),('ruc',data['issuer_vat']),('claveAcceso',key),('codDoc',DOC_TYPE),('estab',establishment),('ptoEmi',point),('secuencial',sequence),('dirMatriz',data['issuer_address'])]:add(tributary,name,value)
    info=etree.SubElement(root,'infoGuiaRemision')
    add(info,'dirEstablecimiento',data.get('establishment_address') or data['issuer_address'])
    add(info,'dirPartida',data['origin_address']);add(info,'razonSocialTransportista',data['carrier_name'])
    add(info,'tipoIdentificacionTransportista',data['carrier_type']);add(info,'rucTransportista',data['carrier_vat'])
    if data.get('accounting'):add(info,'obligadoContabilidad',data['accounting'])
    add(info,'fechaIniTransporte',_fmt(data['date_start']));add(info,'fechaFinTransporte',_fmt(data['date_end']));add(info,'placa',data['plate'])
    recipients=etree.SubElement(root,'destinatarios');recipient=etree.SubElement(recipients,'destinatario')
    add(recipient,'identificacionDestinatario',data['recipient_vat']);add(recipient,'razonSocialDestinatario',data['recipient_name'])
    add(recipient,'dirDestinatario',data['recipient_address']);add(recipient,'motivoTraslado',data['reason'][:300])
    if support:
        add(recipient,'codDocSustento',support.get('doc_type') or '01');add(recipient,'numDocSustento',support['doc_number'])
        if support.get('doc_authorization'):add(recipient,'numAutDocSustento',support['doc_authorization'])
        add(recipient,'fechaEmisionDocSustento',_fmt(support['doc_date']))
    details=etree.SubElement(recipient,'detalles')
    for item in data['items']:
        try:quantity=Decimal(str(item['quantity']))
        except InvalidOperation as error:raise ValueError('Revisa las cantidades de la guía.') from error
        if not quantity.is_finite() or quantity<=0 or not (item.get('description') or '').strip():
            raise ValueError('Cada bien requiere descripción y una cantidad positiva.')
        node=etree.SubElement(details,'detalle')
        if item.get('code'):add(node,'codigoInterno',str(item['code'])[:25])
        add(node,'descripcion',item['description'][:300]);add(node,'cantidad',format(quantity,'f'))
    append_info_adicional(root,data.get('info_adicional'))
    schema=etree.XMLSchema(etree.parse(str(Path(__file__).parent/'xsd/GuiaRemision_V1.1.0.xsd'),etree.XMLParser(no_network=True,resolve_entities=False)))
    if not schema.validate(root):raise ValueError('XML incompatible con el esquema SRI: '+str(schema.error_log.last_error))
    return key,etree.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
