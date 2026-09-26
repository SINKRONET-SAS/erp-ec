"""Conector fiscal durable, limitado al ambiente de pruebas."""
import json
import logging
import re
import uuid
from datetime import timedelta
from urllib.parse import urlsplit, quote
import requests
from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.addons.erpec_secrets import secret_store

secret_store.register('erpec.fiscal.connection', 'api_key_encrypted', lambda record: 'fiscal_connector:%d:api_key' % record.id)

_logger = logging.getLogger(__name__)
_INTERNAL = object()


class ProtocolError(Exception):
    def __init__(self, code, retry=False):
        self.code, self.retry = code, retry
        super().__init__(code)


def origin(url):
    value = urlsplit(url or '')
    if value.username or value.password or value.query or value.fragment:
        raise ValidationError('La URL no admite usuario, contraseña, parámetros ni fragmentos.')
    if value.scheme != 'https' and not (value.scheme == 'http' and value.hostname in ('127.0.0.1', 'localhost')):
        raise ValidationError('Usa HTTPS o una dirección HTTP local.')
    if not value.netloc or value.path not in ('', '/'):
        raise ValidationError('Indica únicamente la dirección base del Facturador.')
    return url.rstrip('/')


class Connection(models.Model):
    _name = 'erpec.fiscal.connection'
    _description = 'Conexión fiscal de pruebas'
    _check_company_auto = True

    name = fields.Char(default='Facturador — Pruebas', required=True, string='Nombre')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict', string='Empresa')
    base_url = fields.Char('Dirección del Facturador', required=True)
    organization_ref = fields.Char('Identificador de organización de la suite', required=True)
    empresa_ref = fields.Integer('ID Empresa Facturador', required=True)
    workspace_ref = fields.Integer('ID Workspace Facturador', required=True)
    emission_point_ref = fields.Integer('ID Punto de emisión', required=True)
    # DI25-05.1: la clave NUNCA se guarda en claro. `api_key` es solo de entrada (se lee siempre
    # vacío) y su inverso la cifra con erpec_secrets; solo el servidor la descifra, al llamar al
    # Facturador (_secret_api_key). Mismo patrón que erpec_payphone.provider.token.
    api_key = fields.Char('Clave API de pruebas (se guarda cifrada)', compute='_compute_api_key_input', inverse='_inverse_api_key',
                          groups='base.group_system', copy=False)
    api_key_encrypted = fields.Char('Clave API cifrada', groups='base.group_system', copy=False, readonly=True)
    api_key_loaded = fields.Boolean('Clave API cargada (cifrada)', readonly=True, copy=False)
    verified = fields.Boolean('Credencial verificada', readonly=True, copy=False)
    checked_at = fields.Datetime('Última comprobación', readonly=True, copy=False)
    notice = fields.Text('Siguiente acción', readonly=True, default='Completar la vinculación y verificar una clave API de PRUEBAS con permisos de emisión y consulta. La demo no se vincula al emisor Founder.')
    _sql_constraints = [('one_company', 'unique(company_id)', 'Ya existe una conexión para esta empresa.')]

    @api.constrains('base_url', 'empresa_ref', 'workspace_ref', 'emission_point_ref')
    def _validate_config(self):
        for rec in self:
            origin(rec.base_url)
            if min(rec.empresa_ref, rec.workspace_ref, rec.emission_point_ref) <= 0:
                raise ValidationError('Los identificadores externos deben ser positivos y confirmados por el administrador del emisor.')

    @api.model_create_multi
    def create(self, values_list):
        if any(set(v) & {'verified', 'checked_at', 'notice'} for v in values_list):
            raise ValidationError('El estado lo establece la comprobación del servicio.')
        return super().create(values_list)

    def write(self, values):
        self.check_access('write')
        for rec in self.sorted('id'):
            self.env.cr.execute('SELECT id FROM erpec_fiscal_connection WHERE id=%s FOR UPDATE', [rec.id])
        self.invalidate_recordset()
        if self.env.context.get('_fiscal_internal') is not _INTERNAL:
            if set(values) & {'verified', 'checked_at', 'notice'}:
                raise ValidationError('El estado de conexión no se modifica manualmente.')
            locked = {'company_id', 'base_url', 'organization_ref', 'empresa_ref', 'workspace_ref', 'emission_point_ref'}
            if set(values) & locked and self.env['erpec.fiscal.job'].search_count([('connection_id', 'in', self.ids)]):
                raise ValidationError('La conexión tiene documentos vinculados; no puede reasignarse a otro destino.')
            values = dict(values, verified=False)
        return super().write(values)

    def _compute_api_key_input(self):
        self.api_key = False

    def _inverse_api_key(self):
        for record in self:
            value = (record.api_key or '').strip()
            if value:
                models.Model.write(record.sudo(), {
                    'api_key_encrypted': secret_store.encrypt(value.encode('utf-8'), 'fiscal_connector:%d:api_key' % record.id), 'api_key_loaded': True})

    def _secret_api_key(self):
        self.ensure_one()
        record = self.sudo()
        if not record.api_key_encrypted:
            return False
        try:
            return secret_store.decrypt(record.api_key_encrypted, 'fiscal_connector:%d:api_key' % record.id).decode('utf-8')
        except secret_store.SecretError as error:
            raise ValidationError(str(error)) from error

    def _request(self, method, path, correlation, payload=None, key=None):
        self.ensure_one()
        token = self._secret_api_key()
        if not token or not token.startswith('sk_test_'):
            raise ProtocolError('CLAVE_PRUEBAS_REQUERIDA')
        headers = {'Authorization': 'Bearer ' + token, 'X-Correlation-Id': correlation, 'Accept': 'application/json'}
        if key:
            headers['Idempotency-Key'] = key
        try:
            response = requests.request(method, origin(self.base_url) + path, json=payload, headers=headers, timeout=(5, 20), allow_redirects=False)
        except requests.RequestException:
            raise ProtocolError('CONEXION_NO_CONFIRMADA', retry=True) from None
        if response.status_code == 404 and method == 'GET' and '/invoices/' in path:
            return None
        if response.status_code not in (200, 201, 202):
            raise ProtocolError('HTTP_' + str(response.status_code), retry=response.status_code == 429 or response.status_code >= 500)
        try:
            body = response.json()
        except ValueError:
            raise ProtocolError('RESPUESTA_NO_JSON', retry=True) from None
        if not isinstance(body, dict) or body.get('success') is not True or not isinstance(body.get('data'), dict):
            raise ProtocolError('CONTRATO_INVALIDO')
        return body['data']

    def _capabilities(self, correlation):
        data = self._request('GET', '/api/integrations/v1/capabilities', correlation)
        identity = data.get('identity') or {}
        if data.get('contractVersion') != '1.0' or data.get('source') != 'CUSTOM':
            raise ProtocolError('VERSION_U_ORIGEN_INCOMPATIBLE')
        if data.get('ambiente') != 'PRUEBAS' or identity.get('empresaAmbiente') != '1' or identity.get('ownerAmbiente') != '1':
            raise ProtocolError('AMBIENTE_NO_ES_PRUEBAS')
        if identity.get('empresaId') != self.empresa_ref or identity.get('workspaceId') != self.workspace_ref:
            raise ProtocolError('IDENTIDAD_EXTERNA_NO_COINCIDE')
        if not {'emit:factura', 'read:comprobantes'}.issubset(set(data.get('scopes') or [])):
            raise ProtocolError('PERMISOS_API_INSUFICIENTES')
        return data

    def action_verify(self):
        self.ensure_one(); self.check_access('write')
        correlation = uuid.uuid4().hex
        try:
            self._capabilities(correlation)
            values = {'verified': True, 'notice': 'Identidad y ambiente PRUEBAS verificados. El servicio aún debe validar firma y punto de emisión al procesar cada comprobante.'}
        except ProtocolError as exc:
            values = {'verified': False, 'notice': 'Revisar configuración: ' + exc.code + '. Correlación: ' + correlation}
            _logger.warning('Verificación fiscal code=%s statusCode=422 correlationId=%s userId=%s', exc.code, correlation, self.env.uid)
        self.with_context(_fiscal_internal=_INTERNAL).write(dict(values, checked_at=fields.Datetime.now()))
        return True


