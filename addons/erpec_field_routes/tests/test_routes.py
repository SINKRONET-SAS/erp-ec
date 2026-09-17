"""Pruebas de control de visitas de vendedores: geocerca (Haversine), excepciones revisables
(no bloqueo duro), inmutabilidad de marcas, y aislamiento por empresa/vendedor."""
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

from ..models import haversine_meters

# Sitio de referencia: Parque La Carolina, Quito.
SITE_LAT, SITE_LON = -0.1807, -78.4864
# ~30 m al norte del sitio (dentro de un radio de 150 m).
NEARBY_LAT, NEARBY_LON = -0.18043, -78.4864
# ~2 km al norte del sitio (fuera de cualquier geocerca razonable).
FAR_LAT, FAR_LON = -0.1627, -78.4864


@tagged('post_install', '-at_install')
class RouteCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write({'groups_id': [(4, self.env.ref('erpec_field_routes.group_route_manager').id)]})
        self.employee = self.env['hr.employee'].create({'name': 'Vendedor de ensayo', 'company_id': self.env.company.id})
        self.site = self.env['erpec.route.site'].create({
            'name': 'Cliente de ensayo', 'latitude': SITE_LAT, 'longitude': SITE_LON,
            'radius_meters': 150, 'min_accuracy_meters': 50})
        self.day = self.env['erpec.route.day'].create({'employee_id': self.employee.id, 'date': '2026-09-18'})
        self.stop = self.env['erpec.route.stop'].create({'route_day_id': self.day.id, 'site_id': self.site.id})

    def test_haversine_known_distance(self):
        self.assertEqual(haversine_meters(SITE_LAT, SITE_LON, SITE_LAT, SITE_LON), 0.0)
        self.assertGreater(haversine_meters(SITE_LAT, SITE_LON, FAR_LAT, FAR_LON), 1500)
        self.assertLess(haversine_meters(SITE_LAT, SITE_LON, FAR_LAT, FAR_LON), 2500)

    def test_site_rejects_invalid_coordinates(self):
        with self.assertRaises(ValidationError):
            self.env['erpec.route.site'].create({'name': 'Inválido', 'latitude': 999, 'longitude': 0})

    def test_site_rejects_non_positive_geofence(self):
        with self.assertRaises(ValidationError):
            self.env['erpec.route.site'].create({
                'name': 'Inválido', 'latitude': 0, 'longitude': 0, 'radius_meters': 0, 'min_accuracy_meters': 10})

    def test_day_unique_per_employee_and_date(self):
        with self.assertRaises(Exception):
            self.env['erpec.route.day'].create({'employee_id': self.employee.id, 'date': '2026-09-18'})

    def test_full_visit_within_geofence_no_exception(self):
        self.stop.action_checkin(NEARBY_LAT, NEARBY_LON, 20)
        self.assertEqual(self.stop.state, 'started')
        self.assertTrue(self.stop.checkin_mark_id.within_geofence)
        self.stop.action_checkout(NEARBY_LAT, NEARBY_LON, 20)
        self.assertEqual(self.stop.state, 'completed')
        self.assertTrue(self.stop.checkout_mark_id.within_geofence)
        self.assertFalse(self.env['erpec.route.exception'].search([('stop_id', '=', self.stop.id)]))
        self.assertEqual(self.day.completion_rate, 100.0)
        self.assertEqual(self.day.within_geofence_rate, 100.0)

    def test_checkin_outside_geofence_soft_fails_with_exception(self):
        self.stop.action_checkin(FAR_LAT, FAR_LON, 20)
        self.assertEqual(self.stop.state, 'started', 'Fuera de geocerca no bloquea el check-in, solo genera excepción.')
        self.assertFalse(self.stop.checkin_mark_id.within_geofence)
        exception = self.env['erpec.route.exception'].search([('mark_id', '=', self.stop.checkin_mark_id.id)])
        self.assertEqual(len(exception), 1)
        self.assertEqual(exception.exception_type, 'geofence_violation')
        self.assertEqual(exception.state, 'pending')

    def test_checkin_low_accuracy_creates_exception(self):
        self.stop.action_checkin(NEARBY_LAT, NEARBY_LON, 999)
        self.assertTrue(self.stop.checkin_mark_id.within_geofence)
        self.assertTrue(self.stop.checkin_mark_id.low_accuracy)
        exception = self.env['erpec.route.exception'].search([('mark_id', '=', self.stop.checkin_mark_id.id)])
        self.assertEqual(exception.exception_type, 'low_accuracy')

    def test_checkout_before_checkin_blocked(self):
        with self.assertRaises(UserError):
            self.stop.action_checkout(NEARBY_LAT, NEARBY_LON, 20)

    def test_double_checkin_blocked(self):
        self.stop.action_checkin(NEARBY_LAT, NEARBY_LON, 20)
        with self.assertRaises(UserError):
            self.stop.action_checkin(NEARBY_LAT, NEARBY_LON, 20)

    def test_omit_requires_reason_and_creates_exception(self):
        with self.assertRaises(UserError):
            self.stop.action_omit('')
        self.stop.action_omit('Cliente cerrado por feriado.')
        self.assertEqual(self.stop.state, 'omitted')
        exception = self.env['erpec.route.exception'].search([('stop_id', '=', self.stop.id)])
        self.assertEqual(exception.exception_type, 'omitted_visit')

    def test_unplanned_stop_requires_reason_and_flag(self):
        with self.assertRaises(UserError):
            self.day.action_add_unplanned_stop(self.site.id, '')
        stop_id = self.day.action_add_unplanned_stop(self.site.id, 'Visita de oportunidad.')
        stop = self.env['erpec.route.stop'].browse(stop_id)
        self.assertFalse(stop.planned)
        exception = self.env['erpec.route.exception'].search([('stop_id', '=', stop.id)])
        self.assertEqual(exception.exception_type, 'unplanned_visit')
        self.day.write({'allow_unplanned': False})
        with self.assertRaises(UserError):
            self.day.action_add_unplanned_stop(self.site.id, 'Otra visita.')

    def test_complete_day_blocked_with_pending_planned_stops(self):
        self.day.action_start()
        with self.assertRaises(UserError):
            self.day.action_complete()
        self.stop.action_checkin(NEARBY_LAT, NEARBY_LON, 20)
        self.stop.action_checkout(NEARBY_LAT, NEARBY_LON, 20)
        self.day.action_complete()
        self.assertEqual(self.day.state, 'completed')

    def test_visit_mark_is_immutable(self):
        self.stop.action_checkin(NEARBY_LAT, NEARBY_LON, 20)
        mark = self.stop.checkin_mark_id
        with self.assertRaises(ValidationError):
            mark.write({'accuracy_meters': 1})
        with self.assertRaises(ValidationError):
            mark.unlink()
        with self.assertRaises(ValidationError):
            self.env['erpec.route.visit.mark'].create({
                'stop_id': self.stop.id, 'mark_type': 'checkin', 'latitude': 0, 'longitude': 0, 'accuracy_meters': 1})

    def test_exception_cannot_be_created_directly(self):
        with self.assertRaises(ValidationError):
            self.env['erpec.route.exception'].create({
                'stop_id': self.stop.id, 'exception_type': 'unplanned_visit', 'reason': 'manual'})

    def test_exception_approve_and_reject_flow(self):
        self.stop.action_checkin(FAR_LAT, FAR_LON, 20)
        exception = self.env['erpec.route.exception'].search([('mark_id', '=', self.stop.checkin_mark_id.id)])
        exception.action_approve('Cliente confirmó que se movió de local.')
        self.assertEqual(exception.state, 'approved')
        self.assertTrue(exception.reviewed_by)
        self.assertTrue(exception.reviewed_at)

    def test_exception_reject_requires_resolution(self):
        self.stop.action_omit('Motivo original.')
        exception = self.env['erpec.route.exception'].search([('stop_id', '=', self.stop.id)])
        with self.assertRaises(UserError):
            exception.action_reject('')
        exception.action_reject('No es un motivo válido, repetir la visita.')
        self.assertEqual(exception.state, 'rejected')

    def test_stop_state_immutable_outside_actions(self):
        with self.assertRaises(ValidationError):
            self.stop.write({'state': 'completed'})

    def test_wizards_call_underlying_actions(self):
        wizard = self.env['erpec.route.visit.wizard'].create({
            'stop_id': self.stop.id, 'mark_type': 'checkin',
            'latitude': NEARBY_LAT, 'longitude': NEARBY_LON, 'accuracy_meters': 15})
        wizard.action_confirm()
        self.assertEqual(self.stop.state, 'started')
        checkout_wizard = self.env['erpec.route.visit.wizard'].create({
            'stop_id': self.stop.id, 'mark_type': 'checkout',
            'latitude': NEARBY_LAT, 'longitude': NEARBY_LON, 'accuracy_meters': 15})
        checkout_wizard.action_confirm()
        self.assertEqual(self.stop.state, 'completed')

    def test_company_and_rep_isolation(self):
        other_company = self.env['res.company'].create({'name': 'Otra empresa ensayo visitas'})
        other_employee = self.env['hr.employee'].create({'name': 'Otro vendedor', 'company_id': other_company.id})
        rep_user = new_test_user(
            self.env, login='route_rep_isolation', groups='erpec_field_routes.group_route_rep',
            company_id=other_company.id, company_ids=[(6, 0, other_company.ids)])
        other_employee.write({'user_id': rep_user.id})
        with self.assertRaises(AccessError):
            self.day.with_user(rep_user).read(['state'])
        own_day = self.env['erpec.route.day'].with_user(rep_user).create({
            'employee_id': other_employee.id, 'date': '2026-09-18', 'company_id': other_company.id})
        self.assertTrue(own_day.with_user(rep_user).read(['state']))
