# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class MaintenanceTask(models.TransientModel):
    _name = 'maintenance.task'
    _description = "Create Task from Maintenance"

    project_id = fields.Many2one('project.project',string="Project",required=True)
    title = fields.Char(required=True)
    user_ids = fields.Many2many('res.users', string='Assignees', context={'active_test': False}, tracking=True,required=True)
    date_deadline = fields.Date(string='Deadline', index=True, copy=False, tracking=True, task_dependency_tracking=True)
    planned_hours = fields.Float("Planned Hours", tracking=True)
    tag_ids = fields.Many2many('project.tags',string='Tags')
    description = fields.Html(string='Description', sanitize_attributes=False)

    def create_task(self):
        maintenance = self.env['maintenance.request'].browse(self._context.get('active_id'))
        data = {'name':self.title,'planned_hours':self.planned_hours,'project_id':self.project_id.id,'date_deadline':self.date_deadline,'user_ids':[(6,0, self.user_ids.ids)] or [],'tag_ids': [(6,0, self.tag_ids.ids)] or [],'maintenance_id':maintenance.id,'description':self.description}
        task = self.env['project.task'].create(data)
        return task
