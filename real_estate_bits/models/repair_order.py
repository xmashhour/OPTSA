# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class Repair(models.Model):
    _inherit = 'repair.order'

    project_id = fields.Many2one('project.worksite', 'Main Property', copy=False)

    @api.onchange('project_id')
    def onchange_project(self):
        if self.project_id:
            units = self.env['product.template'].search(
                [('is_property', '=', True), ('project_worksite_id', '=', self.project_id.id)])
            products = self.env['product.product'].search([('product_tmpl_id', 'in', units.ids)])
            return {'domain': {'product_id': [('id', 'in', products.ids)]}}
