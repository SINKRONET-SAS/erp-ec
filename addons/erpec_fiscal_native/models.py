"""Vista previa nativa sin reservar secuencias ni comunicar al SRI."""
import base64,hashlib,json
from odoo import api,fields,models
from odoo.exceptions import ValidationError
from .engine import generate
_INTERNAL=object()


class Company(models.Model):
    _inherit='res.company'
    ec_native_ordinary=fields.Boolean('Perfil ordinario revisado, sin atributos fiscales especiales')
    ec_native_accounting=fields.Selection([('SI','Sí'),('NO','No')],string='Obligado a llevar contabilidad (verificar RUC)')
    ec_tax_regime=fields.Selection([('general','General'),('rimpe_emprendedor','RIMPE emprendedor'),('rimpe_popular','RIMPE negocio popular')],string='Régimen fiscal',
        help='Los regímenes RIMPE exigen la leyenda contribuyenteRimpe en los comprobantes, que este motor aún no genera: no se permite emitir hasta ampliarlo.')

    ec_system_provider_vat=fields.Char('RUC del proveedor del sistema de facturación',
        help='Ficha Técnica SRI 2.34, Anexo 26 (Resolución NAC-DGERCGC26-00000027): quien emite con un sistema de facturación de '
             'terceros incluye en la información adicional de cada comprobante el campo "RUC Proveedor". Si queda vacío se usa el '
             'RUC del proveedor configurado en el sistema; no se incluye cuando coincide con el RUC de esta empresa (sistema propio).')

    def _ec_system_provider(self):
        self.ensure_one()
        return (self.ec_system_provider_vat or self.env['ir.config_parameter'].sudo().get_param('erpec.system_provider_vat') or '').strip()

    def _ec_info_adicional(self):
        """Campos adicionales obligatorios de los comprobantes nativos de esta empresa."""
        self.ensure_one()
        provider=self._ec_system_provider()
        if provider and provider!=(self.vat or '').strip():
            return [('RUC Proveedor',provider)]
        return []

    @api.constrains('ec_system_provider_vat')
    def _check_system_provider_vat(self):
        for company in self:
            value=(company.ec_system_provider_vat or '').strip()
            if value and not (len(value)==13 and value.isdigit() and value.endswith('001')):
                raise ValidationError('El RUC del proveedor del sistema debe tener 13 dígitos y terminar en 001.')

    def _check_regime_supported(self):
        for company in self:
            if company.ec_tax_regime and company.ec_tax_regime!='general':
                raise ValidationError('El régimen %s requiere ampliar el XML (leyenda contribuyenteRimpe) antes de emitir; este motor solo admite el régimen general.'%dict(company._fields['ec_tax_regime'].selection)[company.ec_tax_regime])


