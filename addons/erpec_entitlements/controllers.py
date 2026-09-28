"""Salud mínima para el trabajador, sin contraseñas ni información comercial."""
from odoo import http
from odoo.http import request

class TenantHealth(http.Controller):
    @http.route('/erpec/tenant-health',type='http',auth='public',methods=['GET'],save_session=False)
    def health(self):
        record=request.env['erpec.tenant.entitlement'].sudo().search([],limit=1)
        return request.make_json_response({'ready':bool(record),'revision':record.revision or None},status=200 if record else 503,
                                          headers={'Cache-Control':'no-store'})
