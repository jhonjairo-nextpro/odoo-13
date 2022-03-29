# -*- coding: utf-8 -*-

{
    'name': 'Paymentez Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'Paymentez Acquirer: Paymentez Implementation',
    'version': '1.0',
    'description': """Paymentez Payment Acquirer""",
    'depends': ['payment','sale'],
    'data': [
        'views/payment_views.xml',
        'views/payment_paymentez_templates.xml',
        'views/account_payment_view.xml',
        'data/payment_acquirer_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
