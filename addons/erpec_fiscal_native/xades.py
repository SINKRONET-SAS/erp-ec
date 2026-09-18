"""Firma XAdES-BES local; no reserva secuencias ni transmite comprobantes."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re
import uuid
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree

DS='http://www.w3.org/2000/09/xmldsig#'
XA='http://uri.etsi.org/01903/v1.3.2#'
C14N='http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
SHA256='http://www.w3.org/2001/04/xmlenc#sha256'
RSA256='http://www.w3.org/2001/04/xmldsig-more#rsa-sha256'
ENV=DS+'enveloped-signature'
NS={'ds':DS,'xades':XA}

def canonical(node):
    return etree.tostring(node,method='c14n',exclusive=False,with_comments=False)

def b64(value):
    return base64.b64encode(value).decode('ascii')

def digest(value):
    return b64(hashlib.sha256(value).digest())

def parse_xml(xml):
    if len(xml)>5_000_000:
        raise ValueError('XML demasiado grande.')
    parser=etree.XMLParser(resolve_entities=False,no_network=True,load_dtd=False,remove_blank_text=False)
    try:
        root=etree.fromstring(xml,parser)
    except etree.XMLSyntaxError as error:
        raise ValueError('XML inválido.') from error
    if root.getroottree().docinfo.doctype or any(isinstance(n,etree._Entity) for n in root.iter()):
        raise ValueError('No se admiten DTD ni entidades XML.')
    ids=[v for n in root.iter() for k,v in n.attrib.items() if k.lower()=='id']
    if len(ids)!=len(set(ids)):
        raise ValueError('El XML contiene identificadores duplicados.')
    return root

def credentials(p12,password,issuer_ruc,now=None):
    try:
        key,cert,chain=pkcs12.load_key_and_certificates(p12,password)
    except ValueError as error:
        raise ValueError('No se pudo abrir el certificado con la contraseña indicada.') from error
    if not isinstance(key,rsa.RSAPrivateKey) or cert is None or key.key_size<2048:
        raise ValueError('Se requiere certificado con clave RSA de al menos 2048 bits.')
    if key.public_key().public_numbers()!=cert.public_key().public_numbers():
        raise ValueError('La clave no corresponde al certificado.')
    current=now or datetime.now(timezone.utc)
    if not cert.not_valid_before_utc<=current<=cert.not_valid_after_utc:
        raise ValueError('El certificado está fuera de vigencia.')
    if not re.fullmatch(r'[0-9]{13}',issuer_ruc or ''):
        raise ValueError('RUC del emisor incompleto.')
    identities=[str(a.value) for a in cert.subject]
    exact=any(issuer_ruc==v or v.startswith(issuer_ruc+'-') for v in identities)
    personal=int(issuer_ruc[2])<6 and issuer_ruc.endswith('001') and any(
        v==issuer_ruc[:10] or v.startswith(issuer_ruc[:10]+'-') for v in identities)
    if not exact and not personal:
        raise ValueError('El identificador del certificado no corresponde al emisor.')
    try:
        usage=cert.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound as error:
        raise ValueError('El certificado no declara uso de clave de firma.') from error
    if not usage.digital_signature and not usage.content_commitment:
        raise ValueError('El certificado no permite firma de documentos.')
    return key,cert,chain or []

# Comprobantes electrónicos SRI admitidos: cada uno comparte el mismo bloque infoTributaria
# (ambiente/ruc/claveAcceso/codDoc/...), por eso sign()/verify() son agnósticos al tipo de
# documento y solo validan la etiqueta raíz contra este catálogo -- ver xsd/*.xsd de cada uno.
COMPROBANTE_TAGS = {'factura', 'notaCredito', 'notaDebito', 'guiaRemision'}


def sign(xml,p12,password,issuer_ruc,now=None):
    root=parse_xml(xml)
    if root.tag not in COMPROBANTE_TAGS or root.get('id')!='comprobante' or root.findtext('infoTributaria/ruc')!=issuer_ruc:
        raise ValueError('Se requiere un comprobante del emisor con id comprobante.')
    if root.xpath('//ds:Signature',namespaces=NS):
        raise ValueError('El XML ya tiene una firma; no se vuelve a firmar.')
    key,cert,chain=credentials(p12,password,issuer_ruc,now)
    uid=uuid.uuid4().hex
    signature=etree.SubElement(root,'{'+DS+'}Signature',nsmap=NS,Id='Signature-'+uid)
    def add(parent,ns,name,text=None,**attrs):
        node=etree.SubElement(parent,'{'+ns+'}'+name,**attrs)
        if text is not None:node.text=str(text)
        return node
    info=add(signature,DS,'SignedInfo')
    add(info,DS,'CanonicalizationMethod',Algorithm=C14N)
    add(info,DS,'SignatureMethod',Algorithm=RSA256)
    value=add(signature,DS,'SignatureValue')
    keyinfo=add(signature,DS,'KeyInfo',Id='KeyInfo-'+uid)
    certs=add(keyinfo,DS,'X509Data')
    for item in [cert]+chain:
        add(certs,DS,'X509Certificate',b64(item.public_bytes(serialization.Encoding.DER)))
    object_node=add(signature,DS,'Object')
    properties=add(object_node,XA,'QualifyingProperties',Target='#Signature-'+uid)
    signed=add(properties,XA,'SignedProperties',Id='SignedProperties-'+uid)
    signature_props=add(signed,XA,'SignedSignatureProperties')
    add(signature_props,XA,'SigningTime',(now or datetime.now(timezone.utc)).isoformat(timespec='seconds'))
    signedcert=add(add(signature_props,XA,'SigningCertificate'),XA,'Cert')
    certdigest=add(signedcert,XA,'CertDigest')
    add(certdigest,DS,'DigestMethod',Algorithm=SHA256)
    add(certdigest,DS,'DigestValue',digest(cert.public_bytes(serialization.Encoding.DER)))
    issuer=add(signedcert,XA,'IssuerSerial')
    add(issuer,DS,'X509IssuerName',cert.issuer.rfc4514_string())
    add(issuer,DS,'X509SerialNumber',cert.serial_number)
    data_props=add(signed,XA,'SignedDataObjectProperties')
    data_format=add(data_props,XA,'DataObjectFormat',ObjectReference='#Document-'+uid)
    add(data_format,XA,'Description','Factura electrónica')
    add(data_format,XA,'MimeType','text/xml')
    unsigned=deepcopy(root);unsigned.remove(unsigned.find('{'+DS+'}Signature'))
    for target,content,kind in [('comprobante',canonical(unsigned),'document'),
                                ('KeyInfo-'+uid,canonical(keyinfo),'key'),
                                ('SignedProperties-'+uid,canonical(signed),'properties')]:
        attrs={'URI':'#'+target}
        if kind=='document':attrs['Id']='Document-'+uid
        if kind=='properties':attrs['Type']='http://uri.etsi.org/01903#SignedProperties'
        ref=add(info,DS,'Reference',**attrs)
        transforms=add(ref,DS,'Transforms')
        if kind=='document':add(transforms,DS,'Transform',Algorithm=ENV)
        add(transforms,DS,'Transform',Algorithm=C14N)
        add(ref,DS,'DigestMethod',Algorithm=SHA256)
        add(ref,DS,'DigestValue',digest(content))
    value.text=b64(key.sign(canonical(info),padding.PKCS1v15(),hashes.SHA256()))
    return etree.tostring(root,encoding='UTF-8',xml_declaration=True)

def verify(xml,expected_certificate):
    """Comprueba firma, referencias y certificado esperado; no valida confianza ni revocación."""
    root=parse_xml(xml)
    signatures=root.xpath('//ds:Signature',namespaces=NS)
    if len(signatures)!=1 or signatures[0].getparent()!=root:
        raise ValueError('Se requiere una única firma al final del comprobante.')
    signature=signatures[0]
    info=signature.find('ds:SignedInfo',NS)
    if info is None or info.find('ds:SignatureMethod',NS).get('Algorithm')!=RSA256 or info.find('ds:CanonicalizationMethod',NS).get('Algorithm')!=C14N:
        raise ValueError('Algoritmo de firma no admitido.')
    refs=info.findall('ds:Reference',NS)
    if len(refs)!=3:raise ValueError('La firma debe proteger documento, certificado y propiedades.')
    expected_targets={'#comprobante','#'+signature.find('ds:KeyInfo',NS).get('Id'),
                      '#'+signature.find('.//xades:SignedProperties',NS).get('Id')}
    if {r.get('URI') for r in refs}!=expected_targets:
        raise ValueError('Referencias de firma inesperadas.')
    for ref in refs:
        uri=ref.get('URI')
        targets=root.xpath('//*[@id=$id or @Id=$id]',id=uri[1:])
        if len(targets)!=1:raise ValueError('Referencia ambigua o inexistente.')
        node=deepcopy(targets[0])
        transforms=[t.get('Algorithm') for t in ref.findall('ds:Transforms/ds:Transform',NS)]
        if transforms!=([ENV,C14N] if uri=='#comprobante' else [C14N]):
            raise ValueError('Transformación XML no admitida.')
        if uri=='#comprobante':node.remove(node.find('{'+DS+'}Signature'))
        else:node=targets[0]
        if ref.find('ds:DigestMethod',NS).get('Algorithm')!=SHA256 or digest(canonical(node))!=ref.findtext('ds:DigestValue',namespaces=NS):
            raise ValueError('El XML o sus propiedades fueron modificados.')
    certdata=base64.b64decode(signature.findtext('ds:KeyInfo/ds:X509Data/ds:X509Certificate',namespaces=NS),validate=True)
    if certdata!=expected_certificate.public_bytes(serialization.Encoding.DER):
        raise ValueError('Certificado diferente del esperado.')
    expected_certificate.public_key().verify(base64.b64decode(signature.findtext('ds:SignatureValue',namespaces=NS),validate=True),
        canonical(info),padding.PKCS1v15(),hashes.SHA256())
    return True
