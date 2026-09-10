"""Cobros de ensayo, confirmación remota y conciliación durable con la suite."""
import hashlib
import json
import logging
import uuid
from decimal import Decimal
from urllib.parse import urlsplit

import requests
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.erpec_suite.models.commercial import administrator

_logger = logging.getLogger(__name__)
API_URL = 'https://pay.payphonetodoesposible.com/api/button/'
RETURN_PATH = '/payment/payphone/return'


class ConfigurationError(ValidationError):
    pass


def cents(value):
    result = Decimal(str(value)) * 100
    if not result.is_finite() or result != result.to_integral_value() or result < 0:
        raise ValidationError('Usa importes no negativos con un máximo de dos decimales.')
    return int(result)


class Provider(models.Model):
    _name = 'erpec.payphone.provider'
    _description = 'Configuración privada de PayPhone de pruebas'
    name = fields.Char(default='PayPhone · Pruebas', required=True)
    company_id = fields.Many2one('res.company', string='Organización operadora', required=True,
                                default=lambda self: self.env.company)
    token = fields.Char('Token de la aplicación de prueba', groups='base.group_system', copy=False)
    store_id = fields.Char('StoreID de la tienda', groups='base.group_system', copy=False)
    public_url = fields.Char('Dominio autorizado', required=True,
                            default='https://pruebas.sinkronet.com.ec')
    test_acknowledged = fields.Boolean('He comprobado que SK_ERP está en Prueba en PayPhone')
    return_url = fields.Char('URL de respuesta', compute='_compute_status')
    status = fields.Char('Preparación', compute='_compute_status')
    _sql_constraints = [('provider_company_unique', 'unique(company_id)',
                         'Ya existe una configuración PayPhone para esta organización.')]

    @api.depends('token', 'store_id', 'public_url', 'test_acknowledged')
    def _compute_status(self):
        for record in self:
            record.return_url = (record.public_url or '').rstrip('/') + RETURN_PATH
            record.status = ('Lista para preparar un ensayo; conexión externa aún no verificada'
                             if record.token and record.store_id and record.test_acknowledged
                             else 'Pendiente: Token, StoreID y confirmación del modo Prueba')

    @api.constrains('public_url')
    def _validate_url(self):
        for record in self:
            url = urlsplit(record.public_url or '')
            if (url.scheme != 'https' or not url.hostname or url.username or url.password
                    or url.query or url.fragment or url.path not in ('', '/')):
                raise ValidationError('Introduce solo el dominio HTTPS autorizado, sin ruta ni parámetros.')

    def write(self, values):
        administrator(self.env)
        self.check_access('write')
        if 'company_id' in values and self.env['erpec.payphone.payment'].sudo().search_count([('provider_id', 'in', self.ids)]):
            raise ValidationError('Una configuración con pagos no puede cambiar de organización.')
        # Mantener las credenciales de preparación durante la confirmación y sus reintentos.
        if {'token', 'store_id', 'public_url', 'test_acknowledged', 'company_id'} & values.keys():
            self.env.cr.execute('SELECT id FROM erpec_payphone_provider WHERE id IN %s ORDER BY id FOR UPDATE', [tuple(self.ids)])
            if self.env['erpec.payphone.payment'].sudo().search_count([
                    ('provider_id', 'in', self.ids), ('state', 'in', ['queued', 'prepared', 'confirming', 'review'])]):
                raise ValidationError('Hay pagos abiertos. Concílialos antes de cambiar esta configuración.')
        return super().write(values)

    def _request(self, endpoint, payload):
        self.ensure_one()
        if not self.token or not self.store_id or not self.test_acknowledged:
            raise ValidationError('Configura Token, StoreID y confirma el ambiente Prueba antes de continuar.')
        try:
            response = requests.post(API_URL + endpoint, json=payload, headers={
                'Authorization': 'Bearer ' + self.token.strip(),
                'Content-Type': 'application/json', 'Origin': self.public_url.rstrip('/'),
                'Referer': self.public_url.rstrip('/') + '/',
            }, timeout=(5, 15), allow_redirects=False)
            if endpoint == 'Prepare' and response.status_code in (401, 403):
                raise ConfigurationError('PAYPHONE_CREDENTIALS: acceso rechazado; corrige Token y StoreID antes de reintentar.')
            if response.status_code != 200:
                raise ValidationError('PAYPHONE_HTTP_%s: revisa las credenciales y el estado en PayPhone.' % response.status_code)
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            # No registrar cuerpo, cabeceras, token ni información de tarjetas.
            _logger.warning('Error de conexión PayPhone code=PAYPHONE_CONNECTION status=502 correlationId=%s userId=%s', payload.get('clientTransactionId') or payload.get('clientTxId') or 'configuracion', self.env.uid)
            raise ValidationError('PAYPHONE_CONNECTION: respuesta no disponible; revisa y concilia antes de repetir el cobro.') from error
        if not isinstance(data, dict) or data.get('errorCode'):
            raise ValidationError('PAYPHONE_RESPONSE: PayPhone no aceptó la solicitud; consulta su panel.')
        return data


