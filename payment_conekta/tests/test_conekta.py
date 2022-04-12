# Copyright 2020 Vauxoo S.A. de C.V. (https://www.vauxoo.com) <info@vauxoo.com>
# License OPL-1 (https://www.odoo.com/documentation/user/13.0/legal/licenses/licenses.html).

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TesConekta(TransactionCase):

    def setUp(self):
        super().setUp()
        self.conekta = self.env.ref('payment_conekta.payment_acquirer_conekta')
        self.country = self.env.ref('base.us')
        self.currency = self.env.ref('base.USD')
        self.main_company = self.env.ref('base.main_company')
        self.state = self.env.ref('base.state_us_3')
        self.pricelist = self.env.ref('product.list0')

        self.product = self.env['product.product'].create({
            'name': 'Product A',
        })

        self.buyer = self.env['res.partner'].create({
            'name': 'Norbert Buyer',
            'lang': 'en_US',
            'email': 'norbert.buyer@example.com',
            'street': 'Huge Street',
            'street2': '2/543',
            'phone': '0032 12 34 56 78',
            'city': 'Sin City',
            'zip': '1000',
            'country_id': self.country.id,
            'state_id': self.state.id,
        })

        self.order = self.env['sale.order'].create({
            'partner_id': self.buyer.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [
                (0, False, {
                    'product_id': self.product.id,
                    'name': '1 Product',
                    'price_unit': 100.0,
                }),
            ],
        })

        self.journal = self.env['account.journal'].create({
            'name': 'Sales Journal - Test',
            'code': 'TSJ',
            'type': 'sale',
            'company_id': self.main_company.id
        })

        self.conekta.write({
            'conekta_public_key': 'key_FYRbSGG18rSqnNZqjiQzagA',
            'conekta_private_key': 'key_L9DRqz64M7xDr4z7e1wqFQ',
            'state': 'test',
            'journal_id': self.journal.id,
        })

        self.token = self.env['payment.token'].create({
            'name': '4242424242424242',
            'acquirer_id': self.conekta.id,
            'acquirer_ref': 'tok_test_visa_4242',
            'partner_id': self.buyer.id,
            'verified': True,
        })

    def test_01_conekta_s2s(self, request=None):
        self.assertEqual(self.conekta.state, 'test', 'test without test environment')
        # Create transaction
        tx = self.order._create_payment_transaction({
            'reference': fields.datetime.now().strftime('%Y%m%d_%H%M%S'),
            'currency_id': self.currency.id,
            'acquirer_id': self.conekta.id,
            'partner_id': self.buyer.id,
            'payment_token_id': self.token.id,
            'type': 'form',
        })
        # Do transaction
        tx.with_context(off_session=True).conekta_s2s_do_transaction()
        # Check state
        self.assertEqual(tx.state, 'done', 'Transcation has been discarded.')
