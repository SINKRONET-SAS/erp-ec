"""Landing pública de autoservicio. Quien visita nunca obtiene sesión ni permisos Odoo:
toda escritura ocurre aquí bajo el usuario administrador (sudo), igual que ya hace
`erpec_payphone`'s `/payment/payphone/return`."""
import re

from markupsafe import escape
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

RUC_RE = re.compile(r'\d{13}')
EMAIL_RE = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
REQUIRED_TEXT_FIELDS = ('company_name', 'company_regime', 'street', 'contact_name')


def page(title, body_html, status=200):
    body = ('<!doctype html><html lang="es"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>SK ERP · Autoservicio</title>'
            '<style>body{font:18px system-ui;background:#f3f6fa;color:#182738;padding:8vh 6vw}'
            'main{max-width:650px;margin:auto;background:white;padding:36px;border-radius:16px}'
            'a{color:#065bc4}label{display:block;margin-top:14px;font-size:15px}'
            'input,select{width:100%%;padding:8px;font-size:16px;box-sizing:border-box}'
            'button{margin-top:22px;padding:10px 24px;font-size:16px}</style>'
            '<main><h1>%s</h1>%s</main></html>') % (escape(title), body_html)
    return request.make_response(body, headers=[('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'), ('Referrer-Policy', 'origin'), ('X-Content-Type-Options', 'nosniff')], status=status)


class SelfserviceController(http.Controller):
    @http.route('/autoservicio', type='http', auth='public', methods=['GET'], sitemap=False)
    def landing(self, **kwargs):
        plans = request.env['erpec.plan'].sudo().search([('published', '=', True)])
        if not plans:
            return page('Autoservicio no disponible', '<p>No hay planes publicados en este momento.</p>')
        options = ''.join(
            '<option value="%d">%s — USD %.2f/mes</option>' % (plan.id, escape(plan.name), plan.price)
            for plan in plans)
        token = request.csrf_token()
        form = (
            '<form method="post" action="/autoservicio/solicitar">'
            '<input type="hidden" name="csrf_token" value="%s">'
            '<label>Razón social<input name="company_name" required maxlength="200"></label>'
            '<label>RUC<input name="company_vat" required pattern="\\d{13}" maxlength="13"></label>'
            '<label>Régimen tributario<select name="company_regime" required>'
            '<option value="general">General</option>'
            '<option value="rimpe_negocio_popular">RIMPE Negocio Popular</option>'
            '<option value="rimpe_emprendedor">RIMPE Emprendedor</option></select></label>'
            '<label>Dirección<input name="street" required maxlength="200"></label>'
            '<label>Nombre de contacto<input name="contact_name" required maxlength="200"></label>'
            '<label>Correo de contacto<input type="email" name="contact_email" required maxlength="200"></label>'
            '<label>Teléfono de contacto<input name="contact_phone" maxlength="30"></label>'
            '<label>Plan<select name="plan_id" required>%s</select></label>'
            '<button type="submit">Continuar al pago</button></form>'
        ) % (escape(token), options)
        return page('Contratar ERP EC', form)

    @http.route('/autoservicio/solicitar', type='http', auth='public', methods=['POST'], sitemap=False)
    def signup(self, **post):
        values = {key: (post.get(key) or '').strip() for key in
                  ('company_name', 'company_vat', 'company_regime', 'street',
                   'contact_name', 'contact_email', 'contact_phone')}
        try:
            plan_id = int(post.get('plan_id', ''))
        except (TypeError, ValueError):
            return page('Datos incompletos', '<p>Selecciona un plan válido.</p>', 400)
        if not RUC_RE.fullmatch(values['company_vat']):
            return page('RUC inválido', '<p>El RUC debe tener 13 dígitos numéricos.</p>', 400)
        if not EMAIL_RE.fullmatch(values['contact_email']):
            return page('Correo inválido', '<p>Indica un correo de contacto válido.</p>', 400)
        if values['company_regime'] not in ('general', 'rimpe_negocio_popular', 'rimpe_emprendedor'):
            return page('Datos incompletos', '<p>Selecciona un régimen tributario válido.</p>', 400)
        if not all(values[key] for key in REQUIRED_TEXT_FIELDS):
            return page('Datos incompletos', '<p>Completa todos los campos requeridos.</p>', 400)
        values['plan_id'] = plan_id
        admin = request.env.ref('base.user_admin')
        requests_model = request.env['erpec.selfservice.request'].with_user(admin).sudo()
        try:
            signup_request = requests_model.create_from_signup(values)
        except (ValidationError, UserError) as error:
            return page('No se pudo continuar', '<p>%s</p>' % escape(str(error)), 400)
        return request.redirect('/payment/payphone/checkout/' + signup_request.payment_id.reference)
