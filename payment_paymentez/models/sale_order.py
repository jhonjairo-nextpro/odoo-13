
from odoo import api, models, fields, _


class SaleOrder(models.Model):
    _inherit = "sale.order"
    paymentez_auth_code = fields.Char(string='Numero de autorización de pago')
    paymentez_trans_code = fields.Char(string='ID de transacción de pago')
    is_quote = fields.Boolean(string='Es cotización?')
