"""DI25-16: la entrada pública conserva la plantilla de Odoo (marca genérica, enlaces "#", contacto y redes de
ejemplo). Se reemplaza solo el contenido que todavía es plantilla, de forma idempotente, sin pisar ediciones
propias del cliente y sin inventar textos legales: no se muestra un enlace "Legal" sin destino real."""
import base64

from odoo import api, models, tools

BRAND = 'ERP EC · SINKRONET'

HOME_WRAP = (
    '<div id="wrap" class="oe_structure">'
    '<section class="s_text_block pt80 pb80 erpec_entry"><div class="container text-center">'
    '<p class="text-uppercase small mb-2">SINKRONET</p>'
    '<h1>ERP EC</h1>'
    '<p class="lead">Un espacio para coordinar las ventas, compras, nómina y facturación electrónica de tu empresa.</p>'
    '<p><a class="btn btn-primary btn-lg" href="/web/login">Ingresar al ERP</a></p>'
    '<p class="text-muted">Usa el acceso asignado por el administrador de tu empresa.</p>'
    '</div></section></div>'
)

FOOTER_ARCH = (
    '<data inherit_id="website.layout" name="Default" active="True">'
    '<xpath expr="//div[@id=\'footer\']" position="replace">'
    '<div id="footer" class="oe_structure oe_structure_solo" t-ignore="true" t-if="not no_footer">'
    '<section class="s_text_block pt16 pb16 erpec_entry_footer"><div class="container text-center">'
    '<p class="mb-1"><strong>ERP EC</strong> · SINKRONET · Tecnología Odoo Community</p>'
    '<p class="mb-0"><a href="/web/login">Ingresar</a></p>'
    '</div></section></div></xpath></data>'
)


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def _erpec_apply_entry_branding(self):
        View = self.env['ir.ui.view'].with_context(lang='en_US', active_test=False)
        for website in self.search([]):
            if website.name == 'My Website':
                website.name = BRAND
            if website.logo == website._default_logo():
                with tools.file_open('erpec_website_entry/static/src/logo.svg', 'rb') as handle:
                    website.logo = base64.b64encode(handle.read())
        for view in View.search([('key', '=', 'website.homepage')]):
            arch = view.arch_db or ''
            if 'oe_empty' in arch and 'erpec_entry' not in arch:
                view.arch_db = arch.replace('<div id="wrap" class="oe_structure oe_empty"/>', HOME_WRAP)
        for view in View.search([('key', '=', 'website.footer_custom')]):
            arch = view.arch_db or ''
            if 'erpec_entry_footer' not in arch and ('Useful Links' in arch or 'YourCompany' in arch or 'Copyright' in arch):
                view.arch_db = FOOTER_ARCH
        for view in View.search([('key', '=', 'website.footer_copyright_company_name')]):
            arch = view.arch_db or ''
            if 'Company name' in arch:
                view.arch_db = arch.replace('Copyright &amp;copy; Company name', '&amp;copy; SINKRONET S.A.S. · ERP EC')
        return True
