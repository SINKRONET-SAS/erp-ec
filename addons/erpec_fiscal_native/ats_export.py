"""DI25-04.2 (pieza mínima, no el agregador completo): construye el bloque <compras> del XML del
ATS a partir de datos reales de compras del ERP, siguiendo el orden exacto de elementos que exige
xsd/at.xsd (secuencia estricta; XSD no admite reordenar). No es el agregador de todas las secciones
(compras/ventas/anulados/retenciones/reembolsos/notas) ni tiene estado propio, UI ni conciliación
con documentos origen -- eso sigue fuera de alcance (ver docs/ALCANCE_ATS_RDEP.md). Es la pieza
reutilizable que demuestra que se puede construir un XML real y válido a partir de datos del ERP,
no solo transcribir el ejemplo oficial del SRI.

`codSustento` no se inventa: si la línea trae uno ya clasificado (erpec_workspace.tax_intersection,
DI25-04 ya implementado para compras), se usa ese; si no, se exige explícitamente por parámetro --
esta función nunca elige un sustento por defecto en silencio.
"""
from decimal import Decimal, ROUND_HALF_UP

try:
    from . import ats_catalog
except ImportError:  # ejecutado como script suelto, fuera del paquete Odoo
    import ats_catalog

REQUIRED_HEADER_KEYS = ('tipo_id_informante', 'id_informante', 'razon_social', 'anio', 'mes', 'codigo_operativo')
# Estos campos son opcionales según xsd/at.xsd (minOccurs=0) pero el motor de validación real del
# DIMM (ValidacionATS.validarInformacion(), no solo el esquema) los exige en la práctica desde
# fechas de vigencia concretas (verificado contra el DIMM, no una suposición): totbasesImpReemb
# desde 03/2015, valRetBien10 desde 06/2015, valRetServ20 desde 06/2015, valRetServ50 desde
# enero/2016, y el bloque pagoExterior completo (el esquema lo permite vacío, el DIMM no).
REQUIRED_COMPRA_KEYS = (
    'cod_sustento', 'tp_id_prov', 'id_prov', 'tipo_comprobante', 'fecha_registro', 'establecimiento',
    'punto_emision', 'secuencial', 'fecha_emision', 'autorizacion', 'base_no_gra_iva', 'base_imponible',
    'base_imp_grav', 'base_imp_exe', 'monto_ice', 'monto_iva', 'val_ret_bien10', 'val_ret_serv20',
    'valor_ret_bienes', 'val_ret_serv50', 'valor_ret_servicios', 'val_ret_serv100', 'tot_bases_imp_reemb',
    'pago_local_o_exterior', 'aplica_convenio_doble_tributacion', 'pago_exterior_sujeto_retencion_normativa',
)


