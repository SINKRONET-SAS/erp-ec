"""Generador de RIDE (representación impresa del comprobante electrónico) a partir del XML ya
autorizado por el SRI. Verificado campo por campo contra el ejemplo oficial de la Ficha Técnica
2.34 (Anexo 2, página 60: imagen del RIDE de FACTURA, inspeccionada visualmente): recuadro de
emisor a la izquierda, recuadro de comprobante/autorización a la derecha, clave de acceso bajo
el código de barras, caja de comprador, tabla de detalle con barra de encabezado, totales
alineados a la derecha. La arquitectura de dos columnas con recuadros también se contrastó
contra el renderizador real de sinkroniq-mobile (backend/src/pdf/renderers/classicRideStrategy.js
+ baseRideRenderer.js, PDFKit) -- incluida solo como referencia de diseño ya validada en
producción, no se copió código ni datos, y aquí se usa reportlab (no PDFKit).

Los nombres de elemento XML citados aquí están confirmados contra
addons/erpec_fiscal_native/xsd/factura_V2.1.0.xsd (fuente primaria); no se inventan campos
(p. ej. ICE/IRBPNR se muestran genéricos por código, no se asume su nombre oficial sin
confirmarlo). Sin logo ni QR (el QR no es un requisito confirmado en la ficha 2.34; el código
de barras Code128 sí, y es opcional según el numeral 9.20 del anexo)."""
import io

from lxml import etree
from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

AMBIENTE_LABEL = {'1': 'PRUEBAS', '2': 'PRODUCCIÓN'}
EMISION_LABEL = {'1': 'NORMAL', '2': 'CONTINGENCIA'}
# Solo el código '2' (IVA) está confirmado y en uso por engine.py; otros códigos del catálogo
# oficial (p. ej. ICE, IRBPNR) se muestran genéricos por número, sin asumir su nombre.
IMPUESTO_LABEL = {'2': 'IVA'}
PORCENTAJE_LABEL = {'0': '0%', '2': '12%', '3': '14%', '4': '15%', '5': '5%', '6': 'no objeto', '7': 'exento'}

HEADER_COLOR = colors.HexColor('#1A2840')
BORDER_COLOR = colors.HexColor('#555555')
PANEL_FILL = colors.HexColor('#F7F9FC')


def _text(root, path, default=''):
    node = root.find(path)
    return (node.text or default) if node is not None else default


