import base64,hashlib
from odoo.tests import TransactionCase,tagged,new_test_user
from odoo.exceptions import ValidationError,AccessError
from lxml import etree
from ..engine import modulo11,access_key


@tagged('post_install','-at_install')
class NativeCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id':[(4,self.env.ref('account.group_account_user').id)]})
        self.env.company.with_context(no_vat_validation=True).write({'vat':'1790012345001','street':'Matriz de ensayo','ec_native_ordinary':True,'ec_native_accounting':'SI'})
        self.partner=self.env['res.partner'].with_context(no_vat_validation=True).create({'name':'Cliente & ensayo','vat':'1790012345001','street':'Dirección de ensayo','l10n_latam_identification_type_id':self.env.ref('l10n_ec.ec_ruc').id})
        group=self.env['account.tax.group'].create({'name':'IVA de ensayo','l10n_ec_type':'vat15'})
        self.tax=self.env['account.tax'].create({'name':'IVA 15 ensayo','amount_type':'percent','amount':15,'type_tax_use':'sale','tax_group_id':group.id})
        self.move=self.env['account.move'].create({'move_type':'out_invoice','partner_id':self.partner.id,'invoice_date':'2026-09-11','date':'2026-09-11','ec_fiscal_payment_code':'20','invoice_line_ids':[(0,0,{'name':'Servicio & ensayo','quantity':2,'price_unit':100,'discount':10,'tax_ids':[(6,0,self.tax.ids)]})]})
        self.move.l10n_latam_document_number='001-001-000000333';self.move.action_post()

    def preview(self):
        return self.env['erpec.fiscal.preview'].browse(self.move.action_native_preview()['res_id'])

    def test_xml_totals_schema_and_repeat_without_queue(self):
        p=self.preview();xml=base64.b64decode(p.xml_file);tree=etree.fromstring(xml)
        self.assertEqual(tree.findtext('infoFactura/importeTotal'),'207.00')
        self.assertEqual(tree.findtext('detalles/detalle/descuento'),'20.00')
        self.assertEqual(tree.findtext('infoFactura/totalDescuento'),'20.00')
        self.assertEqual(tree.findtext('infoFactura/totalConImpuestos/totalImpuesto/valor'),'27.00')
        self.assertEqual(tree.findtext('infoFactura/razonSocialComprador'),'Cliente & ensayo')
        self.assertEqual(p.digest,hashlib.sha256(xml).hexdigest())
        self.assertEqual(self.preview().xml_file,p.xml_file)
        self.assertEqual(len(p.access_key),49);self.assertEqual(p.access_key[23],'1')
        self.assertFalse(self.move.ec_fiscal_job_ids)
        with self.assertRaises(ValidationError):p.write({'access_key':'falsa'})
        with self.assertRaises(ValidationError):self.env['erpec.fiscal.preview'].create({'move_id':self.move.id})
        self.assertIn('ec_native_notice',self.move.get_view(view_type='form')['arch'])

    def test_no_fictitious_emitter_or_unsupported_tax(self):
        self.env.company.vat=False
        with self.assertRaisesRegex(ValidationError,'RUC real'):self.preview()
        self.env.company.with_context(no_vat_validation=True).vat='1790012345001'
        self.env.company.ec_native_ordinary=False
        with self.assertRaises(ValidationError):self.preview()
        self.env.company.ec_native_ordinary=True
        self.tax.amount=14
        with self.assertRaises(ValidationError):self.preview()

    def test_permissions_and_isolation(self):
        p=self.preview()
        other=self.env['res.company'].create({'name':'Otra empresa ensayo'})
        user=new_test_user(self.env,login='fiscal_native_other',groups='account.group_account_user',company_id=other.id,company_ids=[(6,0,other.ids)])
        with self.assertRaises(AccessError):self.move.with_user(user).action_native_preview()
        with self.assertRaises(AccessError):p.with_user(user).read(['xml_file'])

    def test_modulo_and_access_key_edges(self):
        self.assertEqual(modulo11('0'*48),0)
        self.assertEqual(modulo11('6'),1)
        key=access_key('2026-09-11','1790012345001','001-002-000000003','12345678')
        self.assertEqual(key[:10],'1109202601');self.assertEqual(key[24:39],'001002000000003')
        self.assertEqual(int(key[-1]),modulo11(key[:-1]))
        for number in ['001-001-000000000','001-001-1','000-001-000000001']:
            with self.assertRaises(ValueError):access_key('2026-09-11','1790012345001',number,'12345678')

    def test_preserves_existing_external_authority(self):
        from odoo.addons.erpec_fiscal_connector.connector import _INTERNAL
        connection=self.env['erpec.fiscal.connection'].create({'company_id':self.env.company.id,'base_url':'http://127.0.0.1:3099','organization_ref':'ensayo','empresa_ref':1,'workspace_ref':1,'emission_point_ref':1})
        self.env['erpec.fiscal.job'].with_context(_fiscal_internal=_INTERNAL).create({'move_id':self.move.id,'connection_id':connection.id,'external_reference':'ensayo-native-block','correlation_id':'ensayo','payload':{}})
        with self.assertRaisesRegex(ValidationError,'asignada al Facturador'):self.preview()