def _money(value):
    return str(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _validate_header(header):
    missing = [key for key in REQUIRED_HEADER_KEYS if header.get(key) in (None, '')]
    if missing:
        raise ValueError('Faltan campos obligatorios del encabezado ATS: %s' % ', '.join(missing))
    if header['tipo_id_informante'] not in ('R',):
        raise ValueError('tipo_id_informante debe ser "R" (RUC); el catálogo del ATS no admite otro para el informante.')


def _validate_compra(compra):
    missing = [key for key in REQUIRED_COMPRA_KEYS if compra.get(key) in (None, '')]
    if missing:
        raise ValueError('Faltan campos obligatorios de una línea de compra ATS: %s' % ', '.join(missing))
    if compra['cod_sustento'] not in ats_catalog.SUPPORT_CODES:
        raise ValueError('codSustento %r no está en el catálogo oficial del ATS (ats_catalog.SUPPORT_CODES).' % compra['cod_sustento'])
    if compra['tipo_comprobante'] not in ats_catalog.VOUCHER_TYPES:
        raise ValueError('tipoComprobante %r no está en el catálogo oficial del ATS (ats_catalog.VOUCHER_TYPES).' % compra['tipo_comprobante'])
    valid_sustentos = ats_catalog.VOUCHER_TYPES[compra['tipo_comprobante']]['validSustento']
    if valid_sustentos and compra['cod_sustento'] not in valid_sustentos:
        raise ValueError('El comprobante %r no admite el sustento %r según el catálogo oficial.' % (compra['tipo_comprobante'], compra['cod_sustento']))


def build_compra_element(compra):
    """Un <detalleCompras>, en el orden exacto que exige detalleComprasType de at.xsd."""
    _validate_compra(compra)
    parts = [
        '<codSustento>%s</codSustento>' % compra['cod_sustento'],
        '<tpIdProv>%s</tpIdProv>' % compra['tp_id_prov'],
        '<idProv>%s</idProv>' % compra['id_prov'],
        '<tipoComprobante>%s</tipoComprobante>' % compra['tipo_comprobante'].zfill(2),
        '<fechaRegistro>%s</fechaRegistro>' % compra['fecha_registro'],
        '<establecimiento>%s</establecimiento>' % compra['establecimiento'],
        '<puntoEmision>%s</puntoEmision>' % compra['punto_emision'],
        '<secuencial>%s</secuencial>' % compra['secuencial'],
        '<fechaEmision>%s</fechaEmision>' % compra['fecha_emision'],
        '<autorizacion>%s</autorizacion>' % compra['autorizacion'],
        '<baseNoGraIva>%s</baseNoGraIva>' % _money(compra['base_no_gra_iva']),
        '<baseImponible>%s</baseImponible>' % _money(compra['base_imponible']),
        '<baseImpGrav>%s</baseImpGrav>' % _money(compra['base_imp_grav']),
        '<baseImpExe>%s</baseImpExe>' % _money(compra['base_imp_exe']),
        '<montoIce>%s</montoIce>' % _money(compra['monto_ice']),
        '<montoIva>%s</montoIva>' % _money(compra['monto_iva']),
        '<valRetBien10>%s</valRetBien10>' % _money(compra['val_ret_bien10']),
        '<valRetServ20>%s</valRetServ20>' % _money(compra['val_ret_serv20']),
        '<valorRetBienes>%s</valorRetBienes>' % _money(compra['valor_ret_bienes']),
        '<valRetServ50>%s</valRetServ50>' % _money(compra['val_ret_serv50']),
        '<valorRetServicios>%s</valorRetServicios>' % _money(compra['valor_ret_servicios']),
        '<valRetServ100>%s</valRetServ100>' % _money(compra['val_ret_serv100']),
        '<totbasesImpReemb>%s</totbasesImpReemb>' % _money(compra['tot_bases_imp_reemb']),
        '<pagoExterior>%s</pagoExterior>' % ''.join([
            '<pagoLocExt>%s</pagoLocExt>' % compra['pago_local_o_exterior'],
            '<aplicConvDobTrib>%s</aplicConvDobTrib>' % compra['aplica_convenio_doble_tributacion'],
            '<pagExtSujRetNorLeg>%s</pagExtSujRetNorLeg>' % compra['pago_exterior_sujeto_retencion_normativa'],
        ]),
    ]
    return '<detalleCompras>%s</detalleCompras>' % ''.join(parts)


def build_ats_xml(header, compras):
    """XML mínimo del ATS (<iva>) con un bloque <compras>, en el orden exacto de ivaType.
    header: dict con REQUIRED_HEADER_KEYS. compras: lista de dicts con REQUIRED_COMPRA_KEYS."""
    _validate_header(header)
    if not compras:
        raise ValueError('build_ats_xml requiere al menos una compra; no genera un anexo vacío.')
    detalle = ''.join(build_compra_element(compra) for compra in compras)
    body = [
        '<TipoIDInformante>%s</TipoIDInformante>' % header['tipo_id_informante'],
        '<IdInformante>%s</IdInformante>' % header['id_informante'],
        '<razonSocial>%s</razonSocial>' % header['razon_social'],
        '<Anio>%s</Anio>' % header['anio'],
        '<Mes>%s</Mes>' % header['mes'],
        '<codigoOperativo>%s</codigoOperativo>' % header['codigo_operativo'],
        '<compras>%s</compras>' % detalle,
    ]
    return ('<?xml version="1.0" encoding="UTF-8" standalone="no"?><iva>%s</iva>' % ''.join(body)).encode('utf-8')
