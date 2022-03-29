import odoo.http as http
from odoo.http import request
import base64


class SaleOrderFileUpload(http.Controller):

    @http.route('/shop/payment/sale_order_attachment/add', type='http', auth="public", website=True)
    def sale_order_attachment_add(self, url=None, upload=None, **post):

        cr, uid, context = request.cr, request.uid, request.context

        order = request.website.sale_get_order()

        Attachments = request.env['ir.attachment'].sudo()  # registry for the attachment table

        upload_file = request.httprequest.files.getlist('upload')

        if upload_file:
            for i in range(len(upload_file)):
                attachment_id = Attachments.create({
                    'name': upload_file[i].filename,
                    'type': 'binary',
                    'datas': base64.b64encode(upload_file[i].read()),
                    'name': upload_file[i].filename,
                    'public': True,
                    'res_model': 'ir.ui.view',
                    'sale_order_upload_id': order.id,
                })

            return request.redirect('/shop/payment')