class Job(models.Model):
    _name = 'erpec.fiscal.job'
    _description = 'Bandeja fiscal de pruebas'
    _rec_name = 'external_reference'
    _order = 'id desc'
    _check_company_auto = True

    move_id = fields.Many2one('account.move', string='Factura', required=True, check_company=True, ondelete='restrict')
    company_id = fields.Many2one(related='move_id.company_id', store=True, index=True, string='Empresa')
    connection_id = fields.Many2one('erpec.fiscal.connection', string='Conexión', required=True, check_company=True, ondelete='restrict')
    external_reference = fields.Char('Referencia externa', readonly=True, required=True, index=True)
    correlation_id = fields.Char('Correlación', readonly=True, required=True)
    payload = fields.Json('Solicitud conservada', readonly=True)
    state = fields.Selection([('queued','En cola'),('waiting','Esperando resultado'),('retry','Reintento programado'),('blocked','Revisión requerida'),('authorized','Autorizada en pruebas'),('rejected','Rechazada')], default='queued', readonly=True, string='Estado')
    attempts = fields.Integer('Intentos', readonly=True)
    next_attempt = fields.Datetime('Próximo intento', readonly=True)
    message = fields.Text('Estado y siguiente acción', readonly=True, default='Solicitud guardada. Procesar la bandeja para enviarla al Facturador de pruebas.')
    remote_status = fields.Char('Estado Facturador', readonly=True)
    remote_id = fields.Char('ID Factura Facturador', readonly=True)
    number = fields.Char('Número fiscal', readonly=True)
    access_key = fields.Char('Clave de acceso', readonly=True)
    xml_url = fields.Char('XML', readonly=True)
    ride_url = fields.Char('RIDE', readonly=True)
    _sql_constraints = [('one_invoice','unique(move_id)','La factura ya tiene una solicitud fiscal.'),('one_reference','unique(external_reference)','La referencia fiscal debe ser única.')]

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_fiscal_internal') is not _INTERNAL:
            raise ValidationError('Prepara el envío desde la factura contabilizada.')
        moves = self.env['account.move'].browse([v['move_id'] for v in values_list if v.get('move_id')])
        moves._lock_fiscal_source()
        if moves._has_native_fiscal_emissions():
            raise ValidationError('El comprobante ya tiene una emisión nativa; conserva esa autoridad.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_fiscal_internal') is not _INTERNAL:
            raise ValidationError('La bandeja fiscal se actualiza mediante sus acciones.')
        return super().write(values)

    def unlink(self):
        raise ValidationError('Conserva la solicitud fiscal para conciliación y auditoría.')

    def _save(self, **values):
        return self.with_context(_fiscal_internal=_INTERNAL).write(values)

    def _apply(self, data):
        if data.get('contractVersion') != '1.0' or data.get('source') != 'CUSTOM' or data.get('externalReference') != self.external_reference or data.get('idempotencyKey') != self.external_reference:
            raise ProtocolError('RESPUESTA_NO_CORRESPONDE_A_SOLICITUD')
        status = data.get('estado')
        states = {'received':'waiting','processing':'waiting','invoice_requested':'waiting','blocked':'blocked','failed':'blocked','invoice_authorized':'authorized','invoice_rejected':'rejected'}
        if status not in states:
            raise ProtocolError('ESTADO_DESCONOCIDO')
        if self.state in ('authorized','rejected'):
            if states[status] != self.state:
                raise ProtocolError('RESULTADO_FUERA_DE_ORDEN')
            return
        if self.remote_id and data.get('facturaId') and str(data['facturaId']) != self.remote_id:
            raise ProtocolError('IDENTIFICADOR_FISCAL_CAMBIO')
        if status == 'invoice_authorized':
            key = data.get('claveAcceso') or ''
            if not re.fullmatch(r'\d{49}', key) or key[23] != '1' or data.get('rawStatus') != 'AUTORIZADA' or not data.get('facturaId') or not re.fullmatch(r'\d{3}-\d{3}-\d{9}', data.get('numero') or ''):
                raise ProtocolError('AUTORIZACION_INCOMPLETA_O_NO_PRUEBAS')
        urls = {}
        for remote, local in [('xmlUrl','xml_url'),('rideUrl','ride_url')]:
            url = data.get(remote)
            if url:
                parts = urlsplit(url)
                base = urlsplit(origin(self.connection_id.base_url))
                if parts.scheme != base.scheme or parts.netloc != base.netloc or parts.username or parts.password:
                    raise ProtocolError('ENLACE_DOCUMENTAL_NO_CONFIABLE')
            urls[local] = url or False
        message = {'authorized':'Autorizada en PRUEBAS.','rejected':'Rechazada: revisar el comprobante en Facturador.','blocked':'El Facturador requiere revisión de firma, datos, permisos o punto de emisión.','waiting':'Solicitud recibida; todavía no está autorizada.'}[states[status]]
        if not data.get('xmlUrl') or not data.get('rideUrl'):
            message += ' El servicio no entregó ambos enlaces XML/RIDE.'
        self._save(state=states[status], remote_status=status, remote_id=str(data.get('facturaId') or self.remote_id or ''), number=data.get('numero') or False, access_key=data.get('claveAcceso') or False, message=message, **urls)

    def action_process(self):
        for job in self:
            job.check_access('write')
            self.env.cr.execute('SELECT id FROM erpec_fiscal_job WHERE id=%s FOR UPDATE', [job.id])
            job.invalidate_recordset()
            if job.state in ('authorized','rejected'):
                continue
            if job.next_attempt and job.next_attempt > fields.Datetime.now():
                raise UserError('Espera al próximo intento indicado para no saturar el servicio.')
            if job.attempts >= 5:
                job._save(state='blocked', message='Se agotaron cinco intentos. Revisar y habilitar un nuevo ciclo de consulta.')
                continue
            try:
                job._save(attempts=job.attempts + 1)
                self.env.cr.execute('SELECT id FROM erpec_fiscal_connection WHERE id=%s FOR UPDATE', [job.connection_id.id])
                job.connection_id.invalidate_recordset()
                job.connection_id._capabilities(job.correlation_id)
                data = job.connection_id._request('GET', '/api/integrations/v1/invoices/' + quote(job.external_reference, safe=''), job.correlation_id)
                if data is None or data.get('estado') == 'blocked':
                    data = job.connection_id._request('POST', '/api/integrations/v1/invoices', job.correlation_id, payload=job.payload, key=job.external_reference)
                job._apply(data)
                job._save(next_attempt=fields.Datetime.now() + timedelta(seconds=60) if job.state == 'waiting' else False)
            except ProtocolError as exc:
                job._save(state='retry' if exc.retry else 'blocked', message=exc.code + '. Correlación: ' + job.correlation_id, next_attempt=fields.Datetime.now() + timedelta(seconds=60 * max(1,job.attempts)) if exc.retry else False)
                _logger.warning('Operación fiscal code=%s statusCode=422 correlationId=%s userId=%s', exc.code, job.correlation_id, self.env.uid)
        return True

    def action_resume(self):
        self.check_access('write')
        for job in self:
            self.env.cr.execute('SELECT id FROM erpec_fiscal_job WHERE id=%s FOR UPDATE', [job.id])
            job.invalidate_recordset()
            if job.state != 'blocked':
                raise UserError('Solo puede reabrirse una solicitud que requiere revisión.')
            job._save(attempts=0, state='queued', next_attempt=False, message='Revisión solicitada; se conserva la misma referencia y contenido.')
        return True

    @api.model
    def _cron_process(self):
        jobs = self.search([('state','in',['queued','waiting','retry']), '|', ('next_attempt','=',False), ('next_attempt','<=',fields.Datetime.now())], limit=10)
        for job in jobs:
            job.action_process()


