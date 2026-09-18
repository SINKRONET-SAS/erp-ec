"""Emisión nativa real: firma XAdES + transmisión SOAP directa al SRI (ambiente PRUEBAS).
Segunda autoridad de emisión, independiente de erpec_fiscal_connector (que delega en un
servicio Facturador externo) — gobernada por la misma regla "una autoridad por comprobante"
que ya aplica en erpec_fiscal_native.models. Ver docs/PLAN_HAIKY_FACTURACION_NATIVA.md.

`_gather_native_data()` duplica intencionalmente una porción pequeña de la lógica de
`erpec_fiscal_native.models.Move.action_native_preview` (validación de líneas/IVA y armado del
diccionario para engine.generate()): ese archivo está en edición por otra sesión en paralelo al
escribir este incremento, así que no se pudo extraer a una función compartida. Consolidar en un
incremento posterior cuando el archivo esté libre.
"""
import base64
import re
import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.erpec_fiscal_native import xades
from odoo.addons.erpec_fiscal_native.engine import generate
from odoo.addons.erpec_fiscal_native import notacredito_engine, notadebito_engine

from . import ride as ride_module
from . import sri_client

NATIVE_MOVE_TYPES = ('out_invoice', 'out_refund')

_INTERNAL = object()
MAX_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 60
POLL_DELAY_SECONDS = 30

# Autoservicio de carga del .p12 (adaptado de sinkroniq-mobile, backend/src/services/certificados/
# certificateLifecycleService.js: allowlist de CAs conocidas para el SRI, tope de tamaño de
# archivo y límite de intentos de verificación). Odoo no tiene un servicio de firma separado ni
# Redis en este proyecto, así que el límite de intentos se guarda en el propio registro en vez de
# un contador externo, y la "vista previa" se resuelve con un @api.onchange (corre en el cliente
# antes de guardar) en vez de un endpoint aparte.
MAX_P12_BYTES = 262144
MAX_VERIFY_ATTEMPTS = 5
VERIFY_WINDOW_MINUTES = 15
TRUSTED_CA_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    r'security\s*data', r'banco\s*central\s*del?\s*ecuador', r'\bbce\b', r'\banf\s*ac\b',
    r'uanataca', r'datil', r'consejo\s*de\s*la\s*judicatura',
)]
SIGNATURE_PROBE_XML = (
    b'<factura id="comprobante" version="2.1.0"><infoTributaria><ambiente>1</ambiente>'
    b'<tipoEmision>1</tipoEmision><razonSocial>PRUEBA FIRMA ELECTRONICA</razonSocial>'
    b'<ruc>%(ruc)s</ruc><claveAcceso>' + b'0' * 49 + b'</claveAcceso><codDoc>01</codDoc>'
    b'<estab>001</estab><ptoEmi>001</ptoEmi><secuencial>000000000</secuencial>'
    b'<dirMatriz>PRUEBA</dirMatriz></infoTributaria></factura>'
)


