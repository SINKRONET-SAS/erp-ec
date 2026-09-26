"""DI26-D.1 (hallazgo DI26-06): "RUC Proveedor" en la información adicional de todos los comprobantes nativos, según
la Ficha Técnica SRI 2.34, Anexo 26 (Resolución NAC-DGERCGC26-00000027). Cada motor valida su XML contra el XSD oficial
después de agregar el campo."""
from lxml import etree

from odoo.tests import TransactionCase, tagged

from .. import engine, guiaremision_engine, liquidacion_engine, notacredito_engine, notadebito_engine, retencion_engine
from . import (test_guiaremision_engine, test_liquidacion_engine, test_notacredito_engine, test_notadebito_engine,
               test_reembolso_engine, test_retencion_engine)

PROVIDER = [('RUC Proveedor', '1793235327001')]


@tagged('post_install', '-at_install')
class SystemProviderCase(TransactionCase):
    def assert_provider(self, xml):
        campos = etree.fromstring(xml).findall('infoAdicional/campoAdicional')
        self.assertEqual([(c.get('nombre'), c.text) for c in campos], PROVIDER)

    def test_every_native_document_carries_the_provider_and_stays_valid(self):
        cases = [(engine, test_reembolso_engine.ReimbursementEngineCase), (notacredito_engine, test_notacredito_engine.NotaCreditoEngineCase),
                 (notadebito_engine, test_notadebito_engine.NotaDebitoEngineCase), (liquidacion_engine, test_liquidacion_engine.LiquidacionEngineCase),
                 (retencion_engine, test_retencion_engine.RetencionEngineCase), (guiaremision_engine, test_guiaremision_engine.GuiaRemisionEngineCase)]
        for module, case in cases:
            with self.subTest(documento=module.__name__):
                _key, xml = module.generate(case._data(self, info_adicional=PROVIDER))
                self.assert_provider(xml)
                _key, plain = module.generate(case._data(self))
                self.assertNotIn(b'infoAdicional', plain)

    def test_company_uses_the_system_provider_even_for_its_own_system(self):
        company = self.env['res.company'].create({'name': 'Cliente ensayo proveedor', 'vat': '1710034065001'})
        self.env['ir.config_parameter'].sudo().set_param('erpec.system_provider_vat', '1793235327001')
        self.assertEqual(company._ec_info_adicional(), PROVIDER)
        company.vat = '1793235327001'
        self.assertEqual(company._ec_info_adicional(), PROVIDER, 'Fundador (SINKRONET) también declara su propio RUC como proveedor.')
        company.vat = '1710034065001'
        company.ec_system_provider_vat = '0990000000001'
        self.assertEqual(company._ec_info_adicional(), [('RUC Proveedor', '0990000000001')])

    def test_invalid_provider_vat_is_rejected(self):
        company = self.env['res.company'].create({'name': 'Cliente ensayo proveedor 2'})
        with self.assertRaises(Exception):
            company.ec_system_provider_vat = '12345'
            company.flush_recordset()
