# -*- coding: utf-8 -*-
from . import models
from . import report

from odoo import api, SUPERUSER_ID


def _assign_default_invoice_field_ids(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids_without_default_invoice_field_ids  = env['res.company'].search([
        ('invoice_field_ids', '=', False)
    ])
    field_model = env['ir.model.fields'].sudo()
    default_invoice_field_ids = [
                (0,0, {
                    'sequence': 1,
                    'field_id': field_model.search([('name','=','partner_id'),('model_id.model','=','account.move')]).id,
                }),

                (0,0, {
                    'sequence': 2,
                    'field_id': field_model.search([('name','=','partner_vat'),('model_id.model','=','account.move')]).id,
                }),

                (0,0, {
                    'sequence': 3,
                    'field_id': field_model.search([('name','=','company_id'),('model_id.model','=','account.move')]).id,
                }),

                (0,0, {
                    'sequence': 4,
                    'field_id': field_model.search([('name','=','company_vat'),('model_id.model','=','account.move')]).id,
                }),
                (0,0, {
                    'sequence': 5,
                    'field_id': field_model.search([('name','=','datetime_invoice'),('model_id.model','=','account.move')]).id,
                }),
                (0,0, {
                    'sequence': 6,
                    'field_id': field_model.search([('name','=','amount_untaxed'),('model_id.model','=','account.move')]).id,
                }),
                (0,0, {
                    'sequence': 7,
                    'field_id': field_model.search([('name','=','amount_total'),('model_id.model','=','account.move')]).id,
                }),
            ]
    if default_invoice_field_ids:
        for company in company_ids_without_default_invoice_field_ids:
            company.write({
                'invoice_field_ids': default_invoice_field_ids,
            })

