"""DI25-05.4: encargados/subencargados y evaluación del DPD (Art. 49 LOPDP). El sistema exige contrato, jerarquía y
registro de transferencias; no decide ni precarga nada."""
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class ProcessorCase(TransactionCase):
    def processor(self, **extra):
        values = {'name': 'Proveedor de hosting de ensayo', 'role': 'encargado', 'service': 'Aloja la base de datos del ERP.',
                  'data_categories': 'Identificación y datos de contacto'}
        values.update(extra)
        return self.env['erpec.data.processor'].create(values)

    def test_subprocessor_needs_a_parent_and_processor_cannot_have_one(self):
        parent = self.processor()
        with self.assertRaises(ValidationError):
            self.processor(name='Sub sin encargado', role='subencargado')
        child = self.processor(name='Sub con encargado', role='subencargado', parent_id=parent.id)
        self.assertEqual(child.parent_id, parent)
        with self.assertRaises(ValidationError):
            self.processor(name='Encargado con padre', role='encargado', parent_id=parent.id)

    def test_active_requires_a_contract_reference(self):
        with self.assertRaises(ValidationError):
            self.processor(state='active')
        self.assertEqual(self.processor(name='Con contrato', state='active', contract_reference='Contrato 2026-01').state, 'active')

    def test_international_transfer_requires_country_mechanism_and_rnpd_when_active(self):
        with self.assertRaises(ValidationError):
            self.processor(name='Nube A', cross_border=True)
        transfer = self.processor(name='Nube B', cross_border=True, transfer_country='Estados Unidos', transfer_mechanism='Consentimiento específico del titular')
        with self.assertRaises(ValidationError):
            transfer.write({'state': 'active', 'contract_reference': 'Contrato nube'})
        transfer.write({'state': 'active', 'contract_reference': 'Contrato nube', 'rnpd_reference': 'RNPD-ENSAYO-1'})
        self.assertEqual(transfer.state, 'active')

    def test_dpo_assessment_is_recorded_not_decided_by_the_system(self):
        company = self.env['res.company'].create({'name': 'Empresa evaluación DPD'})
        none_apply = self.env['erpec.data.dpo.assessment'].create({'company_id': company.id, 'justification': 'Sin monitoreo ni datos sensibles a gran escala.'})
        self.assertFalse(none_apply.dpo_required)
        other = self.env['res.company'].create({'name': 'Empresa con DPD obligatorio'})
        with self.assertRaises(ValidationError):
            self.env['erpec.data.dpo.assessment'].create({'company_id': other.id, 'large_scale_sensitive': True, 'justification': 'Salud a gran escala.'})
        required = self.env['erpec.data.dpo.assessment'].create({
            'company_id': other.id, 'sector': 'health', 'justification': 'Sector de salud.', 'dpo_name': 'Delegada de ensayo',
            'dpo_contact': 'dpd@example.com', 'spdp_registration': 'SPDP-ENSAYO-1'})
        self.assertTrue(required.dpo_required)
