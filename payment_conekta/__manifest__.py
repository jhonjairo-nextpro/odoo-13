# Copyright 2020 Vauxoo S.A. de C.V. (https://www.vauxoo.com) <info@vauxoo.com>
# License OPL-1 (https://www.odoo.com/documentation/user/13.0/legal/licenses/licenses.html).
{
    "name": "Payment Conekta",
    "summary": "Payment Acquirer Conekta",
    "version": "13.0.1.0.0",
    "category": "Website",
    "website": "https://www.vauxoo.com/",
    "author": "Vauxoo",
    "license": 'OPL-1',
    "installable": True,
    "depends": [
        "payment",
        "website_sale",
    ],
    "data": [
        "views/payment_acquirer_view.xml",
        "views/assets_frontend.xml",
        "views/sale_order_view.xml",
        "views/payment_form.xml",
        "views/payment_confirmation_status.xml",
        "data/payment_acquirer_data.xml",
    ],
    "demo": [
        "demo/res_user_demo.xml",
    ],
    'images': [
        'static/description/main_screen.jpeg'
    ],
    'application': True,
    'live_test_url': 'https://www.vauxoo.com/r/conektapay_130',
    'price': 299,
    'currency': 'EUR',
    "external_dependencies": {
        "python": ["conekta"],
    },
}
