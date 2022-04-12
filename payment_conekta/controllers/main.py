# Copyright 2020 Vauxoo S.A. de C.V. (https://www.vauxoo.com) <info@vauxoo.com>
# License OPL-1 (https://www.odoo.com/documentation/user/13.0/legal/licenses/licenses.html).

import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class ConektaController(http.Controller):

    @http.route('/payment/conekta/s2s/create_json_3ds', type='json',
                auth='public', methods=['POST'], csrf=False)
    def conekta_s2s_create_json_3ds(self, verify_validity=False, **post):
        token = request.env['payment.acquirer'].browse(
            int(post.get('acquirer_id'))).s2s_process(post)
        if not token:
            res = {
                'result': False,
            }
            return res
        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
        }
        if verify_validity is not False:
            token.validate()
            res['verified'] = token.verified
        return res

    @http.route('/payment/conekta/s2s/retrieve_json_3ds', type='json',
                auth='public', methods=['POST'], csrf=False)
    def conekta_s2s_retrieve_json_3ds(self, verify_validity=False, **post):
        tk_id = post.get('payment_token_id', False)
        if not tk_id:
            res = {
                'result': False,
                'error': _(
                    ('Payment token was not provided'
                     ' for the requested operation.'))
            }
            return res
        tk = request.env['payment.token'].sudo().browse(int(tk_id))
        res = {
            'result': True,
            'id': tk.id,
            'short_name': tk.short_name,
            'verified': False,
            '3d_secure': False,
        }
        return res
