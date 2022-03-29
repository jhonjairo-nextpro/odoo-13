from odoo import fields, models, api, _


class ir_attachment(models.Model):
    _inherit = 'ir.attachment'

    sale_order_upload_id = fields.Many2one('sale.order', 'Sale Order Upload')


class sale_order(models.Model):
    _inherit = 'sale.order'

    def _get_sale_order_attachment_count(self):
        for order in self:
            attachment_ids = self.env['ir.attachment'].search([('sale_order_upload_id', '=', order.id)])
            order.sale_order_attachment_count = len(attachment_ids)

    sale_order_attachment_count = fields.Integer('Sale Order Attachments', compute='_get_sale_order_attachment_count')

    def attachment_on_sale_order_upload_button(self):

        self.ensure_one()
        return {
            'name': 'Attachment.Details',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'ir.attachment',
            'domain': [('sale_order_upload_id', '=', self.id)],

        }
