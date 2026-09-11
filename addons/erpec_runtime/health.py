"""Salud de la instancia seleccionada; no consulta la base administrativa postgres."""
import os
from odoo import http
from odoo.http import request


class Health(http.Controller):
    @http.route('/erpec/health', type='http', auth='public', methods=['GET'], save_session=False)
    def health(self):
        request.env.cr.execute('SELECT instance,ready FROM erpec_runtime_identity WHERE singleton')
        row = request.env.cr.fetchone()
        ready = bool(row and row[1] and row[0] == os.environ.get('ERPEC_INSTANCE_ID'))
        return request.make_json_response({'status':'pass' if ready else 'fail'},
            status=200 if ready else 503, headers={'Cache-Control':'no-store'})
