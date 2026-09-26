"""Pruebas del registro de actividades de tratamiento (RAT) y exclusión de correo comercial."""
from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class DataProtectionCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.officer = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Responsable de datos', 'login': 'dpo_test',
            'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('erpec_data_protection.group_data_protection_officer').id])],
        })

    def test_create_activity_requires_required_fields(self):
        activity = self.env['erpec.data.processing.activity'].with_user(self.officer).create({
            'name': 'Nómina de empleados', 'purpose': 'Calcular y pagar remuneraciones',
            'legal_basis': 'obligacion_legal', 'data_subjects': 'Empleados',
            'data_categories': 'Identificación, remuneración, cargas familiares',
            'responsible_id': self.officer.id,
        })
        self.assertEqual(activity.state, 'draft')

    def test_cross_border_transfer_requires_country(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['erpec.data.processing.activity'].with_user(self.officer).create({
                'name': 'Respaldo en la nube', 'purpose': 'Almacenamiento de respaldo',
                'legal_basis': 'interes_legitimo', 'data_subjects': 'Clientes',
                'data_categories': 'Identificación y contacto',
                'responsible_id': self.officer.id, 'cross_border_transfer': True,
            })

    def test_unique_name_per_company(self):
        values = {'name': 'Facturación de clientes', 'purpose': 'Emitir comprobantes de venta',
                  'legal_basis': 'necesidad_contractual', 'data_subjects': 'Clientes',
                  'data_categories': 'Identificación y datos de facturación', 'responsible_id': self.officer.id}
        self.env['erpec.data.processing.activity'].with_user(self.officer).create(values)
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['erpec.data.processing.activity'].with_user(self.officer).create(values)

    def test_access_requires_data_protection_officer(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Sin permiso de datos', 'login': 'no_dpo_test',
            'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            self.env['erpec.data.processing.activity'].with_user(user).create({
                'name': 'Intento sin permiso', 'purpose': 'x', 'legal_basis': 'consentimiento',
                'data_subjects': 'x', 'data_categories': 'x', 'responsible_id': self.officer.id,
            })

    def test_marketing_opt_out(self):
        partner = self.env['res.partner'].create({'name': 'Cliente de ensayo LOPDP', 'email': 'Ensayo.LOPDP@example.com'})
        self.assertFalse(partner.ec_marketing_email_opt_out)
        partner.with_user(self.officer).action_ec_mark_marketing_opt_out()
        partner.invalidate_recordset()
        self.assertTrue(partner.ec_marketing_email_opt_out)
        self.assertTrue(partner.is_blacklisted, 'La exclusión debe quedar en la lista negra que respetan los envíos masivos.')
        self.assertEqual(partner.ec_marketing_email_opt_out_date, fields.Date.today())
        self.assertIn(partner, self.env['res.partner'].search([('ec_marketing_email_opt_out', '=', True)]))

    def test_blacklist_is_the_single_authority(self):
        # DI26-04: una baja desde el enlace de un correo (lista negra) se refleja en la exclusión del contacto.
        partner = self.env['res.partner'].create({'name': 'Baja desde enlace', 'email': 'baja.enlace@example.com'})
        self.env['mail.blacklist'].sudo()._add('baja.enlace@example.com')
        partner.invalidate_recordset()
        self.assertTrue(partner.ec_marketing_email_opt_out)
        partner.ec_marketing_email_opt_out = False
        partner.invalidate_recordset()
        self.assertFalse(partner.is_blacklisted)

    def test_marketing_opt_out_requires_email_and_permission(self):
        partner = self.env['res.partner'].create({'name': 'Sin correo'})
        with self.assertRaisesRegex(UserError, 'no tiene un correo'):
            partner.with_user(self.officer).action_ec_mark_marketing_opt_out()
        seller = new_test_user(self.env, login='dp_optout_seller', groups='base.group_user')
        with self.assertRaises(AccessError):
            partner.with_user(seller).action_ec_mark_marketing_opt_out()

    def test_views_compile(self):
        arch = self.env['erpec.data.processing.activity'].with_user(self.officer).get_view(view_type='form')['arch']
        self.assertIn('legal_basis', arch)
        partner_arch = self.env['res.partner'].with_user(self.officer).get_view(view_type='form')['arch']
        self.assertIn('action_ec_mark_marketing_opt_out', partner_arch)
