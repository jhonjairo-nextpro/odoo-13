# Copyright 2020 Vauxoo S.A. de C.V. (https://www.vauxoo.com) <info@vauxoo.com>
# License OPL-1 (https://www.odoo.com/documentation/user/13.0/legal/licenses/licenses.html).
# pylint: disable=R1710

import logging
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

try:
    import conekta
except (ImportError, IOError) as err:
    _logger.debug(err)


def get_error_message(exception):
    message = exception.error_json.get('message')
    if not message:
        details = exception.error_json.get('details')
        message = details and details[0].get('message')
    return message


class AcquirerConekta(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('conekta', 'Conekta')])
    conekta_public_key = fields.Char(required_if_provider='conekta')
    conekta_private_key = fields.Char(required_if_provider='conekta')

    def conekta_get_form_action_url(self):
        self.ensure_one()
        return '/shop/payment/validate'

    @api.model
    def conekta_s2s_form_process(self, data):
        payment_token = self.env['payment.token'].sudo().create({
            'name': data['cc_number'],
            'acquirer_ref': data['token_id'],
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id']),
            'verified': True
        })
        return payment_token

    def conekta_s2s_form_validate(self, data):
        self.ensure_one()
        # mandatory fields
        for field_name in ["cc_number"]:
            if not data.get(field_name):
                return False
        return True

    def _get_feature_support(self):
        support = super()._get_feature_support()
        tokenized = support.get('tokenize')
        tokenized.append('conekta')
        return support


class PaymentTransactionConekta(models.Model):
    _inherit = 'payment.transaction'

    def conekta_s2s_do_transaction(self, **data):
        self.ensure_one()
        result = self._create_conekta_charge()
        tree = self._conekta_s2s_validate_tree(result)
        return tree

    def _create_conekta_charge(self, **data):
        payment_acquirer = self.env['payment.acquirer']
        conekta_acq = payment_acquirer.sudo().search(
            [('provider', '=', 'conekta')])
        conekta.api_key = conekta_acq.conekta_private_key
        params = self._create_conekta_params('conekta')
        try:
            conekta_res = conekta.Order.create(params)
        except conekta.ConektaError as error:
            return error
        return conekta_res

    def _conekta_build_payload(self, params):
        line_items = []

        for line in params.get('lines'):
            # quantity = 1, becuase price_subtotal is for all products in the order_line
            # Round: because in some cases a penny is lost like 1208.36 * 100 = 120835.99999
            item = {
                'name': line.product_id.name,
                'unit_price': int(round(line.price_subtotal * 100)),
                'quantity': 1,
            }

            if line.product_id.description_sale:
                item['description'] = line.product_id.description_sale[:250]
            else:
                item['description'] = line.product_id.name[:250]

            if line.product_id.default_code:
                item['sku'] = line.product_id.default_code
            if line.product_id.categ_id:
                item['tags'] = [line.product_id.categ_id.name]
            line_items.append(item)

        partner = params.get('partner')
        partner_shipping = params.get('partner_shipping')
        params = {
            'line_items': line_items,
            'currency': self.currency_id.name,
            'customer_info': {
                'name': partner.name,
                'phone': partner.phone or partner.company_id.phone,
                'email': partner.email,
            },
            "shipping_contact": {
                "phone": partner_shipping.phone or partner_shipping.company_id.phone,
                "receiver": partner_shipping.name,
                "address": {
                    "street1": partner_shipping.street,
                    "street2": partner_shipping.street2 or '',
                    "city": partner_shipping.city,
                    "state": partner_shipping.state_id and partner_shipping.state_id.code or '',
                    "postal_code": partner_shipping.zip or '',
                    "country": partner_shipping.country_id.name,
                }
            },
            'tax_lines': [{
                "description": _("TAX"),
                "amount": params.get('amount_tax'),
            }],
            'charges': [{
                'payment_method': {
                    'type': 'card',
                    'token_id': self.payment_token_id.acquirer_ref,
                }
            }]
        }
        return params

    def _create_conekta_params(self, acquirer):
        if self.sale_order_ids:
            order = self.sale_order_ids[:1]
            params = {
                'name': _('%s Order %s') % (order.company_id.name, order.name),
                'lines': order.order_line,
                'partner_shipping': order.partner_shipping_id or order.partner_id,
                'partner': order.partner_id,
                'card': self.payment_token_id.acquirer_ref,
                'amount_tax': int(round(order.amount_tax * 100)),
            }
        else:
            invoice = self.invoice_ids[:1]
            params = {
                'name': _('%s Invoice %s') % (invoice.company_id.name, invoice.name),
                'lines': invoice.invoice_line_ids,
                'partner_shipping': invoice.partner_shipping_id or invoice.partner_id,
                'partner': invoice.partner_id,
                'card': self.payment_token_id.acquirer_ref,
                'amount_tax': int(round(invoice.amount_tax * 100)),
            }
        return self._conekta_build_payload(params)

    def _conekta_s2s_validate_tree(self, tree):
        self.ensure_one()
        # Conekta payment tokens are for only one use, deactivating it to avoid
        # reuse as payment method in website checkout.
        if self.payment_token_id:
            self.payment_token_id.active = False
        if isinstance(tree, conekta.ConektaError):
            message = get_error_message(tree)
            _logger.error(_("Error in Conekta transaction: %s"), message)
            self.write({
                'state': 'error',
                'state_message': message,
                'date': fields.datetime.now(),
            })
            self.payment_token_id.unlink()
            return False
        if tree.payment_status == 'paid':
            self.write({
                'state': 'done',
                'date': fields.datetime.now(),
                'acquirer_reference': tree.id,
            })
            self.execute_callback()
            return True
        if self.state not in ('draft', 'pending', 'refunding'):
            _logger.info(
                'Conekta: trying to validate an already validated tx (ref %s)',
                self.reference)
        return True

    @api.model
    def _conekta_form_get_tx_from_data(self, data):
        reference = data['reference_id']
        payment_tx = self.search([('reference', '=', reference)])
        if not payment_tx or len(payment_tx) > 1:
            error_msg = _(
                'Conekta: received data for reference %s') % reference
            if not payment_tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return payment_tx

    @api.model
    def _conekta_form_validate(self, data):
        date = datetime.datetime.fromtimestamp(
            int(data['paid_at'])).strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'acquirer_reference': data['id'],
            'date': date,
            'state': 'done',
        }
        self.write(data)
