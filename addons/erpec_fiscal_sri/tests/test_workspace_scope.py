"""DI25-14: el Inicio deriva el estado fiscal de lo instalado y configurado; no atribuye a la ausencia global
del motor lo que es falta de configuración de la empresa, ni oculta la validación externa."""
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class WorkspaceScopeCase(TransactionCase):
    def scope(self, company):
        model = self.env['erpec.workspace'].with_company(company)
        workspace = model.search([('company_id', '=', company.id)], limit=1) or model.create({'company_id': company.id})
        workspace.invalidate_recordset(['fiscal_scope'])
        return workspace.fiscal_scope

    def test_installed_scope_is_stated_and_missing_setup_is_separate(self):
        company = self.env['res.company'].create({'name': 'Empresa sin configurar fiscal'})
        text = self.scope(company)
        self.assertIn('Alcance instalado: firma electrónica, envío directo al SRI', text)
        self.assertNotIn('Faltan firma electrónica', text)
        self.assertIn('Falta configurar en esta empresa', text)
        self.assertIn('RUC de la empresa', text)
        self.assertIn('cargar el certificado de firma electrónica', text)
        self.assertIn('registrar el establecimiento y el punto de emisión', text)
        self.assertIn('solo el SRI acredita una autorización', text)

    def test_complete_setup_and_production_are_reported(self):
        company = self.env['res.company'].create({'name': 'Empresa fiscal completa'})
        company.with_context(no_vat_validation=True).vat = '1790012345001'
        self.env['erpec.fiscal.certificate'].sudo().create({'company_id': company.id}).sudo().verified = True
        establishment = self.env['erpec.fiscal.establishment'].create({'company_id': company.id, 'code': '001', 'name': 'Matriz', 'address': 'Quito'})
        point = self.env['erpec.fiscal.point'].create({'company_id': company.id, 'establishment_id': establishment.id, 'emission': '001', 'name': 'Caja 1'})
        text = self.scope(company)
        self.assertIn('Configuración de esta empresa completa', text)
        self.assertIn('Ambiente actual: pruebas', text)
        self.env.cr.execute('UPDATE erpec_fiscal_point SET ambiente=%s WHERE id=%s', ['2', point.id])
        point.invalidate_recordset(['ambiente'])
        self.assertIn('Producción habilitada en 1 punto(s)', self.scope(company))

    def test_emission_inbox_offers_no_manual_creation_and_guides_to_origin(self):
        # DI25-15: el servidor exige origen contabilizado, así que la bandeja no ofrece "Nuevo".
        arch = self.env['erpec.fiscal.emission'].get_view(view_type='list')['arch']
        self.assertIn('create="false"', arch.replace("'", '"').replace('create="0"', 'create="false"'))
        self.assertEqual(self.env['erpec.fiscal.emission']._fields['state'].string, 'Estado')
        help_text = self.env.ref('erpec_fiscal_sri.emission_action').help
        self.assertIn('abre la factura, nota, liquidación, retención o guía de origen', help_text)
