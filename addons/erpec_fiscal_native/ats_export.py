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
# Opcionales (minOccurs=0 en detalleComprasType): bloque air (retención de renta, uno por concepto
# del catálogo de renta) y la referencia al propio comprobante de retención emitido (estabRetencion1/
# ptoEmiRetencion1/secRetencion1/autRetencion1/fechaEmiRet1). Solo se agregan si el llamador los provee.
REQUIRED_AIR_KEYS = ('cod_ret_air', 'base_imp_air', 'porcentaje_air', 'val_ret_air')
RETENTION_REF_KEYS = ('estab_retencion1', 'pto_emi_retencion1', 'sec_retencion1', 'aut_retencion1', 'fecha_emi_ret1')
# ventasType.detalleVentas NO es una fila por documento (a diferencia de compras): es un resumen
# agrupado por tipo de identificación del cliente + tipo de comprobante + tipo de emisión, con un
# conteo de comprobantes (numeroComprobantes) y los importes sumados del grupo. Así lo exige at.xsd.
REQUIRED_VENTA_KEYS = (
    'tp_id_cliente', 'id_cliente', 'tipo_comprobante', 'tipo_emision', 'numero_comprobantes',
    'base_no_gra_iva', 'base_imponible', 'base_imp_grav', 'monto_iva', 'valor_ret_iva', 'valor_ret_renta',
)
# anuladosType.detalleAnulados tampoco es una fila por documento: es un rango de secuenciales
# (secuencialInicio/secuencialFin) bajo una misma autorización, para un mismo tipo de comprobante.
REQUIRED_ANULADO_KEYS = ('tipo_comprobante', 'establecimiento', 'punto_emision', 'secuencial_inicio', 'secuencial_fin', 'autorizacion')


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


def _validate_air(entry):
    missing = [key for key in REQUIRED_AIR_KEYS if entry.get(key) in (None, '')]
    if missing:
        raise ValueError('Faltan campos obligatorios de un detalle air (retención de renta): %s' % ', '.join(missing))


def _build_air_block(air_entries):
    parts = []
    for entry in air_entries:
        _validate_air(entry)
        parts.append('<detalleAir>%s</detalleAir>' % ''.join([
            '<codRetAir>%s</codRetAir>' % entry['cod_ret_air'],
            '<baseImpAir>%s</baseImpAir>' % _money(entry['base_imp_air']),
            '<porcentajeAir>%s</porcentajeAir>' % _money(entry['porcentaje_air']),
            '<valRetAir>%s</valRetAir>' % _money(entry['val_ret_air']),
        ]))
    return '<air>%s</air>' % ''.join(parts)


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
    if compra.get('forma_pago'):
        parts.append('<formasDePago>%s</formasDePago>' % ''.join(
            '<formaPago>%s</formaPago>' % code for code in compra['forma_pago']))
    if compra.get('air'):
        parts.append(_build_air_block(compra['air']))
    if all(compra.get(key) for key in RETENTION_REF_KEYS):
        parts.extend([
            '<estabRetencion1>%s</estabRetencion1>' % compra['estab_retencion1'],
            '<ptoEmiRetencion1>%s</ptoEmiRetencion1>' % compra['pto_emi_retencion1'],
            '<secRetencion1>%s</secRetencion1>' % compra['sec_retencion1'],
            '<autRetencion1>%s</autRetencion1>' % compra['aut_retencion1'],
            '<fechaEmiRet1>%s</fechaEmiRet1>' % compra['fecha_emi_ret1'],
        ])
    return '<detalleCompras>%s</detalleCompras>' % ''.join(parts)


def _validate_venta(venta):
    missing = [key for key in REQUIRED_VENTA_KEYS if venta.get(key) in (None, '')]
    if missing:
        raise ValueError('Faltan campos obligatorios de un grupo de venta ATS: %s' % ', '.join(missing))
    if venta['tipo_comprobante'] not in ats_catalog.VOUCHER_TYPES:
        raise ValueError('tipoComprobante %r no está en el catálogo oficial del ATS (ats_catalog.VOUCHER_TYPES).' % venta['tipo_comprobante'])
    if venta['tipo_emision'] not in ('E', 'F'):
        raise ValueError('tipoEmision debe ser "E" (electrónico) o "F" (físico).')


