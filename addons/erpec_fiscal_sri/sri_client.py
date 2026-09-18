"""Cliente SOAP real contra los servicios web del SRI (Recepción y Autorización de
comprobantes electrónicos). Ambos ambientes tienen endpoint; quién puede usar producción lo decide
la capa Odoo (erpec.fiscal.point: certificado verificado + habilitación explícita del cliente), no
este cliente. La transmisión real a producción NO se ha probado en este proyecto (solo PRUEBAS).

Fuente de los WSDL: los mismos endpoints documentados y usados de verdad por el proyecto de
referencia sinkroniq-mobile (backend/src/config/sriConfig.js), confirmados alcanzables desde
este entorno (celcer.sri.gob.ec respondió 200 al WSDL de Recepción, 13-09-2026)."""
import logging

import zeep
from zeep.transports import Transport

_logger = logging.getLogger(__name__)

AMBIENTES = {
    '1': {
        'label': 'Pruebas',
        'recepcion': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
        'autorizacion': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
        'enabled': True,
    },
    '2': {
        'label': 'Producción',
        'recepcion': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
        'autorizacion': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
        'enabled': True,  # La emisión en producción solo es alcanzable desde un punto de emisión habilitado explícitamente (erpec.fiscal.point).
    },
}


class SriError(Exception):
    def __init__(self, code, retry=False):
        self.code, self.retry = code, retry
        super().__init__(code)


def _client(wsdl_url, timeout=20):
    transport = Transport(timeout=timeout, operation_timeout=timeout)
    return zeep.Client(wsdl_url, transport=transport)


def enviar_recepcion(xml_firmado, ambiente='1', client_factory=_client):
    """Envía el XML ya firmado a RecepcionComprobantesOffline.validarComprobante.
    Devuelve ('RECIBIDA'|'DEVUELTA', [mensajes]). No reintenta rechazos definitivos aquí:
    esa decisión la toma quien orquesta la cola (mirar SriError.retry)."""
    config = AMBIENTES.get(ambiente)
    if not config or not config['enabled']:
        raise SriError('AMBIENTE_NO_HABILITADO')
    try:
        client = client_factory(config['recepcion'])
        response = client.service.validarComprobante(xml=xml_firmado)
    except zeep.exceptions.Fault as error:
        raise SriError('SRI_FAULT: ' + str(error), retry=True) from error
    except Exception as error:  # noqa: BLE001 - errores de red/timeout de zeep no son un tipo único
        raise SriError('SRI_CONEXION: ' + str(error), retry=True) from error
    estado = getattr(response, 'estado', None)
    if estado not in ('RECIBIDA', 'DEVUELTA'):
        raise SriError('SRI_ESTADO_DESCONOCIDO: ' + str(estado), retry=True)
    mensajes = _extract_mensajes(response)
    return estado, mensajes


def consultar_autorizacion(clave_acceso, ambiente='1', client_factory=_client):
    """Consulta AutorizacionComprobantesOffline.autorizacionComprobante. Devuelve
    (estado, autorizacion_o_none, [mensajes]) donde estado es uno de
    AUTORIZADO / NO AUTORIZADO / EN PROCESO / PENDIENTE (sin autorizaciones aún).
    `autorizacion_o_none` es {'comprobante': bytes, 'numero': str, 'fecha': str} solo cuando
    estado == 'AUTORIZADO'; zeep ya entrega la respuesta parseada (no XML crudo por envolver)."""
    config = AMBIENTES.get(ambiente)
    if not config or not config['enabled']:
        raise SriError('AMBIENTE_NO_HABILITADO')
    try:
        client = client_factory(config['autorizacion'])
        response = client.service.autorizacionComprobante(claveAccesoComprobante=clave_acceso)
    except zeep.exceptions.Fault as error:
        raise SriError('SRI_FAULT: ' + str(error), retry=True) from error
    except Exception as error:  # noqa: BLE001
        raise SriError('SRI_CONEXION: ' + str(error), retry=True) from error
    autorizaciones = getattr(getattr(response, 'autorizaciones', None), 'autorizacion', None) or []
    if not autorizaciones:
        return 'PENDIENTE', None, []
    primera = autorizaciones[0]
    estado = getattr(primera, 'estado', None)
    if estado not in ('AUTORIZADO', 'NO AUTORIZADO', 'EN PROCESO'):
        raise SriError('SRI_ESTADO_AUTORIZACION_DESCONOCIDO: ' + str(estado), retry=True)
    mensajes = _extract_mensajes(primera)
    if estado != 'AUTORIZADO':
        return estado, None, mensajes
    comprobante = getattr(primera, 'comprobante', '') or ''
    autorizacion = {
        'comprobante': comprobante.encode('utf-8') if isinstance(comprobante, str) else comprobante,
        'numero': getattr(primera, 'numeroAutorizacion', '') or '',
        'fecha': str(getattr(primera, 'fechaAutorizacion', '') or ''),
    }
    return estado, autorizacion, mensajes


def _extract_mensajes(node):
    mensajes = getattr(getattr(node, 'mensajes', None), 'mensaje', None) or []
    result = []
    for mensaje in mensajes:
        result.append({
            'identificador': getattr(mensaje, 'identificador', None),
            'mensaje': getattr(mensaje, 'mensaje', None),
            'informacionAdicional': getattr(mensaje, 'informacionAdicional', None),
            'tipo': getattr(mensaje, 'tipo', None),
        })
    return result
