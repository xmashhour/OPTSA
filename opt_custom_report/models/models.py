# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Invoice(models.Model):
    _inherit = 'account.move'

    type_of_sale = fields.Char(string="Type Of Sale", required=False, )
    po_no = fields.Char(string="Po No", required=False, )
