"""Establecimiento (padre) y punto de emisión (hijo): principal, protección de cambios y auditoría de integridad."""
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class EstablishmentCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write({'country_id': self.env.ref('base.ec').id})
        self.Establishment = self.env['erpec.fiscal.establishment']
        self.Point = self.env['erpec.fiscal.point']

    def _establishment(self, code, **values):
        vals = {'code': code, 'name': 'PRINCIPAL', 'address': 'LOS CARDENALES SN Y AZULEJOS'}
        vals.update(values)
        return self.Establishment.create(vals)

    def test_first_establishment_is_principal_and_principal_is_unique(self):
        first = self._establishment('011')
        second = self._establishment('012', name='Sucursal')
        self.assertTrue(first.is_principal)
        self.assertFalse(second.is_principal)
        second.is_principal = True
        self.assertTrue(second.is_principal)
        self.assertFalse(first.is_principal)

    def test_code_is_validated_and_locked_when_it_has_points(self):
        with self.assertRaises(ValidationError):
            self._establishment('1')
        establishment = self._establishment('013')
        establishment.code = '014'
        self.Point.create({'establishment_id': establishment.id, 'emission': '001', 'name': 'PRUEBAS'})
        with self.assertRaisesRegex(ValidationError, 'no se cambia'):
            establishment.code = '015'

    def test_point_takes_the_address_from_its_establishment(self):
        establishment = self._establishment('016')
        point = self.Point.create({'establishment_id': establishment.id, 'emission': '001', 'name': 'PRUEBAS'})
        self.assertEqual((point.establishment, point.establishment_name, point.establishment_address),
                         ('016', 'PRINCIPAL', 'LOS CARDENALES SN Y AZULEJOS'))
        establishment.address = 'NUEVA DIRECCIÓN 1'
        self.assertEqual(point.establishment_address, 'NUEVA DIRECCIÓN 1')

    def test_legacy_creation_keys_still_create_the_establishment_once(self):
        first = self.Point.create({'establishment': '017', 'establishment_name': 'PRINCIPAL', 'establishment_address': 'Dirección 17',
                                   'emission': '001', 'name': 'Caja 1'})
        second = self.Point.create({'establishment': '017', 'establishment_name': 'IGNORADO', 'establishment_address': 'Otra',
                                    'emission': '002', 'name': 'Caja 2'})
        self.assertEqual(first.establishment_id, second.establishment_id)
        self.assertEqual(second.establishment_name, 'PRINCIPAL')

    def test_point_codes_are_locked_once_it_has_journals(self):
        establishment = self._establishment('018')
        point = self.Point.create({'establishment_id': establishment.id, 'emission': '001', 'name': 'PRUEBAS'})
        self.assertTrue(point.journal_ids)
        with self.assertRaisesRegex(ValidationError, 'no se cambian'):
            point.emission = '002'

    def test_establishment_with_points_cannot_be_deleted(self):
        establishment = self._establishment('019')
        self.Point.create({'establishment_id': establishment.id, 'emission': '001', 'name': 'PRUEBAS'})
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                establishment.unlink()

    def test_audit_reports_legacy_journals_without_point(self):
        self.assertFalse([item for item in self.Point.audit_integrity() if '087-088' in item])
        self.env['account.journal'].create({
            'name': 'Heredado', 'code': 'AUD1', 'type': 'sale', 'company_id': self.env.company.id,
            'l10n_latam_use_documents': True, 'l10n_ec_entity': '087', 'l10n_ec_emission': '088'})
        self.assertTrue([item for item in self.Point.audit_integrity() if '087-088' in item])
