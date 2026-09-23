"""DI25-04.4: la matriz fiscal no se homologa a sí misma ni precarga ICE/ISD sin sustento."""
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TaxMatrixCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_manager').id)]})
        self.model = self.env['erpec.fiscal.tax.matrix']

    def test_requires_a_reference(self):
        with self.assertRaisesRegex(ValidationError, 'fuente normativa'):
            self.model.create({'company_id': self.env.company.id, 'reference': '   '})

    def test_ice_or_isd_require_a_note_because_no_code_catalog_is_transcribed_yet(self):
        with self.assertRaisesRegex(ValidationError, 'ICE/ISD'), self.cr.savepoint():
            self.model.create({'company_id': self.env.company.id, 'reference': 'Criterio del responsable', 'ice_applies': True})
        matrix = self.model.create({
            'company_id': self.env.company.id, 'reference': 'Criterio del responsable',
            'ice_applies': True, 'note': 'Bebidas alcohólicas, tarifa X según LRTI art. Y.'})
        self.assertTrue(matrix.ice_applies)

    def test_starts_unapproved_and_only_an_explicit_action_approves_it(self):
        matrix = self.model.create({'company_id': self.env.company.id, 'reference': 'Criterio del responsable'})
        self.assertFalse(matrix.approved)
        self.assertFalse(matrix.approved_by)
        matrix.action_approve()
        self.assertTrue(matrix.approved)
        self.assertEqual(matrix.approved_by, self.env.user)
        self.assertTrue(matrix.approved_at)

    def test_editing_content_after_approval_revokes_it(self):
        matrix = self.model.create({'company_id': self.env.company.id, 'reference': 'Criterio del responsable'})
        matrix.action_approve()
        matrix.write({'vat_applies': False})
        self.assertFalse(matrix.approved)
        self.assertFalse(matrix.approved_by)

    def test_revoke_action(self):
        matrix = self.model.create({'company_id': self.env.company.id, 'reference': 'Criterio del responsable'})
        matrix.action_approve()
        matrix.action_revoke_approval()
        self.assertFalse(matrix.approved)

    def test_one_matrix_per_company(self):
        self.model.create({'company_id': self.env.company.id, 'reference': 'Criterio del responsable'})
        with self.assertRaises(Exception), self.cr.savepoint():
            self.model.create({'company_id': self.env.company.id, 'reference': 'Otro criterio'})

    def test_account_user_can_read_but_not_write(self):
        user = new_test_user(self.env, login='matriz_solo_lectura', groups='base.group_user,account.group_account_user')
        matrix = self.model.create({'company_id': self.env.company.id, 'reference': 'Criterio del responsable'})
        self.assertEqual(matrix.with_user(user).reference, 'Criterio del responsable')
        with self.assertRaises(AccessError):
            matrix.with_user(user).write({'vat_applies': False})
        with self.assertRaises(AccessError):
            self.model.with_user(user).create({'company_id': self.env.company.id, 'reference': 'x'})