def build_venta_element(venta):
    """Un <detalleVentas>: resumen agrupado (no una fila por documento), en el orden exacto que
    exige detalleVentasType de at.xsd."""
    _validate_venta(venta)
    parts = [
        '<tpIdCliente>%s</tpIdCliente>' % venta['tp_id_cliente'],
        '<idCliente>%s</idCliente>' % venta['id_cliente'],
        '<tipoComprobante>%s</tipoComprobante>' % venta['tipo_comprobante'].zfill(2),
        '<tipoEmision>%s</tipoEmision>' % venta['tipo_emision'],
        '<numeroComprobantes>%s</numeroComprobantes>' % int(venta['numero_comprobantes']),
        '<baseNoGraIva>%s</baseNoGraIva>' % _money(venta['base_no_gra_iva']),
        '<baseImponible>%s</baseImponible>' % _money(venta['base_imponible']),
        '<baseImpGrav>%s</baseImpGrav>' % _money(venta['base_imp_grav']),
        '<montoIva>%s</montoIva>' % _money(venta['monto_iva']),
        '<valorRetIva>%s</valorRetIva>' % _money(venta['valor_ret_iva']),
        '<valorRetRenta>%s</valorRetRenta>' % _money(venta['valor_ret_renta']),
    ]
    return '<detalleVentas>%s</detalleVentas>' % ''.join(parts)


def _validate_anulado(anulado):
    missing = [key for key in REQUIRED_ANULADO_KEYS if anulado.get(key) in (None, '')]
    if missing:
        raise ValueError('Faltan campos obligatorios de un rango anulado ATS: %s' % ', '.join(missing))
    if anulado['tipo_comprobante'] not in ats_catalog.VOUCHER_TYPES:
        raise ValueError('tipoComprobante %r no está en el catálogo oficial del ATS (ats_catalog.VOUCHER_TYPES).' % anulado['tipo_comprobante'])


def build_anulado_element(anulado):
    """Un <detalleAnulados>: rango de secuenciales bajo una misma autorización, en el orden exacto
    que exige detalleAnuladosType de at.xsd."""
    _validate_anulado(anulado)
    parts = [
        '<tipoComprobante>%s</tipoComprobante>' % anulado['tipo_comprobante'].zfill(2),
        '<establecimiento>%s</establecimiento>' % anulado['establecimiento'],
        '<puntoEmision>%s</puntoEmision>' % anulado['punto_emision'],
        '<secuencialInicio>%s</secuencialInicio>' % anulado['secuencial_inicio'],
        '<secuencialFin>%s</secuencialFin>' % anulado['secuencial_fin'],
        '<autorizacion>%s</autorizacion>' % anulado['autorizacion'],
    ]
    return '<detalleAnulados>%s</detalleAnulados>' % ''.join(parts)


def build_ats_xml(header, compras=(), ventas=(), anulados=()):
    """XML del ATS (<iva>), en el orden exacto de ivaType: compras, ventas, anulados (cada sección
    es opcional según el esquema, pero build_ats_xml exige al menos una de las tres -- no genera
    un anexo vacío). header: dict con REQUIRED_HEADER_KEYS. compras: lista de dicts con
    REQUIRED_COMPRA_KEYS. ventas: lista de dicts con REQUIRED_VENTA_KEYS (ya agrupados por
    tpIdCliente+tipoComprobante+tipoEmision; agrupar es responsabilidad de quien llama, no de esta
    función). anulados: lista de dicts con REQUIRED_ANULADO_KEYS."""
    _validate_header(header)
    if not compras and not ventas and not anulados:
        raise ValueError('build_ats_xml requiere al menos una compra, venta o anulado; no genera un anexo vacío.')
    body = [
        '<TipoIDInformante>%s</TipoIDInformante>' % header['tipo_id_informante'],
        '<IdInformante>%s</IdInformante>' % header['id_informante'],
        '<razonSocial>%s</razonSocial>' % header['razon_social'],
        '<Anio>%s</Anio>' % header['anio'],
        '<Mes>%s</Mes>' % header['mes'],
        '<codigoOperativo>%s</codigoOperativo>' % header['codigo_operativo'],
    ]
    if compras:
        body.append('<compras>%s</compras>' % ''.join(build_compra_element(compra) for compra in compras))
    if ventas:
        body.append('<ventas>%s</ventas>' % ''.join(build_venta_element(venta) for venta in ventas))
    if anulados:
        body.append('<anulados>%s</anulados>' % ''.join(build_anulado_element(anulado) for anulado in anulados))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="no"?><iva>%s</iva>' % ''.join(body)).encode('utf-8')
