"""Datos de empresa comunes a la suite ERP EC."""
from odoo import api, fields, models

EC_LANG = 'es_EC'
EC_TZ = 'America/Guayaquil'


class Company(models.Model):
    _inherit = 'res.company'

    # DI26-B.4 (hallazgo DI26-12): una empresa de ensayo puede compartir un RUC real con datos ficticios; sus anexos
    # se nombran como no presentables y las pantallas lo advierten para evitar una declaración por error.
    ec_test_company = fields.Boolean(
        'Empresa de ensayo (datos ficticios)',
        help='Marca las empresas usadas para pruebas o demostraciones. Sus anexos (ATS, RDEP) se generan con el prefijo '
             'ENSAYO-NO-PRESENTAR y las pantallas avisan que no deben presentarse ante el SRI.')

    def _ec_annex_filename(self, name):
        """Nombre del archivo de un anexo; las empresas de ensayo llevan un prefijo inequívoco."""
        self.ensure_one()
        return ('ENSAYO-NO-PRESENTAR-' + name) if self.ec_test_company else name

    @api.model
    def _ec_apply_locale_defaults(self):
        """DI26-E.1 (hallazgo DI26-07): español de Ecuador y hora de Guayaquil por defecto. Deja es_EC como idioma por defecto de
        los contactos nuevos y corrige las empresas y sus contactos que quedaron en inglés o sin zona horaria. No toca a quien
        eligió otro idioma distinto del inglés de instalación. Sin es_EC activo no hace nada."""
        if not self.env['res.lang']._get_code(EC_LANG):
            return False
        self.env['ir.default'].sudo().set('res.partner', 'lang', EC_LANG)
        companies = self.sudo().with_context(active_test=False).search([])
        partners = companies.partner_id | companies.partner_id.child_ids
        partners.filtered(lambda partner: partner.lang in (False, 'en_US')).write({'lang': EC_LANG})
        partners.filtered(lambda partner: not partner.tz).write({'tz': EC_TZ})
        return True
