# -*- coding: utf-8 -*-
{
    'name': "Stock Inventory Report",
    'summary': """
    An Inventory Report is a document created to track the quantity of goods that have been imported, exported, and remain in stock
       """,
    'description': """
     An Inventory Report is a document created to track the quantity of goods that have been imported, exported, and remain in stock. This report provides warehouse managers with the necessary information to manage and adjust the import and export of goods efficiently and meet customer demand. The information typically included in this report includes the quantity of inventory, the total value of inventory, the quantity of goods imported and the quantity of goods exported within a certain period of time.
    """,
    'depends': ['base', 'stock', 'product', 'purchase','sale','report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_inventory_report.xml',
        'views/templates.xml',
    ],

}