def build_ride(comprobante_xml, numero_autorizacion='', fecha_autorizacion=''):
    """Genera el PDF del RIDE. Devuelve bytes. `comprobante_xml` es el XML del comprobante
    (bytes) devuelto por sri_client.consultar_autorizacion() dentro de autorizacion['comprobante']
    -- zeep ya lo entrega parseado y desenvuelto, no hace falta desempaquetar un <autorizacion>."""
    factura = etree.fromstring(comprobante_xml)
    info = factura.find('infoTributaria')
    detail = factura.find('infoFactura')

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 15 * mm
    left = margin
    right = width - margin
    content_width = right - left

    def box(x, y_top, w, h, fill=None):
        """Recuadro con esquina superior en y_top (convención propia: y decrece hacia abajo)."""
        page.setStrokeColor(BORDER_COLOR)
        page.setLineWidth(0.6)
        if fill is not None:
            page.setFillColor(fill)
            page.rect(x, y_top - h, w, h, stroke=1, fill=1)
            page.setFillColor(colors.black)
        else:
            page.rect(x, y_top - h, w, h, stroke=1, fill=0)

    def text_at(x, y_top, value, size=8, bold=False, color=colors.black, align='left', w=None):
        page.setFillColor(color)
        page.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
        if align == 'right' and w:
            page.drawRightString(x + w, y_top, value)
        elif align == 'center' and w:
            page.drawCentredString(x + w / 2, y_top, value)
        else:
            page.drawString(x, y_top, value)
        page.setFillColor(colors.black)

    # ── Recuadro emisor (izquierda) ────────────────────────────────────────
    y_top = height - margin
    left_box_h = 42 * mm
    box(left, y_top, 78 * mm, left_box_h)
    ey = y_top - 5 * mm
    text_at(left + 3 * mm, ey, _text(info, 'razonSocial'), size=11, bold=True, color=HEADER_COLOR)
    ey -= 5 * mm
    nombre_comercial = _text(info, 'nombreComercial')
    if nombre_comercial and nombre_comercial != _text(info, 'razonSocial'):
        text_at(left + 3 * mm, ey, nombre_comercial, size=8)
        ey -= 4.5 * mm
    text_at(left + 3 * mm, ey, 'RUC: ' + _text(info, 'ruc'), size=8)
    ey -= 4.5 * mm
    dir_establecimiento = _text(detail, 'dirEstablecimiento')
    direccion = dir_establecimiento or _text(info, 'dirMatriz')
    text_at(left + 3 * mm, ey, 'Dirección: ' + direccion, size=8)
    ey -= 4.5 * mm
    obligado_contabilidad = _text(detail, 'obligadoContabilidad')
    if obligado_contabilidad:
        text_at(left + 3 * mm, ey, 'Obligado a llevar contabilidad: ' + obligado_contabilidad, size=8)
        ey -= 4.5 * mm
    contribuyente_especial = _text(detail, 'contribuyenteEspecial')
    if contribuyente_especial:
        text_at(left + 3 * mm, ey, 'Contribuyente especial Nro: ' + contribuyente_especial, size=8)
        ey -= 4.5 * mm
    agente_retencion = _text(info, 'agenteRetencion')
    if agente_retencion:
        text_at(left + 3 * mm, ey, 'Agente de retención Resolución No.: ' + agente_retencion, size=8)
        ey -= 4.5 * mm
    contribuyente_rimpe = _text(info, 'contribuyenteRimpe')
    if contribuyente_rimpe:
        text_at(left + 3 * mm, ey, contribuyente_rimpe, size=8)

    # ── Recuadro comprobante + autorización (derecha) ──────────────────────
    right_box_x = left + 80 * mm
    right_box_w = right - right_box_x
    box(right_box_x, y_top, right_box_w, 12 * mm)
    text_at(right_box_x, y_top - 6 * mm, 'FACTURA', size=13, bold=True, color=HEADER_COLOR,
            align='center', w=right_box_w)
    text_at(right_box_x, y_top - 10.5 * mm, 'No. %s-%s-%s' % (
        _text(info, 'estab'), _text(info, 'ptoEmi'), _text(info, 'secuencial')),
        size=9, bold=True, align='center', w=right_box_w)

    auth_top = y_top - 12 * mm
    auth_h = 30 * mm
    box(right_box_x, auth_top, right_box_w, auth_h, fill=PANEL_FILL)
    ry = auth_top - 4 * mm
    text_at(right_box_x + 2 * mm, ry, 'NÚMERO DE AUTORIZACIÓN:', size=7, bold=True, color=BORDER_COLOR)
    ry -= 3.5 * mm
    text_at(right_box_x + 2 * mm, ry, numero_autorizacion or 'PENDIENTE', size=7)
    ry -= 4 * mm
    text_at(right_box_x + 2 * mm, ry, 'FECHA Y HORA DE AUTORIZACIÓN: ' + (fecha_autorizacion or 'PENDIENTE'),
            size=7)
    ry -= 4 * mm
    ambiente = _text(info, 'ambiente')
    tipo_emision = _text(info, 'tipoEmision')
    text_at(right_box_x + 2 * mm, ry, 'AMBIENTE: ' + AMBIENTE_LABEL.get(ambiente, ambiente or '—'),
            size=7, bold=True)
    text_at(right_box_x + right_box_w - 2 * mm, ry, 'EMISIÓN: ' + EMISION_LABEL.get(tipo_emision, tipo_emision or '—'),
            size=7, bold=True, align='right', w=0)
    ry -= 4 * mm
    text_at(right_box_x + 2 * mm, ry, 'CLAVE DE ACCESO:', size=7, bold=True)
    ry -= 8 * mm
    clave_acceso = _text(info, 'claveAcceso')
    if clave_acceso:
        # Code128 es un Flowable, no una Drawing: se dibuja directo con drawOn(), no con
        # renderPDF.draw() (ese requiere un objeto Drawing con renderScale). El ejemplo oficial
        # imprime los 49 dígitos debajo del código de barras, no antes.
        barcode = code128.Code128(clave_acceso, barHeight=8 * mm, barWidth=0.3)
        barcode.drawOn(page, right_box_x + 2 * mm, ry)
        ry -= 4 * mm
        text_at(right_box_x + 2 * mm, ry, clave_acceso, size=6)

    y = auth_top - auth_h - 4 * mm

    # ── Caja comprador ──────────────────────────────────────────────────────
    placa = _text(detail, 'placa')
    guia_remision = _text(detail, 'guiaRemision')
    client_h = (16 if not (placa or guia_remision) else 20) * mm
    box(left, y, content_width, client_h, fill=PANEL_FILL)
    cy = y - 4.5 * mm
    text_at(left + 3 * mm, cy, 'Comprador: ' + _text(detail, 'razonSocialComprador'), size=9, bold=True)
    cy -= 4.5 * mm
    text_at(left + 3 * mm, cy, 'Identificación: ' + _text(detail, 'identificacionComprador'), size=8)
    text_at(left + content_width / 2, cy, 'Fecha de emisión: ' + _text(detail, 'fechaEmision'), size=8)
    cy -= 4.5 * mm
    text_at(left + 3 * mm, cy, 'Dirección: ' + _text(detail, 'direccionComprador'), size=8)
    if placa or guia_remision:
        cy -= 4.5 * mm
        if placa:
            text_at(left + 3 * mm, cy, 'Placa / Matrícula: ' + placa, size=8)
        if guia_remision:
            text_at(left + content_width / 2, cy, 'Guía de remisión: ' + guia_remision, size=8)
    y -= client_h + 3 * mm

    # ── Tabla de detalle ─────────────────────────────────────────────────────
    columns = [
        ('Cod. Princ.', 0, 22 * mm, 'left'),
        ('Cant.', 22 * mm, 12 * mm, 'right'),
        ('Descripción', 34 * mm, 78 * mm, 'left'),
        ('P.Unit', 112 * mm, 16 * mm, 'right'),
        ('Desc.', 128 * mm, 14 * mm, 'right'),
        ('Total', 142 * mm, content_width - 142 * mm, 'right'),
    ]
    header_h = 6 * mm
    page.setFillColor(HEADER_COLOR)
    page.rect(left, y - header_h, content_width, header_h, stroke=0, fill=1)
    for label, dx, w, align in columns:
        text_at(left + dx + 1 * mm, y - 4.3 * mm, label, size=7.5, bold=True, color=colors.white,
                align=align if align == 'right' else 'left', w=(w - 2 * mm) if align == 'right' else None)
    y -= header_h

    row_h = 5.5 * mm
    for item in factura.findall('detalles/detalle'):
        if y < margin + 45 * mm:
            page.showPage()
            y = height - margin
            page.setFillColor(HEADER_COLOR)
            page.rect(left, y - header_h, content_width, header_h, stroke=0, fill=1)
            for label, dx, w, align in columns:
                text_at(left + dx + 1 * mm, y - 4.3 * mm, label, size=7.5, bold=True, color=colors.white,
                        align=align if align == 'right' else 'left', w=(w - 2 * mm) if align == 'right' else None)
            y -= header_h
        codigo = _text(item, 'codigoPrincipal')
        codigo_aux = _text(item, 'codigoAuxiliar')
        if codigo_aux:
            codigo = codigo + '/' + codigo_aux
        values = [
            codigo[:16],
            _text(item, 'cantidad'),
            _text(item, 'descripcion')[:52],
            _text(item, 'precioUnitario'),
            _text(item, 'descuento'),
            _text(item, 'precioTotalSinImpuesto'),
        ]
        ty = y - 3.8 * mm
        for (label, dx, w, align), value in zip(columns, values):
            text_at(left + dx + 1 * mm, ty, value, size=7.5,
                    align=align if align == 'right' else 'left', w=(w - 2 * mm) if align == 'right' else None)
        page.setStrokeColor(colors.HexColor('#E5E7EB'))
        page.setLineWidth(0.3)
        page.line(left, y - row_h, right, y - row_h)
        y -= row_h

    y -= 3 * mm

    # ── Totales (columna derecha) + forma de pago (izquierda) ─────────────
    totals_x = left + content_width - 60 * mm
    totals_w = 60 * mm
    totals_y = y

    subtotal_rows = []
    for impuesto in detail.findall('totalConImpuestos/totalImpuesto'):
        codigo = _text(impuesto, 'codigo')
        porcentaje = _text(impuesto, 'codigoPorcentaje')
        etiqueta = IMPUESTO_LABEL.get(codigo, 'Impuesto (código %s)' % codigo) if codigo else 'IVA'
        tarifa = PORCENTAJE_LABEL.get(porcentaje, porcentaje)
        subtotal_rows.append(('SUBTOTAL %s:' % tarifa, _text(impuesto, 'baseImponible')))
        subtotal_rows.append(('%s %s:' % (etiqueta, tarifa), _text(impuesto, 'valor')))
        valor_devolucion_iva = _text(impuesto, 'valorDevolucionIva')
        if valor_devolucion_iva:
            subtotal_rows.append(('Devolución IVA:', valor_devolucion_iva))
    subtotal_rows.insert(0, ('SUBTOTAL SIN IMPUESTOS:', _text(detail, 'totalSinImpuestos')))
    total_descuento = _text(detail, 'totalDescuento')
    if total_descuento and total_descuento != '0.00':
        subtotal_rows.append(('DESCUENTO:', total_descuento))
    propina = _text(detail, 'propina')
    if propina and propina != '0.00':
        subtotal_rows.append(('PROPINA:', propina))

    for label, value in subtotal_rows:
        text_at(totals_x, totals_y, label, size=8)
        text_at(totals_x + totals_w, totals_y, value, size=8, align='right', w=0)
        totals_y -= 4.5 * mm

    page.setStrokeColor(BORDER_COLOR)
    page.setLineWidth(0.6)
    page.line(totals_x, totals_y - 1 * mm, totals_x + totals_w, totals_y - 1 * mm)
    totals_y -= 5 * mm
    text_at(totals_x, totals_y, 'TOTAL:', size=11, bold=True)
    text_at(totals_x + totals_w, totals_y, _text(detail, 'importeTotal'), size=11, bold=True, align='right', w=0)

    pay_y = y
    for pago in detail.findall('pagos/pago'):
        text_at(left, pay_y, 'Forma de pago %s: %s' % (_text(pago, 'formaPago'), _text(pago, 'total')), size=8)
        pay_y -= 4.5 * mm

    info_adicional = factura.findall('infoAdicional/campoAdicional')
    if info_adicional:
        pay_y -= 2 * mm
        text_at(left, pay_y, 'Información adicional', size=8, bold=True)
        pay_y -= 4 * mm
        for campo in info_adicional:
            nombre = campo.get('nombre', '')
            text_at(left, pay_y, '%s: %s' % (nombre, campo.text or ''), size=8)
            pay_y -= 4 * mm

    page.showPage()
    page.save()
    return buffer.getvalue()