class Subscription(models.Model):
    _inherit = 'erpec.subscription'
    billing_owner = fields.Selection(selection_add=[('payphone_test', 'PayPhone: ensayo local, sin alta productiva')],
                                     ondelete={'payphone_test': lambda records: records._prevent_payment_uninstall()})

    def _prevent_payment_uninstall(self):
        if self:
            raise ValidationError('Conserva los contratos de ensayo: archiva su evidencia antes de retirar la integración.')

    def action_activate(self):
        self._lock_organization()
        if self.billing_owner == 'payphone_test':
            payment = self.env['erpec.payphone.payment'].search([
                ('subscription_id', '=', self.id), ('state', '=', 'approved')], limit=1)
            if not payment or payment.contract_digest != payment._contract_digest():
                raise ValidationError('Este contrato de ensayo requiere un pago confirmado por PayPhone y conciliado con sus condiciones.')
        return super().action_activate()


class Payment(models.Model):
    _name = 'erpec.payphone.payment'
    _description = 'Pago y conciliación de prueba PayPhone'
    _rec_name = 'reference'
    _order = 'id desc'
    company_id = fields.Many2one('res.company', related='subscription_id.company_id', store=True, readonly=True, string='Organización')
    subscription_id = fields.Many2one('erpec.subscription', required=True, ondelete='restrict', string='Contrato de ensayo')
    provider_id = fields.Many2one('erpec.payphone.provider', required=True, ondelete='restrict', string='Configuración PayPhone')
    reference = fields.Char('Referencia única', readonly=True, copy=False, index=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.USD'), required=True, readonly=True)
    amount_without_tax = fields.Monetary('Base sin impuesto', currency_field='currency_id')
    amount_with_tax = fields.Monetary('Base gravada, sin impuesto', currency_field='currency_id')
    tax = fields.Monetary('Impuesto del ensayo', currency_field='currency_id')
    amount = fields.Monetary('Total USD', compute='_compute_amount', store=True, currency_field='currency_id')
    state = fields.Selection([
        ('draft', 'Borrador'), ('queued', 'Preparación en cola'), ('prepared', 'Listo para pagar'),
        ('confirming', 'Confirmación pendiente'), ('approved', 'Aprobado en prueba'),
        ('canceled', 'Cancelado por PayPhone'), ('review', 'Revisión necesaria'),
    ], default='draft', required=True, readonly=True, string='Estado del pago')
    checkout_url = fields.Char(readonly=True, copy=False, groups='base.group_system')
    remote_id = fields.Char('ID confirmado por PayPhone', readonly=True, copy=False)
    pending_remote_id = fields.Char(readonly=True, copy=False, groups='base.group_system')
    contract_digest = fields.Char(readonly=True, copy=False, groups='base.group_system')
    confirmed_at = fields.Datetime('Confirmado en servidor', readonly=True, copy=False)
    reconciled = fields.Boolean('Contrato e instancia conciliados', readonly=True, copy=False)
    attempts = fields.Integer('Intentos de confirmación', readonly=True, copy=False)
    last_error = fields.Text('Incidencia y siguiente acción', readonly=True, copy=False)
    _sql_constraints = [
        ('reference_unique', 'unique(reference)', 'Referencia de pago duplicada.'),
        ('subscription_payment_unique', 'unique(subscription_id)', 'Este contrato ya tiene un pago. Revisa el existente para evitar duplicarlo.'),
        ('remote_payment_unique', 'unique(provider_id,remote_id)', 'Esta transacción de PayPhone ya está registrada.'),
    ]

    @api.depends('amount_without_tax', 'amount_with_tax', 'tax')
    def _compute_amount(self):
        for record in self:
            record.amount = record.amount_without_tax + record.amount_with_tax + record.tax

    @api.constrains('amount_without_tax', 'amount_with_tax', 'tax', 'currency_id')
    def _validate_amounts(self):
        for record in self:
            total = sum(cents(value) for value in (record.amount_without_tax, record.amount_with_tax, record.tax))
            if total <= 0 or total > 10000 or record.currency_id.name != 'USD':
                raise ValidationError('El piloto admite ensayos en USD mayores que cero y hasta USD 100.')
            if record.tax and not record.amount_with_tax:
                raise ValidationError('El impuesto requiere una base gravada.')

    @api.model_create_multi
    def create(self, values_list):
        administrator(self.env)
        allowed = {'subscription_id', 'provider_id', 'amount_without_tax', 'amount_with_tax', 'tax'}
        for values in values_list:
            if set(values) - allowed:
                raise AccessError('No se permite fijar el estado o los identificadores de un pago.')
            subscription = self.env['erpec.subscription'].browse(values.get('subscription_id')).exists()
            provider = self.env['erpec.payphone.provider'].browse(values.get('provider_id')).exists()
            if not subscription or not provider:
                raise ValidationError('Selecciona contrato y configuración PayPhone.')
            subscription.check_access('read')
            provider.check_access('read')
            if (subscription.billing_owner != 'payphone_test' or subscription.activated_at
                    or provider.company_id != subscription.company_id):
                raise ValidationError('Usa un contrato borrador de ensayo PayPhone y configuración de la misma organización.')
            values.update(company_id=subscription.company_id.id, reference=uuid.uuid4().hex,
                          currency_id=self.env.ref('base.USD').id)
        return super().create(values_list)

    def write(self, values):
        administrator(self.env)
        self.check_access('write')
        if set(values) - {'amount_without_tax', 'amount_with_tax', 'tax'}:
            raise AccessError('Solo las acciones verificadas pueden modificar el estado del pago.')
        self._lock()
        if any(record.state != 'draft' for record in self):
            raise ValidationError('Los importes no se modifican después de enviar el pago.')
        return super().write(values)

    def _update(self, values):
        return super().write(values)

    def _lock(self):
        # Todas las rutas comparten orden: compañía, contrato, proveedor, pago.
        for record in self.sorted('id'):
            for table, identifier in [('res_company', record.company_id.id),
                                      ('erpec_subscription', record.subscription_id.id),
                                      ('erpec_payphone_provider', record.provider_id.id),
                                      ('erpec_payphone_payment', record.id)]:
                self.env.cr.execute('SELECT id FROM ' + table + ' WHERE id=%s FOR UPDATE', [identifier])
        self.invalidate_recordset()

    def _contract_digest(self):
        contract = self.subscription_id
        contract.invalidate_recordset()
        data = [contract.company_id.id, contract.plan_id.id, str(contract.starts_on), str(contract.ends_on),
                contract.billing_owner, contract.billing_reference, contract.authorization]
        return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()

    def action_prepare(self):
        self.ensure_one()
        administrator(self.env)
        self.check_access('write')
        self._lock()
        if self.state != 'draft':
            raise ValidationError('El pago ya fue enviado. Revisa su estado; no se enviará un segundo cobro.')
        provider = self.provider_id
        if not provider.token or not provider.store_id or not provider.test_acknowledged:
            raise ValidationError('Completa la configuración privada de PayPhone de pruebas.')
        if self.subscription_id.billing_owner != 'payphone_test' or self.subscription_id.activated_at:
            raise ValidationError('El contrato ya no corresponde a un borrador de ensayo.')
        self._update({'state': 'queued', 'contract_digest': self._contract_digest(), 'last_error': False})
        self.env.ref('erpec_payphone.payment_cron')._trigger()
        return True

    def _prepare(self):
        self.ensure_one()
        if (self.provider_id.company_id != self.company_id or self._contract_digest() != self.contract_digest
                or self.subscription_id.billing_owner != 'payphone_test' or self.subscription_id.activated_at):
            raise ValidationError('PAYPHONE_CONTRACT_CHANGED: revisa el contrato y la organización antes de iniciar un cobro.')
        payload = {
            'amount': sum(cents(value) for value in (self.amount_without_tax, self.amount_with_tax, self.tax)),
            'amountWithoutTax': cents(self.amount_without_tax), 'amountWithTax': cents(self.amount_with_tax),
            'tax': cents(self.tax), 'currency': 'USD', 'clientTransactionId': self.reference,
            'storeId': self.provider_id.store_id.strip(), 'reference': 'SK ERP - ensayo de integración',
            'responseUrl': self.provider_id.return_url,
        }
        data = self.provider_id._request('Prepare', payload)
        url = data.get('payWithPayPhone') or data.get('payWithCard')
        parsed = urlsplit(url or '')
        if (not data.get('paymentId') or parsed.scheme != 'https' or parsed.username or parsed.password
                or parsed.hostname != 'pay.payphonetodoesposible.com'):
            raise ValidationError('PAYPHONE_LINK: respuesta inesperada; revisa la transacción en PayPhone.')
        self._update({'state': 'prepared', 'checkout_url': url, 'last_error': False})

    def action_open_checkout(self):
        self.ensure_one()
        administrator(self.env)
        self.check_access('read')
        if self.state != 'prepared':
            raise ValidationError('El enlace solo está disponible cuando el pago está preparado.')
        return {'type': 'ir.actions.act_url', 'url': self.provider_id.public_url.rstrip('/') +
                '/payment/payphone/checkout/' + self.reference, 'target': 'new'}

    def _confirm(self, remote_id):
        self.ensure_one()
        if self.state in ('approved', 'canceled'):
            return
        data = self.provider_id._request('V2/Confirm', {'id': int(remote_id), 'clientTxId': self.reference})
        amount = sum(cents(value) for value in (self.amount_without_tax, self.amount_with_tax, self.tax))
        if (data.get('clientTransactionId') != self.reference or str(data.get('transactionId')) != str(remote_id)
                or type(data.get('amount')) is not int or data.get('amount') != amount
                or data.get('currency') != 'USD' or type(data.get('statusCode')) is not int):
            raise ValidationError('PAYPHONE_MISMATCH: el resultado no coincide con este pago. No se activó el contrato.')
        code = data['statusCode']
        if code not in (2, 3):
            raise ValidationError('PAYPHONE_PENDING: el proveedor todavía no informa un resultado final.')
        self._update({'state': 'approved' if code == 3 else 'canceled', 'remote_id': str(remote_id),
                      'confirmed_at': fields.Datetime.now(), 'pending_remote_id': False, 'last_error': False})

    def _receive_return(self, remote_id):
        self.ensure_one()
        self._lock()
        if self.state in ('approved', 'canceled'):
            return
        if self.state not in ('prepared', 'confirming', 'review') or not self.contract_digest:
            raise ValidationError('El pago no está preparado para confirmarse.')
        self._update({'state': 'confirming', 'pending_remote_id': str(remote_id)})
        self._try_confirm()

    def _try_confirm(self):
        self._update({'attempts': self.attempts + 1})
        try:
            with self.env.cr.savepoint():
                self._confirm(self.pending_remote_id)
        except ValidationError as error:
            self._update({'last_error': str(error), 'state': 'review' if self.attempts >= 3 else 'confirming'})
            _logger.warning('Confirmación pendiente code=PAYPHONE_CONFIRM status=502 correlationId=%s userId=%s', self.reference, self.env.uid)

    def _reconcile(self):
        if self.state != 'approved' or self.reconciled:
            return
        if self._contract_digest() != self.contract_digest:
            raise ValidationError('PAYPHONE_CONTRACT_CHANGED: las condiciones cambiaron. Revisar manualmente; no se activó el servicio.')
        self.subscription_id.action_activate()
        if self.subscription_id.plan_id.erp:
            self.env['erpec.provision']._request(self.subscription_id)
        self._update({'reconciled': True, 'last_error': False})

    def action_retry_confirmation(self):
        self.ensure_one()
        administrator(self.env)
        self.check_access('write')
        self._lock()
        if self.state == 'approved' and not self.reconciled:
            self._reconcile()
        elif self.pending_remote_id and self.state in ('review', 'confirming'):
            self._update({'state': 'confirming', 'attempts': 0})
            self.env.ref('erpec_payphone.payment_cron')._trigger()
        else:
            raise ValidationError('No hay una confirmación pendiente para reintentar. Revisa PayPhone antes de preparar otro pago.')
        return True

    @api.model
    def _cron_process(self):
        # Solo el administrador ejecuta la cola; cada pago conserva su organización.
        for payment in self.sudo().search([('reconciled', '=', False), ('state', 'in', ['queued', 'confirming', 'approved'])], limit=100, order='id'):
            if payment.state == 'approved' and payment.reconciled:
                continue
            payment = payment.with_user(self.env.ref('base.user_admin')).sudo().with_company(payment.company_id)
            payment._lock()
            preparing = payment.state == 'queued'
            if preparing:
                # Fuera del savepoint: el marcador persiste incluso si cae la conexión externa.
                payment._update({'state': 'review', 'last_error': 'Preparación iniciada; si se interrumpió, revisar PayPhone antes de repetir.'})
                self.env.cr.commit()
                payment._lock()
            try:
                with self.env.cr.savepoint():
                    if preparing:
                        payment._prepare()
                    elif payment.state == 'confirming' and payment.pending_remote_id:
                        payment._try_confirm()
                    elif payment.state == 'approved' and not payment.reconciled:
                        payment._reconcile()
            except ConfigurationError as error:
                payment._update({'state': 'draft', 'last_error': str(error)})
                _logger.warning('Credenciales rechazadas code=PAYPHONE_CREDENTIALS status=401 correlationId=%s userId=%s', payment.reference, self.env.uid)
            except (ValidationError, AccessError) as error:
                payment._update({'last_error': str(error)})
                _logger.warning('Pago requiere revisión code=PAYPHONE_REVIEW status=409 correlationId=%s userId=%s', payment.reference, self.env.uid)
            self.env.cr.commit()
