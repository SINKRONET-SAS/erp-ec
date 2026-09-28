"""Catálogo y portal con identidad personal explícita; importes calculados exclusivamente en servidor."""
import uuid
from urllib.parse import urlencode
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError,UserError,ValidationError
from werkzeug.exceptions import NotFound
from ..models import RUC_RE,EMAIL_RE,REGIME_OPTIONS

STATES={'draft':'Registrada','awaiting_payment':'Esperando pago','paid':'Pago confirmado; preparando tu ERP',
        'scheduled':'Pago confirmado para la próxima renovación','provisioned':'Tu ERP está disponible','failed':'Se requiere revisión del operador'}


def operator_model(name):
    return request.env[name].with_user(request.env.ref('base.user_admin')).sudo().with_company(request.website.company_id)


def owned_customer(reference):
    record=operator_model('erpec.customer').search([('reference','=',reference),('portal_user_id','=',request.env.uid),
        ('company_id','=',request.website.company_id.id)],limit=1)
    if not record:raise NotFound()
    return record


def owned_signup(reference):
    record=operator_model('erpec.selfservice.request').search([('reference','=',reference),('customer_id.portal_user_id','=',request.env.uid),
        ('company_id','=',request.website.company_id.id)],limit=1)
    if not record:raise NotFound()
    return record


def render(template,values,status=200):
    response=request.render('erpec_selfservice.'+template,dict(states=STATES,**values))
    response.status_code=status
    response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})
    return response


def fail(message,status=400):
    return render('commercial_error',{'message':message},status)


def selection(values):
    plan_id=int(values.get('plan_id','0'))
    plan=request.env['erpec.plan']._public_offers(request.website.company_id).filtered(lambda p:p.id==plan_id)
    if not plan:raise ValidationError('Esta oferta no está disponible. Revisa los planes publicados.')
    users=int(values['user_quantity']) if values.get('user_quantity') else plan.max_users
    options=[int(value) for value in request.httprequest.values.getlist('option_ids')]
    quote=plan._quote(values.get('period','monthly'),users,options)
    return plan,quote


def renewal_context(values):
    reference=values.get('customer')
    if not reference:return None,None
    customer=owned_customer(reference)
    previous=operator_model('erpec.subscription').search([('id','=',int(values.get('previous_id',0))),
        ('customer_id','=',customer.id),('activated_at','!=',False)],limit=1)
    if not previous:raise ValidationError('Selecciona un contrato autorizado de tu empresa para renovar.')
    return customer,previous


class SelfserviceController(http.Controller):
    @http.route('/autoservicio',type='http',auth='public',website=True,methods=['GET'],sitemap=True)
    def landing(self,**kwargs):
        return render('landing',{})

    @http.route('/autoservicio/contratar',type='http',auth='user',website=True,methods=['GET'],sitemap=False)
    def configure(self,**values):
        try:
            plan,quote=selection(values)
            customer,previous=renewal_context(values)
        except (ValueError,TypeError):return fail('La cantidad de usuarios y el plan deben ser números enteros.')
        except (ValidationError,UserError) as error:return fail(str(error))
        return render('configure',{'plan':plan,'quote':quote,'customer':customer,'previous':previous,
            'request_key':uuid.uuid4().hex,'regimes':REGIME_OPTIONS})

    @http.route('/autoservicio/solicitar',type='http',auth='user',website=True,methods=['POST'],sitemap=False)
    def signup(self,**post):
        try:
            plan,quote=selection(post)
            customer,previous=renewal_context(post)
            values={key:(post.get(key) or '').strip() for key in ('company_name','company_vat','company_regime','street','contact_name','contact_email','contact_phone')}
            if customer:
                values.update(company_name=customer.name,company_vat=customer.vat,company_regime=customer.regime,street=customer.street,
                    contact_name=customer.contact_name,contact_email=customer.email,contact_phone=customer.phone)
            if not all(values[k] for k in ('company_name','company_regime','street','contact_name')):
                raise ValidationError('Completa los datos de empresa y contacto.')
            if any(len(v or '')>200 for v in values.values()) or not RUC_RE.fullmatch(values['company_vat']) or not EMAIL_RE.fullmatch(values['contact_email']):
                raise ValidationError('Revisa el RUC de 13 dígitos, el correo y la longitud de los datos.')
            if values['company_regime'] not in dict(REGIME_OPTIONS):raise ValidationError('Selecciona un régimen disponible.')
            values.update(plan_id=plan.id,period=quote['period'],user_quantity=quote['users'],option_ids=quote['option_ids'],request_key=post.get('request_key'))
            with request.env.cr.savepoint():
                signup=operator_model('erpec.selfservice.request')._create_signup(values,owner_user=request.env.user,customer=customer,previous=previous)
        except (ValueError,TypeError):return fail('Revisa el plan y la cantidad de usuarios.')
        except (ValidationError,UserError,AccessError) as error:return fail(str(error))
        return request.redirect('/mi-servicio/alta/'+signup.reference)

    @http.route('/mi-servicio',type='http',auth='user',website=True,methods=['GET'],sitemap=False)
    def portal(self,**kwargs):
        customers=operator_model('erpec.customer').search([('portal_user_id','=',request.env.uid),('company_id','=',request.website.company_id.id)])
        signups=operator_model('erpec.selfservice.request').search([('customer_id','in',customers.ids)])
        return render('portal',{'customers':customers,'signups':signups})

    @http.route('/mi-servicio/alta/<string:reference>',type='http',auth='user',website=True,methods=['GET'],sitemap=False)
    def progress(self,reference,**kwargs):
        signup=owned_signup(reference)
        job=signup.customer_id.provision_ids[:1]
        return render('progress',{'signup':signup,'job':job,'quote':signup.subscription_id.commercial_snapshot})

    @http.route('/mi-servicio/cliente/<string:reference>/renovar',type='http',auth='user',website=True,methods=['GET'],sitemap=False)
    def renew(self,reference,**kwargs):
        customer=owned_customer(reference)
        previous=customer.subscription_ids.filtered('activated_at').sorted(lambda x:x.ends_on,reverse=True)[:1]
        offers=request.env['erpec.plan']._public_offers(request.website.company_id)
        if not previous: return fail('La empresa aún no tiene un contrato confirmado.')
        return render('renew',{'customer':customer,'previous':previous,'offers':offers})

    @http.route('/mi-servicio/cliente/<string:reference>/acceso',type='http',auth='user',website=True,methods=['POST'],sitemap=False)
    def access(self,reference,**post):
        customer=owned_customer(reference)
        job=customer.provision_ids[:1]
        if not job or job.state!='ready':return fail('La instancia todavía no está disponible.',409)
        try:
            if post.get('renew_link')=='1':
                job.action_refresh_access()
                return render('commercial_notice',{'message':'La solicitud está guardada. El operador preparará un nuevo enlace; revisa el estado en unos instantes.'})
            target=job._activation_url()
        except (ValidationError,AccessError) as error:return fail(str(error),409)
        response=request.redirect(target,local=False)
        response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
        return response
