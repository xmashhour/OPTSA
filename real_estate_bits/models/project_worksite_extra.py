from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCategory(models.Model):
    _name = "project.worksite.category"
    _description = "Project Worksite Category"

    name = fields.Char()


class Amenities(models.Model):
    _name = "project.amenities"
    _description = "Project Amenities"

    name = fields.Char("Amenity", required=1)


class Utilities(models.Model):
    _name = "property.utilities"
    _description = "Utilities"

    name = fields.Char("Utility")
    price = fields.Float("Price")
    property_id = fields.Many2one("product.template")
    project_id = fields.Many2one("project.worksite")
