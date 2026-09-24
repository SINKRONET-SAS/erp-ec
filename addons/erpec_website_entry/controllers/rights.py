"""DI25-05.4: canal público de derechos del titular (LOPDP). Registra la solicitud como tarea interna del responsable
designado en la empresa; no envía correos, no verifica identidad (eso lo hace el responsable antes de responder, como
exige erpec_data_protection) y se deshabilita solo si la empresa no designó responsable."""
import re
from datetime import timedelta

from odoo import fields, http
from odoo.http import request

from odoo.addons.erpec_data_protection.models import RIGHTS_REQUEST_DEADLINE_DAYS, RIGHTS_REQUEST_TYPES

EMAIL = re.compile(r'^[^@\s]{1,64}@[^@\s]{1,120}\.[^@\s]{2,}$')
MAX_PER_HOUR = 30


class RightsChannel(http.Controller):
    def _company(self):
        return request.website.company_id.sudo()

    def _values(self, **extra):
        company = self._company()
        values = {'types': RIGHTS_REQUEST_TYPES, 'enabled': bool(company.ec_dp_public_responsible_id), 'rights_email': company.ec_dp_rights_email,
                  'days': RIGHTS_REQUEST_DEADLINE_DAYS, 'errors': [], 'form': {}}
        values.update(extra)
        return values

    @http.route('/derechos-datos', type='http', auth='public', website=True, sitemap=True)
    def form(self, **kw):
        return request.render('erpec_website_entry.rights_form', self._values())

    @http.route('/derechos-datos/enviar', type='http', auth='public', website=True, methods=['POST'], csrf=True, sitemap=False)
    def submit(self, **post):
        company = self._company()
        responsible = company.ec_dp_public_responsible_id
        form = {key: (post.get(key) or '').strip() for key in ('request_type', 'requester_name', 'requester_identification', 'requester_email', 'description')}
        if not responsible:
            return request.render('erpec_website_entry.rights_form', self._values(form=form, errors=['El canal público no está habilitado en este momento.']))
        errors = []
        if post.get('website_url'):
            errors.append('No se pudo procesar la solicitud.')
        if form['request_type'] not in dict(RIGHTS_REQUEST_TYPES):
            errors.append('Elige el derecho que quieres ejercer.')
        if not (2 <= len(form['requester_name']) <= 120):
            errors.append('Escribe tu nombre completo (hasta 120 caracteres).')
        if not (5 <= len(form['requester_identification']) <= 30):
            errors.append('Escribe tu cédula, RUC o pasaporte (hasta 30 caracteres); se usa para verificar tu identidad.')
        if not EMAIL.match(form['requester_email']) or len(form['requester_email']) > 160:
            errors.append('Escribe un correo válido para poder responderte.')
        if len(form['description']) > 2000:
            errors.append('El detalle admite hasta 2000 caracteres.')
        Request = request.env['erpec.data.subject.request'].sudo()
        since = fields.Datetime.now() - timedelta(hours=1)
        if not errors and Request.search_count([('company_id', '=', company.id), ('channel', '=', 'publico'), ('create_date', '>=', since)]) >= MAX_PER_HOUR:
            errors.append('Se recibieron muchas solicitudes en la última hora. Inténtalo más tarde o escribe al correo indicado.')
        if errors:
            return request.render('erpec_website_entry.rights_form', self._values(form=form, errors=errors))
        label = dict(RIGHTS_REQUEST_TYPES)[form['request_type']]
        record = Request.with_company(company).create({
            'company_id': company.id, 'name': 'Público - %s - %s' % (label.split(' (')[0], form['requester_name']), 'request_type': form['request_type'],
            'requester_name': form['requester_name'], 'requester_identification': form['requester_identification'], 'requester_email': form['requester_email'],
            'description': form['description'], 'responsible_id': responsible.id, 'channel': 'publico'})
        return request.render('erpec_website_entry.rights_done', {'reference': record.name, 'deadline': record.deadline_date, 'days': RIGHTS_REQUEST_DEADLINE_DAYS,
                                                                    'rights_email': company.ec_dp_rights_email})
