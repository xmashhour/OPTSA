# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name' : "Create Task from Maintenance Request | Quick Create Task from Maintenance | Convert Maintenance Requests into Project Tasks",
    'version' : "16.0.0.0",
    'category' : "Project",
    'summary': 'create project tasks from maintenance task integration convert maintenance into task creation from maintenance request to project task generation from maintenance Convert maintenance into tasks create task from maintenance task assignment from maintenance',
    'description' : '''Create Task from Maintenance Request Odoo App helps businesses to seamlessly convert maintenance requests into project tasks. This app enhances efficiency by eliminating the need for manual task creation, ensuring that maintenance-related activities are properly tracked and managed within project workflows. By linking maintenance requests directly to tasks, businesses can improve communication between teams, and monitor progress effectively.''',
    'author' : "BROWSEINFO",
    'website': 'https://www.browseinfo.com/demo-request?app=bi_task_from_maintenance&version=16&edition=Community',
    "currency": 'EUR',
    'depends' : ['maintenance','project','hr_timesheet'],
    'data': [
                "security/ir.model.access.csv",
                "views/maintenance_task_wizard.xml",
                "views/maintenance_request_view.xml",
             ],
    'auto_install': False,
    'installable': True,
    'live_test_url': "https://www.browseinfo.com/demo-request?app=bi_task_from_maintenance&version=16&edition=Community",
    'license': 'OPL-1',
    "images":['static/description/Banner.gif'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
