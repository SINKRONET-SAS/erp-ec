"""DI25-05.4: canal público de derechos del titular. Visitante sin cuenta, CSRF, honeypot, validación, deshabilitado sin responsable."""
import re

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class RightsChannelCase(HttpCase):
    def setUp(self):
        super().setUp()
        self.company = self.env['website'].search([], limit=1).company_id
        self.responsible = self.env.ref('base.user_admin')

    def token(self):
        page = self.url_open('/derechos-datos')
        self.assertEqual(page.status_code, 200)
        match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
        return page, (match.group(1) if match else None)

    def payload(self, token, **extra):
        data = {'csrf_token': token, 'request_type': 'acceso', 'requester_name': 'Titular de prueba', 'requester_identification': '0912345678',
                'requester_email': 'titular@example.com', 'description': 'Quiero saber qué datos tienen de mí.'}
        data.update(extra)
        return data

    def test_disabled_without_a_responsible(self):
        self.company.ec_dp_public_responsible_id = False
        page = self.url_open('/derechos-datos')
        self.assertIn('no está habilitado', page.text)
        self.assertNotIn('/derechos-datos/enviar', page.text)

    def test_visitor_submits_and_the_responsible_gets_an_internal_request(self):
        self.company.ec_dp_public_responsible_id = self.responsible
        page, token = self.token()
        self.assertIn('Derechos sobre tus datos personales', page.text)
        self.assertTrue(token)
        response = self.url_open('/derechos-datos/enviar', data=self.payload(token))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Recibimos tu solicitud', response.text)
        record = self.env['erpec.data.subject.request'].search([('requester_email', '=', 'titular@example.com')], limit=1)
        self.assertEqual(record.channel, 'publico')
        self.assertEqual(record.responsible_id, self.responsible)
        self.assertFalse(record.identity_verified, 'La identidad la verifica el responsable, no el formulario.')
        self.assertTrue(record.activity_ids, 'Debe agendarse la tarea interna de respuesta.')

    def test_form_informs_controller_purpose_basis_and_retention(self):
        # DI26-15: el formulario identifica al responsable y explica finalidad, base legal y conservación.
        self.company.write({'ec_dp_public_responsible_id': self.responsible.id, 'vat': '1710034065001', 'ec_dp_rights_email': 'datos@example.com'})
        page, _token = self.token()
        for text in (self.company.name, '1710034065001', 'datos@example.com', 'Finalidad', 'Base legal', 'Conservación'):
            self.assertIn(text, page.text)

    def test_invalid_data_and_honeypot_create_nothing(self):
        self.company.ec_dp_public_responsible_id = self.responsible
        _page, token = self.token()
        before = self.env['erpec.data.subject.request'].search_count([])
        bad = self.url_open('/derechos-datos/enviar', data=self.payload(token, requester_email='no-es-correo'))
        self.assertIn('correo válido', bad.text)
        bot = self.url_open('/derechos-datos/enviar', data=self.payload(token, website_url='http://spam.example'))
        self.assertIn('No se pudo procesar', bot.text)
        wrong_type = self.url_open('/derechos-datos/enviar', data=self.payload(token, request_type='inventado'))
        self.assertIn('Elige el derecho', wrong_type.text)
        self.assertEqual(self.env['erpec.data.subject.request'].search_count([]), before)

    def test_missing_csrf_is_rejected(self):
        self.company.ec_dp_public_responsible_id = self.responsible
        before = self.env['erpec.data.subject.request'].search_count([])
        response = self.url_open('/derechos-datos/enviar', data=self.payload('token-falso'))
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(self.env['erpec.data.subject.request'].search_count([]), before)

    def test_footer_links_to_the_channel(self):
        footer = self.env['ir.ui.view'].with_context(lang='en_US', active_test=False).search([('key', '=', 'website.footer_custom')], limit=1)
        self.assertIn('/derechos-datos', footer.arch_db)
