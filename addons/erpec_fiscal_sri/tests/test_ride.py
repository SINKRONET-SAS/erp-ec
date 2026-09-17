"""Pruebas de ride.py: genera un PDF real a partir de un XML de comprobante sintético."""
from odoo.tests.common import BaseCase

from .. import ride

FACTURA_XML = '''<factura id="comprobante" version="2.1.0">
<infoTributaria><ruc>1793235327001</ruc><razonSocial>SINKRONET S.A.S.</razonSocial>
<dirMatriz>Los Cardenales SN</dirMatriz><estab>001</estab><ptoEmi>001</ptoEmi>
<secuencial>000000444</secuencial><claveAcceso>1609202601179323532700111001001000000444123456781</claveAcceso></infoTributaria>
<infoFactura><fechaEmision>16/09/2026</fechaEmision><razonSocialComprador>Cliente de ensayo</razonSocialComprador>
<identificacionComprador>1793235327001</identificacionComprador><direccionComprador>Dirección de ensayo</direccionComprador>
<totalSinImpuestos>100.00</totalSinImpuestos><totalDescuento>0.00</totalDescuento>
<totalConImpuestos><totalImpuesto><codigoPorcentaje>4</codigoPorcentaje><baseImponible>100.00</baseImponible><valor>15.00</valor></totalImpuesto></totalConImpuestos>
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
