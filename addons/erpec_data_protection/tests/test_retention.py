"""DI25-05.3: la eliminación no se responde como cumplida cuando hay un bloqueo legal declarado; sin excepción
documentada no se puede responder, con ella sí (respuesta parcial). El plazo fiscal de 7 años (Art. 41 del Reglamento de
Comprobantes de Venta, Retención y Documentos Complementarios) se prueba con facturas reales en erpec_acceptance."""
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class RetentionCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.officer = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Responsable de conservación', 'login': 'dpo_retention_test',
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('erpec_data_protection.group_data_protection_officer').id])]})

    def request(self, **extra):
        values = {'name': 'Eliminación - Titular de prueba', 'request_type': 'eliminacion', 'requester_name': 'Titular de prueba',
                  'responsible_id': self.officer.id, 'identity_verified': True, 'response_notes': 'Se eliminan los datos no sujetos a conservación.'}
        values.update(extra)
        return self.env['erpec.data.subject.request'].with_user(self.officer).create(values)

    def test_legal_hold_needs_a_reason(self):
        with self.assertRaises(ValidationError):
            self.request(legal_hold=True)

    def test_legal_hold_blocks_erasure_until_the_exception_is_documented(self):
        request = self.request(legal_hold=True, legal_hold_reason='Auditoría del SRI en curso')
        self.assertIn('Bloqueo legal declarado', request.retention_blockers)
        with self.assertRaisesRegex(UserError, 'sin documentar la excepción'):
            request.action_mark_answered()
        request.exception_notes = 'Se conservan los datos requeridos por la auditoría (Art. 18 LOPDP).'
        request.action_mark_answered()
        self.assertEqual(request.state, 'answered')

    def test_other_rights_and_free_erasure_are_not_blocked(self):
        free = self.request()
        self.assertFalse(free.retention_blockers)
        free.action_mark_answered()
        self.assertEqual(free.state, 'answered')
        access = self.request(request_type='acceso', legal_hold=True, legal_hold_reason='Litigio')
        self.assertFalse(access.retention_blockers)
        access.action_mark_answered()
