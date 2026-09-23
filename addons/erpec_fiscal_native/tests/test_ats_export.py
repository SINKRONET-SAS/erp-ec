"""Genera un XML real del ATS (pieza mínima, no el agregador completo) y lo valida contra el
esquema oficial. DI25-04.2 (pieza reutilizable) + DI25-04.3 (validado además contra el motor real
del DIMM en sesión; ese paso no se automatiza aquí porque depende de una instalación local de
terceros, ver scripts/verify-ats-dimm.py y docs/evidencias/DI25/DI25-04-dimm-validacion.json)."""
from pathlib import Path

from lxml import etree
from odoo.tests import TransactionCase, tagged

from .. import ats_export

XSD_PATH = Path(__file__).resolve().parent.parent / 'xsd' / 'at.xsd'


def _header(**overrides):
    return dict({
        'tipo_id_informante': 'R', 'id_informante': '1790012345001',
        'razon_social': 'Comercial Andina DEMO', 'anio': 2026, 'mes': '09',
        'codigo_operativo': 'IVA',
    }, **overrides)


def _compra(**overrides):
    return dict({
        'cod_sustento': '02', 'tp_id_prov': '01', 'id_prov': '0992222222001',
        'tipo_comprobante': '1', 'fecha_registro': '11/09/2026', 'establecimiento': '001',
        'punto_emision': '001', 'secuencial': '000900001', 'fecha_emision': '11/09/2026',
        'autorizacion': '1234567890123456789012345678901234567890123456789',
        'base_no_gra_iva': 0, 'base_imponible': 200.0, 'base_imp_grav': 200.0, 'base_imp_exe': 0,
        'monto_ice': 0, 'monto_iva': 30.0, 'val_ret_bien10': 0, 'val_ret_serv20': 0,
        'valor_ret_bienes': 0, 'val_ret_serv50': 0, 'valor_ret_servicios': 0, 'val_ret_serv100': 0,
        'tot_bases_imp_reemb': 0, 'pago_local_o_exterior': '01',
        'aplica_convenio_doble_tributacion': 'NA', 'pago_exterior_sujeto_retencion_normativa': 'NA',
    }, **overrides)


@tagged('post_install', '-at_install')
class AtsExportCase(TransactionCase):
    def test_minimal_purchase_produces_schema_valid_xml(self):
        # DI25-04.3, sesión 23-09-2026: este XML exacto (misma forma de datos) se validó además
        # contra el motor real del DIMM (ValidacionATS.validarEsquema/validarInformacion) sin
        # errores; ver docs/evidencias/DI25/DI25-04-dimm-validacion.json.
        xml_bytes = ats_export.build_ats_xml(_header(), [_compra()])
        schema = etree.XMLSchema(etree.parse(str(XSD_PATH)))
        doc = etree.fromstring(xml_bytes)
        self.assertTrue(schema.validate(doc), schema.error_log)
        self.assertEqual(doc.find('IdInformante').text, '1790012345001')
        self.assertEqual(doc.find('compras/detalleCompras/tipoComprobante').text, '01')

    def test_voucher_type_is_zero_padded_to_satisfy_the_schema_pattern(self):
        # tipoComprobanteCompraAnuType exige \d\w\w? (mínimo 2 caracteres); ats_catalog.py guarda
        # los códigos de un dígito ('1', '2'...) sin relleno, así que hay que rellenarlos al emitir.
        xml_bytes = ats_export.build_ats_xml(_header(), [_compra(tipo_comprobante='1')])
        doc = etree.fromstring(xml_bytes)
        self.assertEqual(doc.find('compras/detalleCompras/tipoComprobante').text, '01')

    def test_rejects_a_sustento_not_declared_in_the_official_catalog(self):
        with self.assertRaisesRegex(ValueError, 'catálogo oficial'):
            ats_export.build_ats_xml(_header(), [_compra(cod_sustento='99')])

    def test_rejects_a_sustento_not_valid_for_the_voucher_type(self):
        # Tabla 4 del catálogo: el comprobante '10' (Distribución de Dividendos) solo admite
        # sustento '10'; forzar '02' debe rechazarse sin generar el XML.
        with self.assertRaisesRegex(ValueError, 'no admite el sustento'):
            ats_export.build_ats_xml(_header(), [_compra(tipo_comprobante='19', cod_sustento='01')])

    def test_rejects_incomplete_header_or_purchase(self):
        with self.assertRaisesRegex(ValueError, 'encabezado'):
            ats_export.build_ats_xml(_header(razon_social=''), [_compra()])
        with self.assertRaisesRegex(ValueError, 'línea de compra'):
            ats_export.build_ats_xml(_header(), [_compra(base_imponible=None)])

    def test_rejects_empty_purchase_list(self):
        with self.assertRaisesRegex(ValueError, 'al menos una compra'):
            ats_export.build_ats_xml(_header(), [])
