# Copyright 2020 Vauxoo S.A. de C.V. (https://www.vauxoo.com) <info@vauxoo.com>
# License OPL-1 (https://www.odoo.com/documentation/user/13.0/legal/licenses/licenses.html).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_tx_status = fields.Boolean(compute='_compute_transaction_ids')

    @api.depends('transaction_ids')
    def _compute_transaction_ids(self):
        for rec in self:
            tx = rec.transaction_ids.get_last_transaction()
            rec.payment_tx_status = tx and tx.state == 'done' and \
                tx.acquirer_id.provider == 'conekta'
