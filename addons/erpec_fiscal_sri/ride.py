"""Generador de RIDE (representación impresa del comprobante electrónico) a partir del XML ya
autorizado por el SRI. Contenido completo exigido por la normativa (clave de acceso, emisor,
comprador, detalle, impuestos, totales, forma de pago, número y fecha de autorización); no
pretende igualar visualmente el RIDE de ningún proveedor específico — no hay una plantilla
oficial de referencia disponible para clonar."""
import io

from lxml import etree
from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

NS_STRIP = None  # Los XML del SRI no llevan namespace en los elementos de factura.


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
    y = height - margin

    def line(text, size=9, bold=False, dy=5.5 * mm):
        nonlocal y
        page.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
        page.drawString(margin, y, text)
        y -= dy

    line('RUC: ' + _text(info, 'ruc'), bold=True)
    line(_text(info, 'razonSocial'), bold=True)
    line('Dirección matriz: ' + _text(info, 'dirMatriz'))
    y -= 3 * mm
    line('FACTURA', size=12, bold=True)
    line('No. %s-%s-%s' % (_text(info, 'estab'), _text(info, 'ptoEmi'), _text(info, 'secuencial')))
    line('Clave de acceso: ' + _text(info, 'claveAcceso'), size=7)
    if _text(info, 'claveAcceso'):
        # Code128 es un Flowable, no una Drawing: se dibuja directo con drawOn(), no con
        # renderPDF.draw() (ese requiere un objeto Drawing con renderScale).
        barcode = code128.Code128(_text(info, 'claveAcceso'), barHeight=10 * mm, barWidth=0.35)
        barcode.drawOn(page, margin, y - 12 * mm)
        y -= 15 * mm
    line('Autorización SRI: ' + (numero_autorizacion or 'PENDIENTE'), size=8)
    line('Fecha de autorización: ' + (fecha_autorizacion or ''), size=8)
    y -= 3 * mm

    page.setStrokeColor(colors.grey)
    page.line(margin, y, width - margin, y)
    y -= 6 * mm
    line('Cliente: ' + _text(detail, 'razonSocialComprador'), bold=True)
    line('Identificación: ' + _text(detail, 'identificacionComprador'))
    line('Dirección: ' + _text(detail, 'direccionComprador'))
    line('Fecha de emisión: ' + _text(detail, 'fechaEmision'))
    y -= 3 * mm

    page.line(margin, y, width - margin, y)
    y -= 6 * mm
    line('Cant.   Descripción                                  P.Unit   Desc.   Total', bold=True, size=8)
    for item in factura.findall('detalles/detalle'):
        cantidad = _text(item, 'cantidad')
        descripcion = _text(item, 'descripcion')[:40]
        precio = _text(item, 'precioUnitario')
        descuento = _text(item, 'descuento')
        total = _text(item, 'precioTotalSinImpuesto')
        line('%-7s %-42s %-8s %-7s %-8s' % (cantidad, descripcion, precio, descuento, total), size=8)
        if y < margin + 40 * mm:
            page.showPage()
            y = height - margin

    y -= 3 * mm
    page.line(margin, y, width - margin, y)
    y -= 6 * mm
    line('Subtotal sin impuestos: ' + _text(detail, 'totalSinImpuestos'))
    line('Descuento: ' + _text(detail, 'totalDescuento'))
    for impuesto in detail.findall('totalConImpuestos/totalImpuesto'):
        line('IVA %s%%: base %s, valor %s' % (
            _text(impuesto, 'codigoPorcentaje'), _text(impuesto, 'baseImponible'), _text(impuesto, 'valor')), size=8)
    line('Propina: ' + _text(detail, 'propina'))
    line('TOTAL: ' + _text(detail, 'importeTotal'), bold=True, size=11)
    for pago in detail.findall('pagos/pago'):
        line('Forma de pago %s: %s' % (_text(pago, 'formaPago'), _text(pago, 'total')), size=8)

    page.showPage()
    page.save()
    return buffer.getvalue()
