"""Archivo de pago bancario homologado (nómina): un solo perfil confirmado basta para probar el
motor; Produbanco valida además contra el ejemplo numérico real de su propia ficha técnica.
DI26-B: la cuenta propia sale del diario bancario de nómina y la identificación del tipo declarado."""
import base64

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged, new_test_user

from .test_treasury import TreasuryCase


@tagged('post_install', '-at_install')
class BankExportCase(TreasuryCase):
    def setUp(self):
        super().setUp()
        self.accountant = new_test_user(self.env, login='bank_export_accountant', groups='erpec_payroll.group_payroll_manager')

    def bank_account(self, employee, key, acc_number, acc_type='AHO'):
        record = self.env['res.partner.bank'].create({
            'acc_number': acc_number, 'partner_id': employee.work_contact_id.id,
            'erpec_bank_key': key, 'erpec_account_type': acc_type,
        })
        employee.bank_account_id = record
        return record

    def company_account(self, key, number='1234567'):
        self.bank.bank_account_id = self.env['res.partner.bank'].create({
            'acc_number': number, 'partner_id': self.env.company.partner_id.id, 'erpec_bank_key': key})

    def prepared_period(self, key='pichincha', identifications=('1710034065', '1710034066')):
        period = self.period()
        period.action_prepare_payments()
        for disbursement, ident, account in zip(period.disbursement_ids, identifications, ('3112480000', '2157575798')):
            disbursement.employee_id.identification_id = ident
            self.bank_account(disbursement.employee_id, key, account)
        self.company_account(key)
        return period

    def generate(self, period, key):
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': key, 'period_id': period.id})
        batch = self.env['erpec.bank.export.batch'].browse(wizard.action_generate()['res_id'])
        return batch, [row.split('\t') for row in base64.b64decode(batch.file).decode('utf-8').split('\n') if row]

    def test_blocked_bank_not_confirmed(self):
        period = self.prepared_period('guayaquil')
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'guayaquil', 'period_id': period.id})
        with self.assertRaisesRegex(ValidationError, 'delimitador'):
            wizard.action_generate()

    def test_blocked_without_company_account_on_the_payroll_journal(self):
        period = self.period(); period.action_prepare_payments()
        for disbursement in period.disbursement_ids:
            disbursement.employee_id.identification_id = '1710034065'
            self.bank_account(disbursement.employee_id, 'pichincha', '3112480000')
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id})
        with self.assertRaisesRegex(ValidationError, 'diario de nómina'):
            wizard.action_generate()
        self.company_account('produbanco')
        with self.assertRaisesRegex(ValidationError, 'diario de nómina'):
            wizard.action_generate()

    def test_blocked_without_employee_account(self):
        period = self.period(); period.action_prepare_payments()
        self.company_account('pichincha')
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id})
        with self.assertRaisesRegex(ValidationError, 'cuenta en Banco Pichincha'):
            wizard.action_generate()

    def test_requires_treasury_and_payroll_groups(self):
        period = self.prepared_period('pichincha')
        stock = new_test_user(self.env, login='bank_export_stock', groups='stock.group_stock_user')
        with self.assertRaises(AccessError):
            self.env['erpec.bank.export.wizard'].with_user(stock).create(
                {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id}).action_generate()
        only_accounting = new_test_user(self.env, login='bank_export_only_accounting', groups='account.group_account_manager')
        with self.assertRaises(AccessError):
            self.env['erpec.bank.export.wizard'].with_user(only_accounting).create(
                {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id}).action_generate()

    def test_pichincha_generates_tab_delimited_file_and_blocks_duplicate(self):
        period = self.prepared_period('pichincha')
        batch, rows = self.generate(period, 'pichincha')
        self.assertEqual(len(batch.line_ids), 2)
        self.assertEqual(batch.total_amount, sum(period.disbursement_ids.mapped('residual')))
        self.assertEqual(len(rows), 2)
        for fields in rows:
            self.assertEqual(len(fields), 12)
            self.assertEqual((fields[0], fields[2], fields[4], fields[8]), ('PA', 'USD', 'CTA', 'C'))
        self.assertEqual(rows[0][3], str(int(round(period.disbursement_ids[0].residual * 100))))
        with self.assertRaises(AccessError):
            batch.write({'name': 'manipulado'})
        with self.assertRaises(ValidationError):
            batch.unlink()
        with self.assertRaises(ValidationError):
            self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
                {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id}).action_generate()

    def test_produbanco_matches_official_worked_example_encoding(self):
        period = self.prepared_period('produbanco')
        employee = period.disbursement_ids[0].employee_id
        employee.write({'identification_id': '0912378320001', 'name': 'JUAN PEREZ IZQUIERDO'})
        self.bank_account(employee, 'produbanco', '1825321', acc_type='CTE')
        self.company_account('produbanco', '13040143820')
        _batch, rows = self.generate(period, 'produbanco')
        row = rows[0]
        self.assertEqual(row[:2], ['PA', '13040143820'])
        self.assertEqual((row[4], row[5], row[7], row[8], row[9], row[10]), ('00001825321', 'USD', 'CTA', '0036', 'CTE', '00001825321'))
        self.assertEqual((row[11], row[12], row[13]), ('R', '0912378320001', 'JUAN PEREZ IZQUIERDO'))

    def test_ruminahui_does_not_zero_pad_amount(self):
        period = self.prepared_period('ruminahui')
        disbursement = period.disbursement_ids[1]
        _batch, rows = self.generate(period, 'ruminahui')
        self.assertEqual(rows[1][8], '0042')
        self.assertEqual(rows[1][6], str(int(round(disbursement.residual * 100))))

    def test_passport_keeps_letters_and_declared_type_wins(self):
        # DI26-03: antes 'PX39582' salía como '39582' y un pasaporte de 10 dígitos salía como cédula.
        period = self.prepared_period('produbanco')
        first, second = period.disbursement_ids.mapped('employee_id')
        first.write({'identification_id': 'PX-39582', 'ec_rdep_id_type': 'P'})
        second.write({'identification_id': '1234567890', 'ec_rdep_id_type': 'P'})
        batch, rows = self.generate(period, 'produbanco')
        self.assertEqual([(r[11], r[12]) for r in rows], [('P', 'PX39582'), ('P', '1234567890')])
        self.assertEqual(batch.line_ids.mapped('id_type'), ['P', 'P'])

    def test_invalid_identification_is_rejected_not_truncated(self):
        period = self.prepared_period('produbanco')
        period.disbursement_ids[0].employee_id.write({'identification_id': '12345', 'ec_rdep_id_type': 'C'})
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'produbanco', 'period_id': period.id})
        with self.assertRaisesRegex(ValidationError, 'no es una cédula'):
            wizard.action_generate()
        period.disbursement_ids[0].employee_id.write({'identification_id': 'AB1234567890123', 'ec_rdep_id_type': 'P'})
        with self.assertRaisesRegex(ValidationError, 'supera los 13'):
            wizard.action_generate()