class Certificate(models.Model):
    _name = 'erpec.fiscal.certificate'
    _description = 'Certificado de firma electrónica (SRI)'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict')
    # Autoservicio: la empresa (cliente) del propio inquilino puede cargar y reemplazar su
    # certificado -- ampliado de solo base.group_system a incluir account.group_account_user.
    # Cambio de postura deliberado: mismo nivel de protección de reposo que la credencial de
    # PayPhone (sin cifrado adicional, solo permisos), pero ahora el grupo con acceso incluye al
    # cliente dueño de la empresa, no solo administración interna -- es el requisito explícito de
    # este incremento (autoservicio real para clientes, modelo multi-tenant de OP08).
    p12_file = fields.Binary('Archivo .p12', groups='base.group_system,account.group_account_user', attachment=False)
    p12_password = fields.Char('Contraseña del .p12', groups='base.group_system,account.group_account_user')
    verified = fields.Boolean('Verificado', readonly=True, copy=False)
    subject_summary = fields.Char('Titular (según certificado)', readonly=True, copy=False)
    issuer_summary = fields.Char('Entidad certificadora', readonly=True, copy=False)
    issuer_trusted = fields.Boolean('Entidad certificadora reconocida', readonly=True, copy=False)
    not_valid_before = fields.Datetime('Vigente desde', readonly=True, copy=False)
    not_valid_after = fields.Datetime('Vigente hasta', readonly=True, copy=False)
    checked_at = fields.Datetime('Última comprobación', readonly=True, copy=False)
    signature_tested = fields.Boolean('Firma de prueba realizada', readonly=True, copy=False)
    signature_tested_at = fields.Datetime('Última prueba de firma', readonly=True, copy=False)
    verify_attempts = fields.Integer('Intentos de verificación', readonly=True, copy=False, default=0)
    verify_window_start = fields.Datetime('Inicio de ventana de intentos', readonly=True, copy=False)
    notice = fields.Text('Estado', readonly=True, default='Cargar el archivo .p12 y su contraseña, luego verificar.')
    _sql_constraints = [('one_company', 'unique(company_id)', 'Ya existe un certificado para esta empresa.')]

    @api.constrains('p12_file')
    def _check_p12_size(self):
        for record in self:
            if record.p12_file and len(base64.b64decode(record.p12_file)) > MAX_P12_BYTES:
                raise ValidationError('El archivo .p12 supera el tamaño máximo permitido (%d KB).' % (MAX_P12_BYTES // 1024))

    @api.onchange('p12_file', 'p12_password')
    def _onchange_p12_preview(self):
        """Vista previa sin persistir: valida en memoria al elegir el archivo/clave, antes de
        guardar -- equivalente al endpoint separado de "preview" de sinkroniq-mobile, pero
        resuelto con el ciclo de onchange propio de Odoo (no llega a la base de datos)."""
        if not self.p12_file or not self.p12_password:
            return
        try:
            p12_bytes = base64.b64decode(self.p12_file)
        except (TypeError, ValueError):
            self.notice = 'El archivo .p12 no es válido.'
            return
        ruc = self.company_id.vat or ''
        try:
            _key, cert, _chain = xades.credentials(p12_bytes, self.p12_password.encode('utf-8'), ruc)
            trusted = self._issuer_trusted(cert.issuer.rfc4514_string())
            preview = 'Vista previa: certificado válido para %s, vigente hasta %s.' % (
                cert.subject.rfc4514_string(), cert.not_valid_after_utc.date().isoformat())
            if not trusted:
                preview += ' Advertencia: la entidad certificadora no está en el catálogo local de CAs reconocidas por el SRI; verifícala manualmente.'
            self.notice = preview
        except ValueError as error:
            self.notice = 'Vista previa: ' + str(error)

    @staticmethod
    def _issuer_trusted(issuer_text):
        return any(pattern.search(issuer_text or '') for pattern in TRUSTED_CA_PATTERNS)

    def _check_verify_rate(self):
        self.ensure_one()
        now = fields.Datetime.now()
        window_start = self.verify_window_start
        if not window_start or now - window_start > timedelta(minutes=VERIFY_WINDOW_MINUTES):
            self.write({'verify_attempts': 0, 'verify_window_start': now})
            return
        if self.verify_attempts >= MAX_VERIFY_ATTEMPTS:
            raise UserError('Demasiados intentos de verificación. Espera %d minutos e inténtalo de nuevo.' % VERIFY_WINDOW_MINUTES)

    def action_verify(self):
        self.ensure_one()
        self.check_access('write')
        self._check_verify_rate()
        p12_bytes = base64.b64decode(self.sudo().p12_file or b'')
        password = (self.sudo().p12_password or '').encode('utf-8')
        ruc = self.company_id.vat or ''
        try:
            _key, cert, _chain = xades.credentials(p12_bytes, password, ruc)
            issuer_text = cert.issuer.rfc4514_string()
            trusted = self._issuer_trusted(issuer_text)
            notice = 'Certificado verificado: firma RSA válida, vigente, y coincide con el RUC de la empresa.'
            if not trusted:
                notice += ' Advertencia: la entidad certificadora no está en el catálogo local de CAs reconocidas por el SRI; verifícala manualmente antes de usarla en producción.'
            values = {
                'verified': True,
                'subject_summary': cert.subject.rfc4514_string(),
                'issuer_summary': issuer_text,
                'issuer_trusted': trusted,
                'not_valid_before': cert.not_valid_before_utc.replace(tzinfo=None),
                'not_valid_after': cert.not_valid_after_utc.replace(tzinfo=None),
                'notice': notice,
                'signature_tested': False,
                'signature_tested_at': False,
            }
        except ValueError as error:
            values = {'verified': False, 'notice': 'No se pudo verificar: ' + str(error)}
        self.write(dict(values, checked_at=fields.Datetime.now(), verify_attempts=self.verify_attempts + 1))
        return True

    def action_test_signature(self):
        """Firma un XML sintético mínimo (no un comprobante real ni un envío al SRI) para
        confirmar que el certificado puede firmar de verdad -- credentials() solo confirma que el
        .p12 abre y coincide con el RUC, no que xades.sign() completa sin error sobre un documento
        real. Mismo objetivo que probarFirma()/probeCertificateSignature() de sinkroniq-mobile,
        sin necesitar un servicio de firma aparte ni tocar la red."""
        self.ensure_one()
        self.check_access('write')
        if not self.verified:
            raise UserError('Verifica el certificado antes de probar la firma.')
        p12_bytes = base64.b64decode(self.sudo().p12_file or b'')
        password = (self.sudo().p12_password or '').encode('utf-8')
        ruc = self.company_id.vat or ''
        probe_xml = SIGNATURE_PROBE_XML % {b'ruc': ruc.encode('utf-8')}
        try:
            signed = xades.sign(probe_xml, p12_bytes, password, ruc)
            xades.verify(signed, xades.credentials(p12_bytes, password, ruc)[1])
            self.write({
                'signature_tested': True,
                'signature_tested_at': fields.Datetime.now(),
                'notice': 'Certificado verificado y firma de prueba exitosa: el certificado puede firmar comprobantes.',
            })
        except ValueError as error:
            self.write({'signature_tested': False, 'notice': 'La prueba de firma falló: ' + str(error)})
        return True


class Emission(models.Model):
    _name = 'erpec.fiscal.emission'
    _description = 'Emisión nativa (firma XAdES + transmisión SOAP directa al SRI)'
    _rec_name = 'access_key'
    _order = 'id desc'
    _check_company_auto = True

    move_id = fields.Many2one('account.move', string='Comprobante', required=True, check_company=True, ondelete='restrict')
    company_id = fields.Many2one(related='move_id.company_id', store=True, index=True)
    ambiente = fields.Selection([('1', 'Pruebas'), ('2', 'Producción')], default='1', required=True, readonly=True)
    access_key = fields.Char('Clave de acceso', readonly=True)
    xml_unsigned = fields.Binary('XML sin firmar', readonly=True, attachment=False)
    xml_signed = fields.Binary('XML firmado', readonly=True, attachment=False)
    xml_authorized = fields.Binary('XML autorizado por el SRI', readonly=True, attachment=False)
    ride_pdf = fields.Binary('RIDE', readonly=True, attachment=False)
    authorization_number = fields.Char('Número de autorización SRI', readonly=True)
    authorization_date = fields.Char('Fecha de autorización SRI', readonly=True)
    state = fields.Selection([
        ('draft', 'Preparando'),
        ('signed', 'Firmada'),
        ('sent', 'Enviada a Recepción'),
        ('waiting', 'Esperando autorización'),
        ('authorized', 'Autorizada'),
        ('rejected', 'No autorizada'),
        ('returned', 'Devuelta en recepción'),
        ('blocked', 'Revisión requerida'),
    ], default='draft', required=True, readonly=True)
    attempts = fields.Integer('Intentos', readonly=True)
    next_attempt = fields.Datetime('Próximo intento', readonly=True)
    message = fields.Text('Estado y siguiente acción', readonly=True, default='Solicitud preparada. Procesar la cola para firmar y transmitir.')
    _sql_constraints = [('one_invoice', 'unique(move_id)', 'El comprobante ya tiene una emisión nativa.')]

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_fiscal_sri_internal') is not _INTERNAL:
            raise ValidationError('Prepara la emisión desde el comprobante contabilizado.')
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('_fiscal_sri_internal') is not _INTERNAL:
            raise ValidationError('La emisión nativa se actualiza mediante sus acciones.')
        return super().write(values)

    def unlink(self):
        raise ValidationError('Conserva la emisión nativa para conciliación y auditoría.')

    def _save(self, **values):
        return self.with_context(_fiscal_sri_internal=_INTERNAL).write(values)

    def action_process(self):
        for emission in self:
            emission.check_access('write')
            self.env.cr.execute('SELECT id FROM erpec_fiscal_emission WHERE id=%s FOR UPDATE', [emission.id])
            emission.invalidate_recordset()
            if emission.state in ('authorized', 'rejected'):
                continue
            if emission.next_attempt and emission.next_attempt > fields.Datetime.now():
                raise UserError('Espera al próximo intento indicado para no saturar el servicio.')
            if emission.attempts >= MAX_ATTEMPTS:
                emission._save(state='blocked', message='Se agotaron %d intentos. Revisar y reabrir explícitamente.' % MAX_ATTEMPTS)
                continue
            try:
                emission._save(attempts=emission.attempts + 1)
                if emission.state in ('draft', 'signed'):
                    emission._transmit()
                elif emission.state in ('sent', 'waiting'):
                    emission._poll()
            except sri_client.SriError as error:
                delay = RETRY_DELAY_SECONDS * max(1, emission.attempts)
                emission._save(
                    state='blocked' if not error.retry else emission.state,
                    message=error.code,
                    next_attempt=fields.Datetime.now() + timedelta(seconds=delay) if error.retry else False,
                )
        return True

    def _transmit(self):
        self.ensure_one()
        xml_signed = base64.b64decode(self.xml_signed)
        estado, mensajes = sri_client.enviar_recepcion(xml_signed, ambiente=self.ambiente)
        if estado == 'DEVUELTA':
            self._save(state='returned', message='DEVUELTA en Recepción: ' + str(mensajes))
            return
        self._save(state='waiting', message='RECIBIDA; esperando autorización.',
                    next_attempt=fields.Datetime.now() + timedelta(seconds=POLL_DELAY_SECONDS))

    @api.model
    def _cron_process(self):
        emissions = self.search([('state', 'not in', ['authorized', 'rejected']),
                                  '|', ('next_attempt', '=', False), ('next_attempt', '<=', fields.Datetime.now())], limit=10)
        for emission in emissions:
            emission.action_process()

    def _poll(self):
        self.ensure_one()
        estado, autorizacion, mensajes = sri_client.consultar_autorizacion(self.access_key, ambiente=self.ambiente)
        if estado in ('PENDIENTE', 'EN PROCESO'):
            self._save(message='Aún sin autorización (%s).' % estado,
                        next_attempt=fields.Datetime.now() + timedelta(seconds=POLL_DELAY_SECONDS))
            return
        if estado == 'NO AUTORIZADO':
            self._save(state='rejected', message='NO AUTORIZADO: ' + str(mensajes))
            return
        # El tipo de comprobante (codDoc) va en la clave de acceso (posiciones 9-10, índice
        # 8:10) -- fuente única de verdad, no se guarda por separado ni se infiere del move_id.
        doc_type = self.access_key[8:10]
        builder = {'04': ride_module.build_ride_notacredito, '05': ride_module.build_ride_notadebito}.get(doc_type, ride_module.build_ride)
        ride_pdf = builder(autorizacion['comprobante'], autorizacion['numero'], autorizacion['fecha'])
        self._save(state='authorized', xml_authorized=base64.b64encode(autorizacion['comprobante']), ride_pdf=base64.b64encode(ride_pdf),
                    authorization_number=autorizacion['numero'], authorization_date=autorizacion['fecha'],
                    message='Autorizada por el SRI.')


class Move(models.Model):
    _inherit = 'account.move'

    ec_fiscal_emission_ids = fields.One2many('erpec.fiscal.emission', 'move_id', string='Emisiones nativas SRI', copy=False)

    def _gather_native_common(self):
        """Datos compartidos entre factura y nota de crédito: identificación del emisor/
        comprador y líneas con impuesto. Duplicado intencional de la validación/armado de
        datos de erpec_fiscal_native.models.Move.action_native_preview — ver docstring del
        módulo."""
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id.commercial_partner_id
        identification = ('04' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_ruc')
                          else '05' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_dni') else '')
        items = []
        for line in self.invoice_line_ids.filtered(lambda row: row.display_type == 'product'):
            tax = line.tax_ids
            if (len(tax) != 1 or tax.amount_type != 'percent' or tax.price_include or tax.include_base_amount
                    or (tax.tax_group_id.l10n_ec_type, tax.amount) not in [('zero_vat', 0), ('vat15', 15)]):
                raise ValidationError('Revisar IVA: se admite una tarifa 0 o 15 por línea, sin impuestos incluidos ni compuestos.')
            items.append({'code': line.product_id.default_code or str(line.id), 'description': line.name,
                          'quantity': line.quantity, 'unit': line.price_unit, 'discount': line.discount,
                          'rate': tax.amount, 'subtotal': line.price_subtotal, 'tax': line.price_total - line.price_subtotal})
        return {'date': str(self.invoice_date), 'number': self.l10n_latam_document_number, 'issuer_vat': company.vat,
                'issuer_name': company.name, 'issuer_address': company.street, 'buyer_type': identification,
                'buyer_vat': partner.vat, 'buyer_name': partner.name, 'buyer_address': partner.street,
                'accounting': company.ec_native_accounting, 'total': self.amount_total, 'items': items}

    def _gather_native_data(self):
        data = self._gather_native_common()
        data['payment'] = self.ec_fiscal_payment_code
        return data

    def _gather_native_credit_note_data(self):
        self.ensure_one()
        original = self.reversed_entry_id
        if not original or original.move_type != 'out_invoice':
            raise ValidationError('La nota de crédito debe generarse desde "Añadir nota de crédito" sobre la factura que modifica.')
        if not original.l10n_latam_document_number or original.l10n_latam_document_type_id.code != '01':
            raise ValidationError('La factura modificada debe tener secuencial asignado y ser de tipo Factura (código 01).')
        data = self._gather_native_common()
        data['modified_type'] = '01'
        data['modified_number'] = original.l10n_latam_document_number
        data['modified_date'] = str(original.invoice_date)
        data['reason'] = (self.ref or self.narration or 'Nota de crédito').strip()[:300]
        return data

    def _gather_native_debit_note_data(self):
        self.ensure_one()
        original = self.debit_origin_id
        if not original or original.move_type != 'out_invoice':
            raise ValidationError('La nota de débito debe generarse desde "Añadir nota de débito" sobre la factura que modifica.')
        if not original.l10n_latam_document_number or original.l10n_latam_document_type_id.code != '01':
            raise ValidationError('La factura modificada debe tener secuencial asignado y ser de tipo Factura (código 01).')
        if self.l10n_latam_document_type_id.code != '05':
            raise ValidationError('La nota de débito debe tener el tipo documental Nota de débito (código 05).')
        data = self._gather_native_common()
        data['modified_type'] = '01'
        data['modified_number'] = original.l10n_latam_document_number
        data['modified_date'] = str(original.invoice_date)
        data['payment'] = self.ec_fiscal_payment_code
        return data

    def action_native_emit(self):
        self.ensure_one()
        self.check_access('write')
        if self.state != 'posted' or self.move_type not in NATIVE_MOVE_TYPES or self.currency_id.name != 'USD' or self.company_id.country_id.code != 'EC':
            raise ValidationError('Se requiere una factura, nota de crédito o nota de débito de venta contabilizada en USD de una empresa de Ecuador.')
        if self.ec_fiscal_job_ids:
            raise ValidationError('Este comprobante ya está asignado al Facturador externo; conserva su autoridad y trazabilidad.')
        if self.ec_fiscal_emission_ids:
            return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission',
                    'res_id': self.ec_fiscal_emission_ids[0].id, 'view_mode': 'form'}
        certificate = self.env['erpec.fiscal.certificate'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not certificate or not certificate.verified:
            raise ValidationError('Configura y verifica primero el certificado de firma electrónica de esta empresa.')
        is_credit_note = self.move_type == 'out_refund'
        is_debit_note = self.move_type == 'out_invoice' and bool(self.debit_origin_id)
        if is_credit_note:
            data, engine_module = self._gather_native_credit_note_data(), notacredito_engine
        elif is_debit_note:
            data, engine_module = self._gather_native_debit_note_data(), notadebito_engine
        else:
            data, engine_module = self._gather_native_data(), None
        numeric_code = str(secrets.randbelow(10**8)).zfill(8)
        data['numeric'] = numeric_code
        try:
            access_key, xml_unsigned = (engine_module.generate(data) if engine_module else generate(data))
        except ValueError as error:
            raise ValidationError(str(error)) from error
        p12_bytes = base64.b64decode(certificate.sudo().p12_file or b'')
        password = (certificate.sudo().p12_password or '').encode('utf-8')
        try:
            xml_signed = xades.sign(xml_unsigned, p12_bytes, password, self.company_id.vat)
        except ValueError as error:
            raise ValidationError('No se pudo firmar: ' + str(error)) from error
        emission = self.env['erpec.fiscal.emission'].with_context(_fiscal_sri_internal=_INTERNAL).create({
            'move_id': self.id, 'access_key': access_key,
            'xml_unsigned': base64.b64encode(xml_unsigned), 'xml_signed': base64.b64encode(xml_signed),
            'state': 'signed', 'message': 'Firmada. Procesar la cola para transmitir al SRI.',
        })
        return {'type': 'ir.actions.act_window', 'res_model': 'erpec.fiscal.emission', 'res_id': emission.id, 'view_mode': 'form'}
