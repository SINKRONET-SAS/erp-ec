"""Pruebas del procedimiento operativo: solicitudes de derechos del titular e incidentes de brecha."""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class DataSubjectRequestCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.officer = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Responsable de datos', 'login': 'dpo_rights_test',
            'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('erpec_data_protection.group_data_protection_officer').id])],
        })

    def _create_request(self, **extra):
        values = {
            'name': 'Acceso - Titular de prueba', 'request_type': 'acceso',
            'requester_name': 'Titular de prueba', 'responsible_id': self.officer.id,
        }
        values.update(extra)
        return self.env['erpec.data.subject.request'].with_user(self.officer).create(values)

    def test_deadline_is_fifteen_days_from_received_date(self):
        request = self._create_request(received_date=fields.Date.to_date('2026-01-01'))
        self.assertEqual(request.deadline_date, fields.Date.to_date('2026-01-16'))

    def test_is_overdue_flag(self):
        overdue = self._create_request(received_date=fields.Date.today() - timedelta(days=20))
        self.assertTrue(overdue.is_overdue)
        recent = self._create_request(received_date=fields.Date.today())
        self.assertFalse(recent.is_overdue)

    def test_closed_request_is_never_overdue(self):
        request = self._create_request(received_date=fields.Date.today() - timedelta(days=20))
        request.with_user(self.officer).write({'identity_verified': True, 'response_notes': 'Se envió el detalle solicitado.'})
        request.with_user(self.officer).action_mark_answered()
        request.with_user(self.officer).action_close()
        self.assertFalse(request.is_overdue)
        self.assertEqual(request.state, 'closed')

    def test_cannot_answer_without_identity_verification(self):
        request = self._create_request(response_notes='Respuesta')
        with self.assertRaises(UserError), self.cr.savepoint():
            request.with_user(self.officer).action_mark_answered()

    def test_cannot_answer_without_response_notes(self):
        request = self._create_request(identity_verified=True)
        with self.assertRaises(UserError), self.cr.savepoint():
            request.with_user(self.officer).action_mark_answered()

    def test_reject_requires_exception_notes(self):
        request = self._create_request(identity_verified=True)
        with self.assertRaises(UserError), self.cr.savepoint():
            request.with_user(self.officer).action_reject()
        request.write({'exception_notes': 'Excepción del Art. 18 LOPDP aplicable.'})
        request.with_user(self.officer).action_reject()
        self.assertEqual(request.state, 'rejected')

    def test_cannot_close_before_answered_or_rejected(self):
        request = self._create_request()
        with self.assertRaises(UserError), self.cr.savepoint():
            request.with_user(self.officer).action_close()

    def test_create_schedules_reminder_activity(self):
        request = self._create_request()
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'erpec.data.subject.request'), ('res_id', '=', request.id),
        ])
        self.assertTrue(activity)
        self.assertEqual(activity.date_deadline, request.deadline_date)

    def test_views_compile(self):
        arch = self.env['erpec.data.subject.request'].with_user(self.officer).get_view(view_type='form')['arch']
        self.assertIn('deadline_date', arch)


@tagged('post_install', '-at_install')
class DataBreachIncidentCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.officer = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Responsable de brechas', 'login': 'dpo_breach_test',
            'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('erpec_data_protection.group_data_protection_officer').id])],
        })

    def _create_incident(self, **extra):
        values = {
            'name': 'Incidente de prueba', 'description': 'Acceso no autorizado a una base de datos',
            'detected_date': fields.Datetime.to_datetime('2026-01-01 08:00:00'), 'responsible_id': self.officer.id,
        }
        values.update(extra)
        return self.env['erpec.data.breach.incident'].with_user(self.officer).create(values)

    def test_authority_deadline_is_five_days_from_detection_when_responsable(self):
        incident = self._create_incident(discovered_by='responsable')
        self.assertEqual(incident.authority_notice_deadline, fields.Datetime.to_datetime('2026-01-06 08:00:00'))

    def test_encargado_deadlines_chain_correctly(self):
        incident = self._create_incident(
            discovered_by='encargado',
            encargado_notice_date=fields.Datetime.to_datetime('2026-01-02 08:00:00'),
        )
        self.assertEqual(incident.encargado_notice_deadline, fields.Datetime.to_datetime('2026-01-03 08:00:00'))
        self.assertEqual(incident.authority_notice_deadline, fields.Datetime.to_datetime('2026-01-07 08:00:00'))

    def test_encargado_notice_before_detection_is_invalid(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._create_incident(
                discovered_by='encargado',
                detected_date=fields.Datetime.to_datetime('2026-01-05 08:00:00'),
                encargado_notice_date=fields.Datetime.to_datetime('2026-01-01 08:00:00'),
            )

    def test_titular_deadline_only_when_risk_to_rights(self):
        with_risk = self._create_incident(risk_to_rights=True)
        self.assertEqual(with_risk.titular_notice_deadline, fields.Datetime.to_datetime('2026-01-04 08:00:00'))
        without_risk = self._create_incident(risk_to_rights=False)
        self.assertFalse(without_risk.titular_notice_deadline)

    def test_close_requires_authority_notified(self):
        incident = self._create_incident()
        with self.assertRaises(UserError), self.cr.savepoint():
            incident.with_user(self.officer).action_close()

    def test_close_requires_titular_notified_or_exception_when_risk(self):
        incident = self._create_incident(risk_to_rights=True)
        incident.with_user(self.officer).action_notify_authority()
        with self.assertRaises(UserError), self.cr.savepoint():
            incident.with_user(self.officer).action_close()
        incident.write({'titular_notice_exception': 'riesgo_descartado'})
        incident.with_user(self.officer).action_close()
        self.assertEqual(incident.state, 'closed')

    def test_notify_authority_advances_state(self):
        incident = self._create_incident()
        self.assertEqual(incident.state, 'draft')
        incident.with_user(self.officer).action_notify_authority()
        self.assertEqual(incident.state, 'notified')
        self.assertTrue(incident.authority_notified_date)

    def test_create_schedules_authority_reminder_activity(self):
        incident = self._create_incident()
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'erpec.data.breach.incident'), ('res_id', '=', incident.id),
        ])
        self.assertTrue(activity)

    def test_views_compile(self):
        arch = self.env['erpec.data.breach.incident'].with_user(self.officer).get_view(view_type='form')['arch']
        self.assertIn('authority_notice_deadline', arch)