class Move(models.Model):
    _inherit = 'account.move'

    ec_fiscal_job_ids = fields.One2many('erpec.fiscal.job','move_id', string='Envíos al Facturador', copy=False)
    ec_fiscal_payment_code = fields.Char('Código SRI de forma de pago', copy=False)

    def action_queue_fiscal(self):
        self.ensure_one(); self.check_access('write')
        self._lock_fiscal_source()
        self.invalidate_recordset()
        if self._has_native_fiscal_emissions():
            raise ValidationError('El comprobante ya tiene una emisión nativa; conserva esa autoridad.')
        existing = self.env['erpec.fiscal.job'].search([('move_id','=',self.id)])
        if existing:
            return {'type':'ir.actions.act_window','res_model':'erpec.fiscal.job','res_id':existing.id,'view_mode':'form'}
        if self.state != 'posted' or self.move_type != 'out_invoice' or self.currency_id.name != 'USD' or self.company_id.country_id.code != 'EC':
            raise ValidationError('Se requiere una factura de venta contabilizada en USD de una empresa de Ecuador.')
        connection = self.env['erpec.fiscal.connection'].search([('company_id','=',self.company_id.id)], limit=1)
        if connection:
            self.env.cr.execute('SELECT id FROM erpec_fiscal_connection WHERE id=%s FOR UPDATE', [connection.id])
            connection.invalidate_recordset()
        if not connection or not connection.verified:
            raise ValidationError('Configura y verifica primero la conexión fiscal de pruebas de esta empresa.')
        partner = self.partner_id.commercial_partner_id
        if not partner.vat or not partner.street or not partner.name or not re.fullmatch(r'\d{2}', self.ec_fiscal_payment_code or ''):
            raise ValidationError('Completa identificación y dirección del cliente, y código SRI de forma de pago verificado.')
        items = []
        for line in self.invoice_line_ids.filtered(lambda rec: rec.display_type == 'product'):
            taxes = line.tax_ids
            if len(taxes) != 1 or taxes.amount_type != 'percent' or taxes.price_include or taxes.include_base_amount or taxes.tax_group_id.l10n_ec_type not in ('vat05','vat08','vat12','vat13','vat14','vat15','zero_vat'):
                raise ValidationError('Este contrato admite un único IVA porcentual explícito, sin precio incluido. Exentos, no objeto, ICE y otros conceptos requieren ampliar el contrato fiscal.')
            if line.quantity <= 0 or line.price_unit < 0 or not 0 <= line.discount <= 100 or line.currency_id.compare_amounts(line.price_subtotal, line.quantity*line.price_unit*(1-line.discount/100)):
                raise ValidationError('Revisa cantidades, precios y descuentos antes de preparar el comprobante.')
            items.append({'code':line.product_id.default_code or str(line.id),'description':line.name,'quantity':line.quantity,'unitPrice':line.price_unit,'discount':line.price_unit*line.discount/100,'vatRate':taxes.amount})
        if not items or self.amount_total <= 0:
            raise ValidationError('La factura requiere líneas e importe positivo.')
        reference = 'odoo-' + uuid.uuid4().hex
        payload = {'externalReference':reference,'customer':{'identification':partner.vat,'legalName':partner.name,'address':partner.street,'email':partner.email or ''},'invoice':{'items':items,'payments':[{'method':self.ec_fiscal_payment_code,'amount':self.amount_total}],'metadata':{'emissionPointId':connection.emission_point_ref,'tenantId':connection.organization_ref}}}
        job = self.env['erpec.fiscal.job'].with_context(_fiscal_internal=_INTERNAL).create({'move_id':self.id,'connection_id':connection.id,'external_reference':reference,'correlation_id':uuid.uuid4().hex,'payload':payload})
        return {'type':'ir.actions.act_window','res_model':'erpec.fiscal.job','res_id':job.id,'view_mode':'form'}

    def _lock_fiscal_source(self):
        """Serializa autoridades y cambios incluso bajo REPEATABLE READ de Odoo."""
        if not self:
            _logger.debug('Sin comprobantes que bloquear code=FISCAL_CONJUNTO_VACIO statusCode=200 correlationId=sin-documento userId=%s', self.env.uid)
            return
        self.check_access('write')
        self.flush_recordset(['write_date'])
        for move in self.sorted('id'):
            # La versión MVCC obliga a reintentar una lectura concurrente antigua.
            self.env.cr.execute('UPDATE account_move SET write_date=write_date WHERE id=%s', [move.id])
        links = [name for name in ('ec_fiscal_job_ids', 'ec_fiscal_emission_ids') if name in self._fields]
        self.invalidate_recordset(links, flush=False)

    def _has_native_fiscal_emissions(self):
        """Extensión para la autoridad nativa, sin exigir su instalación."""
        return False

    def _check_fiscal_mutation(self):
        self._lock_fiscal_source()
        if self._has_fiscal_jobs():
            raise ValidationError('El comprobante conserva una emisión fiscal; sus datos y sustentos no se modifican. Corrige con una nota o procedimiento fiscal.')

    def _has_fiscal_jobs(self):
        self.check_access('read')
        # Consulta interna limitada al vínculo; no concede acceso a la bandeja fiscal.
        return bool(self.sudo().ec_fiscal_job_ids) or self._has_native_fiscal_emissions()

    def button_draft(self):
        self._lock_fiscal_source()
        if self._has_fiscal_jobs():
            raise ValidationError('La factura tiene una solicitud fiscal persistente. Revisa su resultado antes de cualquier corrección fiscal.')
        return super().button_draft()

    def button_cancel(self):
        self._lock_fiscal_source()
        if self._has_fiscal_jobs():
            raise ValidationError('La cancelación contable no anula una solicitud fiscal. Revisa el documento en Facturador.')
        return super().button_cancel()


    def write(self, values):
        if set(values) & {'partner_id','company_id','currency_id','move_type','invoice_line_ids','line_ids','invoice_date','ec_fiscal_payment_code','state','name','journal_id','l10n_latam_document_number','l10n_latam_document_type_id','ref','narration','ec_sri_reimbursement_ids'}:
            self._lock_fiscal_source()
            if self._has_fiscal_jobs():
                raise ValidationError('El envío fiscal conserva el contenido de esta factura. No cambies sus datos después de prepararlo.')
        return super().write(values)


class MoveLine(models.Model):
    _inherit = 'account.move.line'

    def write(self, values):
        if set(values) & {'move_id','name','product_id','quantity','price_unit','discount','tax_ids','currency_id','balance','debit','credit','amount_currency','display_type'}:
            moves = self.move_id | self.env['account.move'].browse(values.get('move_id') or [])
            moves._check_fiscal_mutation()
        return super().write(values)

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if values.get('move_id'):
                self.env['account.move'].browse(values['move_id'])._check_fiscal_mutation()
        return super().create(values_list)

    def unlink(self):
        self.move_id._check_fiscal_mutation()
        return super().unlink()


class Workspace(models.Model):
    _inherit = 'erpec.workspace'

    def _compute_company_readiness(self):
        super()._compute_company_readiness()
        for workspace in self:
            workspace.fiscal_scope = 'Conector de pruebas instalado (Facturador externo; es excluyente con la emisión nativa para un mismo comprobante). Pendiente en este canal: verificar la conexión de la empresa y completar el ensayo con un punto de emisión autorizado. Antes de producción, registrar y emitir el RUC del proveedor del sistema cuando corresponda. Consulta cada solicitud en la bandeja; instalar el conector no autoriza comprobantes.'
