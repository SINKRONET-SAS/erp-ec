"""Migración de diarios existentes a puntos de emisión, adopción de diarios, punto por usuario y diario de liquidaciones."""
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.erpec_fiscal_native.tests.test_xades import ISSUER_RUC


@tagged('post_install', '-at_install')
class MigrationCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write({'country_id': self.env.ref('base.ec').id, 'street': 'Calle de la empresa 1'})
        self.env.company.with_context(no_vat_validation=True).write({'vat': ISSUER_RUC})
        self.Point = self.env['erpec.fiscal.point']

    def _legacy(self, entity='005', emission='007', code='LEG1'):
        return self.env['account.journal'].create({
            'name': 'Facturas heredadas %s-%s' % (entity, emission), 'code': code, 'type': 'sale', 'company_id': self.env.company.id,
            'l10n_latam_use_documents': True, 'l10n_ec_entity': entity, 'l10n_ec_emission': emission})

    def _point(self, entity, emission, **values):
        vals = {'establishment': entity, 'establishment_name': 'PRINCIPAL', 'establishment_address': 'LOS CARDENALES SN Y AZULEJOS',
                'emission': emission, 'name': 'PRUEBAS'}
        vals.update(values)
        return self.Point.create(vals)

    def _move(self, journal):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'journal_id': journal.id, 'invoice_date': '2026-09-18', 'date': '2026-09-18',
            'partner_id': self.env['res.partner'].create({'name': 'Cliente migración'}).id,
            'l10n_latam_document_type_id': self.env.ref('l10n_ec.ec_dt_01').id,
            'invoice_line_ids': [(0, 0, {'name': 'Servicio', 'quantity': 1, 'price_unit': 10})]})
        move.l10n_latam_document_number = '%s-%s-000000001' % (journal.l10n_ec_entity, journal.l10n_ec_emission)
        move.action_post()
        return move

    def test_new_point_adopts_a_matching_legacy_journal(self):
        legacy = self._legacy()
        point = self._point('005', '007')
        self.assertEqual(point.journal_ids, legacy)
        self.assertEqual(legacy.ec_point_id, point)

    def test_dry_run_changes_nothing_and_apply_creates_point_from_company_address(self):
        legacy = self._legacy()
        report = self.Point.migrate_journals(dry_run=True)
        self.assertTrue(any(item['action'] == 'crear punto y adoptar diario' and item['point'] == '005-007' for item in report))
        self.assertFalse(legacy.ec_point_id)
        self.Point.migrate_journals(dry_run=False)
        point = self.Point.search([('establishment', '=', '005'), ('emission', '=', '007')])
        self.assertEqual(point.establishment_address, 'Calle de la empresa 1')
        self.assertEqual(legacy.ec_point_id, point)

    def test_company_without_address_requires_data(self):
        self.env.company.street = False
        self._legacy()
        report = self.Point.migrate_journals(dry_run=False)
        item = next(item for item in report if item['point'] == '005-007')
        self.assertEqual(item['action'], 'requiere datos')
        self.assertFalse(self.Point.search([('establishment', '=', '005')]))

    def test_existing_point_with_empty_own_journal_adopts_legacy_with_history(self):
        point = self._point('006', '008')
        own = point.journal_ids
        legacy = self._legacy('006', '008', 'LEG2')
        move = self._move(legacy)
        number = move.l10n_latam_document_number
        self.Point.migrate_journals(dry_run=False)
        self.assertEqual(legacy.ec_point_id, point)
        self.assertFalse(own.active)
        self.assertFalse(own.ec_point_id)
        self.assertEqual(move.l10n_latam_document_number, number)

    def test_conflict_when_both_journals_have_history(self):
        point = self._point('006', '009')
        own = point.journal_ids
        self._move(own)
        legacy = self._legacy('006', '009', 'LEG3')
        self._move(legacy)
        report = self.Point.migrate_journals(dry_run=False)
        item = next(item for item in report if item['point'] == '006-009')
        self.assertEqual(item['action'], 'conflicto')
        self.assertFalse(legacy.ec_point_id)
        self.assertTrue(own.active)

    def test_migration_requires_accounting_manager(self):
        accountant = new_test_user(self.env, login='migration_accountant', groups='account.group_account_user')
        with self.assertRaisesRegex(ValidationError, 'responsable contable'):
            self.Point.with_user(accountant).migrate_journals()

    def test_liquidation_journal_is_created_once_per_environment(self):
        point = self._point('007', '001')
        action = point.action_create_liquidation_journal()
        journal = self.env['account.journal'].browse(action['res_id'])
        self.assertEqual((journal.type, journal.ec_point_id, journal.ec_sri_ambiente), ('purchase', point, '1'))
        self.assertTrue(journal.l10n_latam_use_documents)
        self.assertEqual(point.action_create_liquidation_journal()['res_id'], journal.id)

    def test_user_default_point_is_self_writable(self):
        self.assertIn('ec_point_id', self.env['res.users'].SELF_WRITEABLE_FIELDS)
