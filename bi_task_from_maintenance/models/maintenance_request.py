# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class ProjectTask(models.Model):
    _inherit = 'project.task'

    maintenance_id = fields.Many2one('maintenance.request')


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    task_count = fields.Integer('Tasks', compute='_compute_task')
    
    # count task generated from maintenance
    def _compute_task(self):
        self.task_count = self.env['project.task'].search_count([('maintenance_id','=',self.id)])
