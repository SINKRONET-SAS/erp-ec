"""Pruebas de ride.py: genera un PDF real a partir de un XML de comprobante sintético."""
import io

from PyPDF2 import PdfReader

from odoo.tests.common import BaseCase

from .. import ride


def _extract_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return '\n'.join(page.extract_text() for page in reader.pages)

FACTURA_XML = '''<factura id="comprobante" version="2.1.0">
<infoTributaria><ambiente>1</ambiente><tipoEmision>1</tipoEmision><ruc>1793235327001</ruc><razonSocial>SINKRONET S.A.S.</razonSocial>
<dirMatriz>Los Cardenales SN</dirMatriz><estab>001</estab><ptoEmi>001</ptoEmi>
<secuencial>000000444</secuencial><claveAcceso>1609202601179323532700111001001000000444123456781</claveAcceso></infoTributaria>
<infoFactura><fechaEmision>16/09/2026</fechaEmision><razonSocialComprador>Cliente de ensayo</razonSocialComprador>
<identificacionComprador>1793235327001</identificacionComprador><direccionComprador>Dirección de ensayo</direccionComprador>
<totalSinImpuestos>100.00</totalSinImpuestos><totalDescuento>0.00</totalDescuento>
<totalConImpuestos><totalImpuesto><codigo>2</codigo><codigoPorcentaje>4</codigoPorcentaje><baseImponible>100.00</baseImponible><valor>15.00</valor></totalImpuesto></totalConImpuestos>
<propina>0.00</propina><importeTotal>115.00</importeTotal>
<pagos><pago><formaPago>20</formaPago><total>115.00</total></pago></pagos></infoFactura>
<detalles><detalle><codigoPrincipal>SERV1</codigoPrincipal><descripcion>Servicio de ensayo</descripcion>
<cantidad>1.00</cantidad><precioUnitario>100.00</precioUnitario><descuento>0.00</descuento>
<precioTotalSinImpuesto>100.00</precioTotalSinImpuesto></detalle></detalles></factura>'''


class TestRide(BaseCase):
    def test_build_ride_produces_pdf_bytes(self):
        pdf = ride.build_ride(FACTURA_XML.encode('utf-8'), numero_autorizacion='1234567890', fecha_autorizacion='2026-09-16T10:00:00-05:00')
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 500)

    def test_build_ride_handles_many_lines_with_page_break(self):
        many_details = ''.join(
            '<detalle><codigoPrincipal>S%d</codigoPrincipal><descripcion>Linea %d</descripcion>'
            '<cantidad>1.00</cantidad><precioUnitario>1.00</precioUnitario><descuento>0.00</descuento>'
            '<precioTotalSinImpuesto>1.00</precioTotalSinImpuesto></detalle>' % (i, i) for i in range(60))
        xml = FACTURA_XML.replace(
            '<detalles><detalle><codigoPrincipal>SERV1</codigoPrincipal><descripcion>Servicio de ensayo</descripcion>'
            '<cantidad>1.00</cantidad><precioUnitario>100.00</precioUnitario><descuento>0.00</descuento>'
            '<precioTotalSinImpuesto>100.00</precioTotalSinImpuesto></detalle></detalles>',
            '<detalles>' + many_details + '</detalles>')
        pdf = ride.build_ride(xml.encode('utf-8'))
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_build_ride_without_access_key_skips_barcode(self):
        xml = FACTURA_XML.replace('<claveAcceso>1609202601179323532700111001001000000444123456781</claveAcceso>', '')
        pdf = ride.build_ride(xml.encode('utf-8'))
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_build_ride_includes_ambiente_emision_and_official_labels(self):
        pdf = ride.build_ride(FACTURA_XML.encode('utf-8'), numero_autorizacion='1234567890',
                               fecha_autorizacion='2026-09-16T10:00:00-05:00')
        text = _extract_text(pdf)
        self.assertIn('AMBIENTE: PRUEBAS', text)
        self.assertIn('EMISIÓN: NORMAL', text)
        self.assertIn('NÚMERO DE AUTORIZACIÓN', text)
        self.assertIn('FECHA Y HORA DE AUTORIZACIÓN', text)
        self.assertIn('CLAVE DE ACCESO', text)
        self.assertIn('1609202601179323532700111001001000000444123456781', text)
        self.assertIn('SUBTOTAL 15%', text)
        self.assertIn('IVA 15%', text)

    def test_build_ride_shows_codigo_auxiliar_placa_and_guia_remision(self):
        xml = FACTURA_XML.replace(
            '<codigoPrincipal>SERV1</codigoPrincipal>',
            '<codigoPrincipal>SERV1</codigoPrincipal><codigoAuxiliar>AUX9</codigoAuxiliar>',
        ).replace(
            '<importeTotal>115.00</importeTotal>',
            '<importeTotal>115.00</importeTotal><placa>ABC-1234</placa>',
        ).replace(
            '<razonSocialComprador>Cliente de ensayo</razonSocialComprador>',
            '<guiaRemision>001-001-000000123</guiaRemision>'
            '<razonSocialComprador>Cliente de ensayo</razonSocialComprador>',
        )
        pdf = ride.build_ride(xml.encode('utf-8'))
        text = _extract_text(pdf)
        self.assertIn('SERV1/AUX9', text)
        self.assertIn('Placa / Matrícula: ABC-1234', text)
        self.assertIn('Guía de remisión: 001-001-000000123', text)

    def test_build_ride_unknown_ambiente_and_emision_show_raw_code(self):
        xml = FACTURA_XML.replace('<ambiente>1</ambiente>', '<ambiente>9</ambiente>') \
            .replace('<tipoEmision>1</tipoEmision>', '<tipoEmision>9</tipoEmision>')
        pdf = ride.build_ride(xml.encode('utf-8'))
        text = _extract_text(pdf)
        self.assertIn('AMBIENTE: 9', text)
        self.assertIn('EMISIÓN: 9', text)
