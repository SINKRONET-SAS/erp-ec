"""Archivo de pago bancario homologado (nómina): un solo perfil confirmado basta para probar el
motor; Produbanco valida además contra el ejemplo numérico real de su propia ficha técnica."""
import base64

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged, new_test_user

from .test_treasury import TreasuryCase


@tagged('post_install', '-at_install')
class BankExportCase(TreasuryCase):
    def setUp(self):
        super().setUp()
        self.accountant = new_test_user(self.env, login='bank_export_accountant', groups='account.group_account_manager')

    def bank_account(self, employee, key, acc_number, acc_type='AHO'):
        record = self.env['res.partner.bank'].create({
            'acc_number': acc_number, 'partner_id': employee.work_contact_id.id,
            'erpec_bank_key': key, 'erpec_account_type': acc_type,
        })
        employee.bank_account_id = record
        return record

    def prepared_period(self, key='pichincha', identifications=('1710034065', '1710034066')):
        period = self.period()
        period.action_prepare_payments()
        for disbursement, ident, account in zip(period.disbursement_ids, identifications, ('3112480000', '2157575798')):
            disbursement.employee_id.identification_id = ident
            self.bank_account(disbursement.employee_id, key, account)
        self.env['erpec.bank.company.account'].create({'company_id': self.env.company.id, 'bank': key, 'account_number': '1234567'})
        return period

    def test_blocked_bank_not_confirmed(self):
        period = self.prepared_period('guayaquil')
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'guayaquil', 'period_id': period.id})
        with self.assertRaisesRegex(ValidationError, 'delimitador'):
            wizard.action_generate()

    def test_blocked_without_company_account(self):
        period = self.period(); period.action_prepare_payments()
        for disbursement in period.disbursement_ids:
            disbursement.employee_id.identification_id = '1710034065'
            self.bank_account(disbursement.employee_id, 'pichincha', '3112480000')
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id})
        with self.assertRaisesRegex(ValidationError, 'Configura la cuenta propia'):
            wizard.action_generate()

    def test_blocked_without_employee_account(self):
        period = self.period(); period.action_prepare_payments()
        self.env['erpec.bank.company.account'].create({'company_id': self.env.company.id, 'bank': 'pichincha', 'account_number': '1234567'})
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id})
        with self.assertRaisesRegex(ValidationError, 'cuenta en Banco Pichincha'):
            wizard.action_generate()

    def test_requires_treasury_group(self):
        period = self.prepared_period('pichincha')
        stock = new_test_user(self.env, login='bank_export_stock', groups='stock.group_stock_user')
        with self.assertRaises(AccessError):
            self.env['erpec.bank.export.wizard'].with_user(stock).create(
                {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id}).action_generate()

    def test_pichincha_generates_tab_delimited_file_and_blocks_duplicate(self):
        period = self.prepared_period('pichincha')
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id})
        action = wizard.action_generate()
        batch = self.env['erpec.bank.export.batch'].browse(action['res_id'])
        self.assertEqual(len(batch.line_ids), 2)
        self.assertEqual(batch.total_amount, sum(period.disbursement_ids.mapped('residual')))
        content = base64.b64decode(batch.file).decode('utf-8')
        rows = [row for row in content.split('\n') if row]
        self.assertEqual(len(rows), 2)
        for row in rows:
            fields = row.split('\t')
            self.assertEqual(len(fields), 12)
            self.assertEqual(fields[0], 'PA')
            self.assertEqual(fields[2], 'USD')
            self.assertEqual(fields[4], 'CTA')
        first_amount_cents = int(round(period.disbursement_ids[0].residual * 100))
        self.assertEqual(rows[0].split('\t')[3], str(first_amount_cents))
        with self.assertRaises(AccessError):
            batch.write({'name': 'manipulado'})
        with self.assertRaises(ValidationError):
            batch.unlink()
        with self.assertRaises(ValidationError):
            self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
                {'company_id': self.env.company.id, 'bank': 'pichincha', 'period_id': period.id}).action_generate()

    def test_produbanco_matches_official_worked_example_encoding(self):
        period = self.prepared_period('produbanco')
        disbursement = period.disbursement_ids[0]
        disbursement.employee_id.identification_id = '0912378320001'
        self.bank_account(disbursement.employee_id, 'produbanco', '1825321', acc_type='CTE')
        disbursement.employee_id.name = 'JUAN PEREZ IZQUIERDO'
        self.env['erpec.bank.company.account'].search(
            [('company_id', '=', self.env.company.id), ('bank', '=', 'produbanco')]).account_number = '13040143820'
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'produbanco', 'period_id': period.id})
        action = wizard.action_generate()
        batch = self.env['erpec.bank.export.batch'].browse(action['res_id'])
        content = base64.b64decode(batch.file).decode('utf-8')
        row = [line for line in content.split('\n') if line][0].split('\t')
        self.assertEqual(row[0], 'PA')
        self.assertEqual(row[1], '13040143820')
        self.assertEqual(row[4], '00001825321')
        self.assertEqual(row[5], 'USD')
        self.assertEqual(row[7], 'CTA')
        self.assertEqual(row[8], '0036')
        self.assertEqual(row[9], 'CTE')
        self.assertEqual(row[10], '00001825321')
        self.assertEqual(row[11], 'R')
        self.assertEqual(row[12], '0912378320001')
        self.assertEqual(row[13], 'JUAN PEREZ IZQUIERDO')

    def test_ruminahui_does_not_zero_pad_amount(self):
        period = self.prepared_period('ruminahui')
        disbursement = period.disbursement_ids[1]
        wizard = self.env['erpec.bank.export.wizard'].with_user(self.accountant).create(
            {'company_id': self.env.company.id, 'bank': 'ruminahui', 'period_id': period.id})
        action = wizard.action_generate()
        batch = self.env['erpec.bank.export.batch'].browse(action['res_id'])
        content = base64.b64decode(batch.file).decode('utf-8')
        second_row = [line for line in content.split('\n') if line][1].split('\t')
        self.assertEqual(second_row[8], '0042')
        self.assertEqual(second_row[6], str(int(round(disbursement.residual * 100))))
