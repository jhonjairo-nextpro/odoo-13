# coding: utf-8

import logging
import requests
import pprint
import time
import hashlib
from base64 import b64encode
from requests.exceptions import HTTPError
from werkzeug import urls
import json
from odoo.http import request

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.tools.float_utils import float_compare, float_repr, float_round

from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('paymentez', 'Paymentez')])
    paymentez_client_app_code = fields.Char(string='App code', required_if_provider='paymentez', groups='base.group_user')
    paymentez_client_app_key = fields.Char(string='App Key', required_if_provider='paymentez', groups='base.group_user')
    paymentez_server_app_code = fields.Char(string='Server code', required_if_provider='paymentez', groups='base.group_user')
    paymentez_server_app_key = fields.Char(string='Server Key', required_if_provider='paymentez', groups='base.group_user')

    def paymentez_form_generate_values(self, tx_values):
        self.ensure_one()
        _logger.info("paymentez_form_generate_values reference:" + str(tx_values))
        currency = self.env['res.currency'].sudo().browse(tx_values['currency_id'])
        if currency != self.env.ref('base.USD') and currency != self.env.ref('base.ECS'):
            raise ValidationError(_('Moneda no soportada por Paymentez'))

        tx_values.update({
            'client_app_code': self.sudo().paymentez_client_app_code,
            'amount': float_repr(float_round(tx_values.get('amount'), 2) * 100, 0),
            'name': tx_values.get('partner_name'),
            'contact': tx_values.get('partner_phone'),
            'email': tx_values.get('partner_email')
        })
        return tx_values

    def _paymentez_request(self, url, data=False, method='POST'):
        self.ensure_one()
        url = urls.url_join(self._get_paymentez_api_url(), url)
        auth_token = self.sudo()._create_paymentez_auth_token()
        headers = {
            'Auth-Token': str(auth_token, encoding="utf-8"),
            'content-type': 'application/json'
        }

        responseObj = {"status_code":"404", "response_json":""}
        try:
            _logger.info("url :" + url + " requests :" +json.dumps(data) + " headers :" +json.dumps(headers))
            resp = requests.request(method, url, data=json.dumps(data), headers=headers)
            
            _logger.info("response.status_code :" + str(resp.status_code)+ " Json :" + json.dumps(resp.json()) )
            responseObj["status_code"] = str(resp.status_code)
            responseObj["response_json"] = resp.json()
            return responseObj
            
        except requests.exceptions.ConnectionError as e:
            _logger.error("Aquí hay más información para el "
                          "siguiente error HTTP en %s:\n"
                          "Request data:\n%s\n"
                          "Response body:\n%s",
                          str(e), pprint.pformat(data), resp.text)
            return responseObj

    @api.model
    def _create_paymentez_auth_token(self):
        server_application_code = self.sudo().paymentez_server_app_code
        server_app_key = self.sudo().paymentez_server_app_key
        unix_timestamp = str(int(time.time()))
        uniq_token_string = server_app_key + unix_timestamp
        uniq_token_hash = hashlib.sha256(str(uniq_token_string).encode()).hexdigest()
        auth_token = b64encode(('%s;%s;%s' % (server_application_code, unix_timestamp, uniq_token_hash)).encode())
        return auth_token
    
    @api.model
    def _get_paymentez_api_url(self):
        url = 'https://ccapi-stg.paymentez.com/v2/transaction/' 
        if self.sudo().state == "enabled" :
            url = 'https://ccapi.paymentez.com/v2/transaction/'
        return url

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _create_paymentez_capture(self, data):
        order = self.env['sale.order'].sudo().browse(int(data.get('order_id')))
        data["order_name"] = order.name
        data["order_id"] = order.id
        data["amount_total"] = order.amount_total
        #data["payment_id"] = ""
        if data.get("response",{}).get("transaction",{}).get("id"):
            data["payment_id"] = data.get("response",{}).get("transaction",{}).get("id")

        return data

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------
    @api.model
    def _paymentez_form_get_tx_from_data(self, data):
        reference = data.get('reference')
        if not reference :
            error_msg = _('Paymentez: received data with missing reference (%s) ') % (reference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = _('Paymentez: received data for reference %s') % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    def _paymentez_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if float_compare(data.get('amount_total', '0.0'), self.amount, precision_digits=2) != 0:
            invalid_parameters.append(('amount_total', data.get('amount_total'), '%.2f' % self.amount))
        return invalid_parameters

    def _paymentez_form_validate(self, data):
        tx = data.get('response',{}).get('transaction')
        status = tx.get("status");
        if status == 'success':
            _logger.info('Validated Paymentez payment for tx %s: set as done' % (self.reference))
            self.write({'acquirer_reference': tx.get('id')})
            #self.write({'paymentez_auth_code': tx.get('authorization_code')})
            #self.write({'paymentez_trans_code': tx.get('id')})
            self._set_transaction_done()
            order = request.env['sale.order'].sudo().browse(int(data.get('order_id')))
            order.write({"paymentez_auth_code":tx.get("authorization_code"),"paymentez_trans_code":tx.get("id")})
            

            return True
        if status == 'review':
            _logger.info('Validated Paymentez payment for tx %s: set as authorized' % (self.reference))
            self.write({'acquirer_reference': tx.get('id')})
            self._set_transaction_authorized()
            return True
        else:
            error = 'Received unrecognized status for Paymentez payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            self.write({'acquirer_reference': tx.get('id'), 'state_message': tx.get('error',"")})
            self._set_transaction_cancel()
            return False

    def _create_paymentez_refund(self):
        refund_params = {  
                    "transaction": {
                        "id": self.acquirer_reference
                    }
                }
        _logger.info('_create_paymentez_refund: Sending values to stripe URL, values:\n%s', pprint.pformat(refund_params))
        res = self.acquirer_id.sudo()._paymentez_request('refund', refund_params)
        _logger.info('_create_paymentez_refund: Values received:\n%s', pprint.pformat(res))
        
        if res["status_code"] != "200":
            json_resp = res["response_json"]
            if json_resp.get("error"):
                msg_error =  json_resp.get("error",{}).get("type")
            raise Warning("Ocurrio un error al realizar el reembolso del pago. Por favor validar! : "+ msg_error)
        else:
            json_resp = res["response_json"]
            if json_resp.get("status") == "success":
                self._set_transaction_cancel()
            else: 
                 raise Warning("Ocurrio un error al realizar el reembolso del pago. Por favor validar!")

        return res

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def paymentez_refund(self):
        self.ensure_one()
        if self.payment_transaction_id.sudo().acquirer_id.provider == "paymentez":
            res = self.payment_transaction_id.sudo()._create_paymentez_refund()
            _logger.info('_paymentez_refund: Values received:\n%s', pprint.pformat(res))

            if res["status_code"] != "200":
                json_resp = res["response_json"]
                if json_resp.get("error"):
                    msg_error =  json_resp.get("error",{}).get("type")
                raise Warning("Ocurrio un error al realizar el reembolso del pago. Por favor validar! : "+ msg_error)
            else:
                json_resp = res["response_json"]
                if json_resp.get("status") == "success":
                    self.sudo().write({"state":"cancelled"})
                else: 
                    raise Warning("Ocurrio un error al realizar el reembolso del pago. Por favor validar!")
                