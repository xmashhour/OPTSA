# -*- coding: utf-8 -*-
# from odoo import http


# class OptCustomReport(http.Controller):
#     @http.route('/opt_custom_report/opt_custom_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/opt_custom_report/opt_custom_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('opt_custom_report.listing', {
#             'root': '/opt_custom_report/opt_custom_report',
#             'objects': http.request.env['opt_custom_report.opt_custom_report'].search([]),
#         })

#     @http.route('/opt_custom_report/opt_custom_report/objects/<model("opt_custom_report.opt_custom_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('opt_custom_report.object', {
#             'object': obj
#         })
