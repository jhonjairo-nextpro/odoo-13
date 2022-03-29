# -*- coding: utf-8 -*-
import logging
import werkzeug
import json
import pprint

from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website

_logger = logging.getLogger(__name__)


class PaymentezController(http.Controller):

    @http.route(['/payment/paymentez/capture'], type='json', auth='public', csrf=False)
    def paymentez_capture(self, **kwargs):
        _logger.info('paymentez_capture' + str(kwargs))
        acquirer_id = kwargs.get('acquirer_id')
        res = { 
                'result': False,
            }

        order = False
        if kwargs.get('order_id'):
            order = request.env['sale.order'].sudo().browse(int(kwargs.get('order_id')))
        
        if request.session.get('sale_order_id') and not order: 
            order = request.env['sale.order'].sudo().browse(int(request.session.get('sale_order_id')))
        
        if request.session.get('sale_last_order_id') and not order: 
            order = request.env['sale.order'].sudo().browse(int(request.session.get('sale_last_order_id')))

        if acquirer_id and order:
            kwargs["order_id"] = order.id
            response = request.env['payment.transaction'].sudo()._create_paymentez_capture( kwargs)

            if response.get("payment_id"):
                _logger.info('Paymentez: entering form_feedback with post data %s', pprint.pformat(response))
                request.env['payment.transaction'].sudo().form_feedback(response, 'paymentez')
                res = { 
                    'result': True,
                    "url": '/payment/process'
                }
        
        return res
        


    @http.route(['/payment/paymentez/get_credentials_api'], type='json', auth='public', csrf=False)
    def paymentez_get_credentials_api(self, **kwargs):
        token = request.env['payment.acquirer'].sudo().browse(int(kwargs.get('acquirer_id')))
        order = False
        if kwargs.get('order_id'):
            order = request.env['sale.order'].sudo().browse(int(kwargs.get('order_id')))
        
        if request.session.get('sale_order_id') and not order: 
            order = request.env['sale.order'].sudo().browse(int(request.session.get('sale_order_id')))
        
        if request.session.get('sale_last_order_id') and not order: 
            order = request.env['sale.order'].sudo().browse(int(request.session.get('sale_last_order_id')))
        
        if not token and not order:
            res = {
                'result': False,
            }
            return res
        
        env_mode = "prod"
       
        if token.state != "enabled":
            env_mode = "stg"
        _logger.info('env_mode:' + str(env_mode))
        _logger.info('token.state:' + str(token.state))

        base_amount_tax = sum(line.price_subtotal for line in order.order_line.filtered(lambda r: r.price_tax > 0 ))
        base_amount_tax = base_amount_tax if base_amount_tax else 0
        order_description = order.order_line[0].product_id.name if order.order_line[0].product_id.name else ""
        tax_percentage = round((order.amount_tax/base_amount_tax)*100,0)

        res = {
            'result': True,
            'id': token.id,
            'short_name': token.provider,
            'client_app_code': token.paymentez_client_app_code,
            'client_app_key': token.paymentez_client_app_key,
            'env_mode': env_mode,
            'user_id': str(order.partner_id.id),
            'user_email': order.partner_id.email if order.partner_id.email else "",
            'user_phone': order.partner_id.phone if order.partner_id.phone else "",
            'order_description': order_description,
            'order_amount': order.amount_total,
            'order_vat': order.amount_tax,
            'order_taxable_amount': base_amount_tax,
            'order_tax_percentage': tax_percentage,
            'order_reference': order.name,
        }

        _logger.info('paymentez_get_credentials_api' + str(res))
        return res
