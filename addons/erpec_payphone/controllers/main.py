"""Retorno público con verificación de servidor; nunca recibe credenciales ni tarjetas."""
import re
from markupsafe import escape
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError


def page(title, message, status=200, link=None, link_label="Continuar en PayPhone"):
    action = ('<p><a href="%s" rel="noopener">%s</a></p>' % (escape(link), escape(link_label))) if link else ''
    body = ('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>SK ERP · PayPhone</title><style>body{font:18px system-ui;background:#f3f6fa;color:#182738;padding:8vh 6vw}'
            'main{max-width:650px;margin:auto;background:white;padding:36px;border-radius:16px}a{color:#065bc4}</style>'
            '<main><p>SK ERP</p><h1>%s</h1><p>%s</p>%s</main></html>') % (escape(title), escape(message), action)
    return request.make_response(body, headers=[('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'), ('Referrer-Policy', 'origin'), ('X-Content-Type-Options', 'nosniff')], status=status)


class PayphoneController(http.Controller):
    @http.route('/payment/payphone/checkout/<string:reference>', type='http', auth='public', methods=['GET'])
    def checkout(self, reference, **kwargs):
        # Público a propósito: la referencia es un UUID no adivinable y la página solo
        # muestra el enlace de checkout ya generado por PayPhone, nunca datos privados.
        payment = request.env['erpec.payphone.payment'].sudo().search([('reference', '=', reference)], limit=1)
        if payment and payment.state=='queued':
            return page('Preparando el pago', 'Tu solicitud está guardada. Actualiza el estado en unos instantes; no envíes otra solicitud.',202,link='/payment/payphone/checkout/'+payment.reference,link_label='Actualizar estado')
        if not payment or payment.state != 'prepared':
            return page('Enlace no disponible', 'Consulta el estado del pago en SK ERP.', 404)
        return page('Pago preparado', 'Confirma los datos antes de continuar. El pago se abrirá en la página de PayPhone.', link=payment.checkout_url)

    @http.route('/payment/payphone/return', type='http', auth='public', methods=['GET'], sitemap=False)
    def payment_return(self, **params):
        reference = params.get('clientTransactionId', '')
        remote_id = params.get('id', '')
        if not re.fullmatch(r'[0-9a-f]{32}', reference) or not re.fullmatch(r'[1-9][0-9]{0,17}', remote_id):
            return page('Retorno PayPhone disponible', 'Faltan parámetros válidos de una transacción. No se ha registrado ningún pago.', 400)
        payment = request.env['erpec.payphone.payment'].sudo().search([('reference', '=', reference)], limit=1)
        if not payment:
            return page('Pago no identificado', 'Revisa la referencia del pago en SK ERP.', 404)
        payment = payment.with_user(request.env.ref('base.user_admin')).sudo().with_company(payment.company_id)
        try:
            payment._receive_return(remote_id)
        except ValidationError:
            return page('Revisión necesaria', 'No se pudo confirmar esta transacción. Revisa el pago en SK ERP.', 409)
        messages = {
            'approved': ('Pago confirmado', 'PayPhone confirmó el importe y la transacción. La conciliación del contrato se procesará en SK ERP.'),
            'canceled': ('Pago cancelado', 'PayPhone informó la cancelación. No se ha activado ningún servicio.'),
        }
        title, message = messages.get(payment.state, ('Confirmación pendiente', 'La respuesta aún no está verificada. SK ERP reintentará la consulta; no repitas el pago.'))
        return page(title, message)