class Move(models.Model):
    _inherit='account.move'
    ec_native_notice=fields.Text(compute='_compute_native_notice',string='Preparación local')

    @api.depends('company_id.vat','company_id.street','company_id.ec_native_ordinary','company_id.ec_native_accounting','state','move_type')
    def _compute_native_notice(self):
        for move in self:
            missing=[]
            if not move.company_id.vat:missing.append('RUC real del emisor')
            if not move.company_id.street:missing.append('dirección matriz')
            if not move.company_id.ec_native_ordinary or not move.company_id.ec_native_accounting:missing.append('perfil fiscal y obligación contable verificados en la empresa')
            if move.state!='posted':missing.append('factura contabilizada')
            move.ec_native_notice=('Completar: '+', '.join(missing)+'. ' if missing else '')+'Vista previa del XML sin firma, preparada dentro del ERP: no emite ni autoriza. La firma XAdES, el envío y la autorización del SRI y el RIDE se hacen en la pestaña "Firma y transmisión SRI", en el ambiente configurado para la empresa. El RUC del proveedor del sistema se agrega en la información adicional cuando corresponde (Ficha Técnica 2.34, Anexo 26).'

    def _gather_native_common(self, allow_special_vat=False):
        """Datos comunes para vista previa y emisión; una validación de líneas e identificación."""
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id.commercial_partner_id
        identification = ('04' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_ruc')
                          else '05' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_dni')
                          else '06' if partner.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_passport') else '')
        items = []
        for line in self.invoice_line_ids.filtered(lambda row: row.display_type == 'product'):
            tax = line.tax_ids
            special = {'not_charged_vat': 'no_object', 'exempt_vat': 'exempt'}.get(tax.tax_group_id.l10n_ec_type) if len(tax) == 1 else None
            if (len(tax) != 1 or tax.amount_type != 'percent' or tax.price_include or tax.include_base_amount
                    or not ((tax.tax_group_id.l10n_ec_type, tax.amount) in [('zero_vat', 0), ('vat15', 15)] or (allow_special_vat and special and tax.amount == 0))):
                raise ValidationError('Revisar IVA: se admite una tarifa 0 o 15 por línea (y no objeto/exento solo en facturas), sin impuestos incluidos ni compuestos.')
            items.append({'code': line.product_id.default_code or str(line.id), 'description': line.name,
                          'quantity': line.quantity, 'unit': line.price_unit, 'discount': line.discount,
                          'rate': special if (allow_special_vat and special) else tax.amount, 'subtotal': line.price_subtotal,
                          'tax': line.price_total - line.price_subtotal})
        return {'date': str(self.invoice_date), 'number': self.l10n_latam_document_number, 'issuer_vat': company.vat,
                'issuer_name': company.name, 'issuer_address': company.street, 'buyer_type': identification,
                'buyer_vat': partner.vat, 'buyer_name': partner.name, 'buyer_address': partner.street,
                'accounting': company.ec_native_accounting, 'total': self.amount_total, 'items': items}

    def action_native_preview(self):
        self.ensure_one();self.check_access('read')
        if not self.env.user.has_group('account.group_account_user'):raise ValidationError('La preparación fiscal requiere permisos contables.')
        if self.state!='posted' or self.move_type!='out_invoice' or self.currency_id.name!='USD' or self.company_id.country_id.code!='EC':
            raise ValidationError('Se requiere factura de venta contabilizada en USD de Ecuador.')
        if self.ec_fiscal_job_ids:raise ValidationError('Esta factura ya está asignada al Facturador; conserva su autoridad y trazabilidad.')
        company=self.company_id;partner=self.partner_id.commercial_partner_id
        company._check_regime_supported()
        if not company.ec_native_ordinary or not company.ec_native_accounting:
            raise ValidationError('El perfil tributario especial requiere ampliar el XML antes de usarlo.')
        data = self._gather_native_common()
        data['payment'] = self.ec_fiscal_payment_code
        data['ambiente'] = '1'
        # Código reproducible solo para previsualización; no reserva un secuencial fiscal.
        data['info_adicional']=self.company_id._ec_info_adicional()
        digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest();data['numeric']=str(int(digest[:12],16)%100000000).zfill(8)
        try:key,xml=generate(data)
        except ValueError as error:raise ValidationError(str(error)) from error
        preview=self.env['erpec.fiscal.preview'].with_context(_native_preview=_INTERNAL).create({'move_id':self.id,'access_key':key,'xml_file':base64.b64encode(xml),'filename':'PREVIA-SIN-FIRMA-'+self.name.replace('/','-')+'.xml','digest':hashlib.sha256(xml).hexdigest()})
        return {'type':'ir.actions.act_window','res_model':'erpec.fiscal.preview','res_id':preview.id,'view_mode':'form','target':'new'}


class Preview(models.TransientModel):
    _name='erpec.fiscal.preview'
    _description='Vista previa fiscal local sin firma'
    move_id=fields.Many2one('account.move',required=True,readonly=True, string='Asiento contable')
    company_id=fields.Many2one(related='move_id.company_id',store=True, string='Empresa')
    access_key=fields.Char('Clave de la vista previa',readonly=True)
    xml_file=fields.Binary('XML sin firma',readonly=True,attachment=False)
    filename=fields.Char(readonly=True, string='Nombre del archivo')
    digest=fields.Char('SHA256 del XML',readonly=True)

    @api.model_create_multi
    def create(self,values_list):
        if self.env.context.get('_native_preview') is not _INTERNAL:raise ValidationError('Genera la vista previa desde la factura.')
        return super().create(values_list)

    def write(self,values):
        raise ValidationError('La vista previa no se edita; vuelve a generarla desde la factura.')
