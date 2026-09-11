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
            move.ec_native_notice=('Completar: '+', '.join(missing)+'. ' if missing else '')+'Preparación XML dentro del ERP, sin servicio Facturador. Ambiente PRUEBAS. Falta implementar y validar firma XAdES, envío/consulta SRI y RIDE autorizado; esta vista previa no emite ni autoriza.'

    def action_native_preview(self):
        self.ensure_one();self.check_access('read')
        if not self.env.user.has_group('account.group_account_user'):raise ValidationError('La preparación fiscal requiere permisos contables.')
        if self.state!='posted' or self.move_type!='out_invoice' or self.currency_id.name!='USD' or self.company_id.country_id.code!='EC':
            raise ValidationError('Se requiere factura de venta contabilizada en USD de Ecuador.')
        if self.ec_fiscal_job_ids:raise ValidationError('Esta factura ya está asignada al Facturador; conserva su autoridad y trazabilidad.')
        company=self.company_id;partner=self.partner_id.commercial_partner_id
        if not company.ec_native_ordinary or not company.ec_native_accounting:
            raise ValidationError('El perfil tributario especial requiere ampliar el XML antes de usarlo.')
        identification='04' if partner.l10n_latam_identification_type_id==self.env.ref('l10n_ec.ec_ruc') else '05' if partner.l10n_latam_identification_type_id==self.env.ref('l10n_ec.ec_dni') else ''
        items=[]
        for line in self.invoice_line_ids.filtered(lambda row:row.display_type=='product'):
            tax=line.tax_ids
            if len(tax)!=1 or tax.amount_type!='percent' or tax.price_include or tax.include_base_amount or (tax.tax_group_id.l10n_ec_type,tax.amount) not in [('zero_vat',0),('vat15',15)]:
                raise ValidationError('Revisar IVA: se admite una tarifa 0 o 15 por línea, sin impuestos incluidos ni compuestos.')
            items.append({'code':line.product_id.default_code or str(line.id),'description':line.name,'quantity':line.quantity,'unit':line.price_unit,'discount':line.discount,'rate':tax.amount,'subtotal':line.price_subtotal,'tax':line.price_total-line.price_subtotal})
        data={'date':str(self.invoice_date),'number':self.l10n_latam_document_number,'issuer_vat':company.vat,'issuer_name':company.name,'issuer_address':company.street,'buyer_type':identification,'buyer_vat':partner.vat,'buyer_name':partner.name,'buyer_address':partner.street,'accounting':company.ec_native_accounting,'payment':self.ec_fiscal_payment_code,'total':self.amount_total,'items':items}
        # Código reproducible solo para previsualización; no reserva un secuencial fiscal.
        digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest();data['numeric']=str(int(digest[:12],16)%100000000).zfill(8)
        try:key,xml=generate(data)
        except ValueError as error:raise ValidationError(str(error)) from error
        preview=self.env['erpec.fiscal.preview'].with_context(_native_preview=_INTERNAL).create({'move_id':self.id,'access_key':key,'xml_file':base64.b64encode(xml),'filename':'PREVIA-SIN-FIRMA-'+self.name.replace('/','-')+'.xml','digest':hashlib.sha256(xml).hexdigest()})
        return {'type':'ir.actions.act_window','res_model':'erpec.fiscal.preview','res_id':preview.id,'view_mode':'form','target':'new'}


class Preview(models.TransientModel):
    _name='erpec.fiscal.preview'
    _description='Vista previa fiscal local sin firma'
    move_id=fields.Many2one('account.move',required=True,readonly=True)
    company_id=fields.Many2one(related='move_id.company_id',store=True)
    access_key=fields.Char('Clave de la vista previa',readonly=True)
    xml_file=fields.Binary('XML sin firma',readonly=True,attachment=False)
    filename=fields.Char(readonly=True)
    digest=fields.Char('SHA256 del XML',readonly=True)

    @api.model_create_multi
    def create(self,values_list):
        if self.env.context.get('_native_preview') is not _INTERNAL:raise ValidationError('Genera la vista previa desde la factura.')
        return super().create(values_list)

    def write(self,values):
        raise ValidationError('La vista previa no se edita; vuelve a generarla desde la factura.')
