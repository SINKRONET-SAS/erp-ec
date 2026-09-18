"""Pruebas de sri_client.py con el cliente zeep simulado vía client_factory; no contactan al
SRI real. sri_client.AMBIENTES['1']['enabled'] apunta a celcer.sri.gob.ec (confirmado
alcanzable por fuera de esta batería, ver docs/PLAN_HAIKY_FACTURACION_NATIVA.md)."""
from types import SimpleNamespace

from odoo.tests.common import BaseCase

from .. import sri_client


class FakeService:
    def __init__(self, response=None, fault=None, error=None):
        self._response, self._fault, self._error = response, fault, error

    def validarComprobante(self, xml):
        return self._respond()

    def autorizacionComprobante(self, claveAccesoComprobante):
        return self._respond()

    def _respond(self):
        if self._error:
            raise self._error
        if self._fault:
            import zeep.exceptions
            raise zeep.exceptions.Fault(self._fault)
        return self._response


class FakeClient:
    def __init__(self, service):
        self.service = service


def factory_for(response=None, fault=None, error=None):
    return lambda url, timeout=20: FakeClient(FakeService(response, fault, error))


class TestSriClient(BaseCase):
    def test_recepcion_recibida(self):
        response = SimpleNamespace(estado='RECIBIDA', mensajes=None)
        estado, mensajes = sri_client.enviar_recepcion(b'<factura/>', client_factory=factory_for(response))
        self.assertEqual(estado, 'RECIBIDA')
        self.assertEqual(mensajes, [])

    def test_recepcion_devuelta_with_messages(self):
        mensaje = SimpleNamespace(identificador='35', mensaje='CLAVE_ACCESO_REGISTRADA', informacionAdicional='', tipo='ERROR')
        response = SimpleNamespace(estado='DEVUELTA', mensajes=SimpleNamespace(mensaje=[mensaje]))
        estado, mensajes = sri_client.enviar_recepcion(b'<factura/>', client_factory=factory_for(response))
        self.assertEqual(estado, 'DEVUELTA')
        self.assertEqual(mensajes[0]['identificador'], '35')

    def test_recepcion_connection_error_is_retryable(self):
        with self.assertRaises(sri_client.SriError) as ctx:
            sri_client.enviar_recepcion(b'<factura/>', client_factory=factory_for(error=TimeoutError('timeout')))
        self.assertTrue(ctx.exception.retry)

    def test_autorizacion_pendiente_sin_autorizaciones(self):
        response = SimpleNamespace(autorizaciones=None)
        estado, autorizacion, mensajes = sri_client.consultar_autorizacion('0' * 49, client_factory=factory_for(response))
        self.assertEqual(estado, 'PENDIENTE')
        self.assertIsNone(autorizacion)

    def test_autorizacion_autorizado_returns_comprobante(self):
        autorizacion_node = SimpleNamespace(estado='AUTORIZADO', comprobante='<factura/>',
                                            numeroAutorizacion='123', fechaAutorizacion='2026-09-16', mensajes=None)
        response = SimpleNamespace(autorizaciones=SimpleNamespace(autorizacion=[autorizacion_node]))
        estado, autorizacion, mensajes = sri_client.consultar_autorizacion('0' * 49, client_factory=factory_for(response))
        self.assertEqual(estado, 'AUTORIZADO')
        self.assertEqual(autorizacion['comprobante'], b'<factura/>')
        self.assertEqual(autorizacion['numero'], '123')

    def test_autorizacion_no_autorizado(self):
        autorizacion_node = SimpleNamespace(estado='NO AUTORIZADO', comprobante=None, mensajes=None)
        response = SimpleNamespace(autorizaciones=SimpleNamespace(autorizacion=[autorizacion_node]))
        estado, autorizacion, mensajes = sri_client.consultar_autorizacion('0' * 49, client_factory=factory_for(response))
        self.assertEqual(estado, 'NO AUTORIZADO')
        self.assertIsNone(autorizacion)

    def test_ambiente_produccion_uses_production_endpoints(self):
        urls = []

        def factory(url, timeout=20):
            urls.append(url)
            return FakeClient(FakeService(SimpleNamespace(estado='RECIBIDA', comprobantes=None)))
        sri_client.enviar_recepcion(b'<factura/>', ambiente='2', client_factory=factory)
        sri_client.enviar_recepcion(b'<factura/>', ambiente='1', client_factory=factory)
        self.assertIn('//cel.sri.gob.ec/', urls[0])
        self.assertIn('//celcer.sri.gob.ec/', urls[1])

    def test_unknown_ambiente_is_rejected(self):
        with self.assertRaises(sri_client.SriError):
            sri_client.enviar_recepcion(b'<factura/>', ambiente='9', client_factory=factory_for())
