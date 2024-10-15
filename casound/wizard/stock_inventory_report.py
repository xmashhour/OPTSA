from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError
from odoo.http import request
import io
import xlsxwriter
from datetime import date


class StockInventoryReport(models.TransientModel):
    _name = "casound.stock_inventory_report.wizard"
    _description = "Stock Inventory Report"

    # Fields definition
    start_date = fields.Date(string="Start", required=True)
    end_date = fields.Date(string="End", required=True)
    location_ids = fields.Many2many(comodel_name='stock.location', domain=[], string='Locations')
    product_ids = fields.Many2many(comodel_name='product.product', string='Products')
    categ_ids = fields.Many2many(comodel_name='product.category', string='Categories')

    def get_average_cost_at_date(self, product_id, date):
        # Get the stock valuation layers for the product up to the specified date
        valuation_layers = self.env['stock.valuation.layer'].search([
            ('product_id', '=', product_id),
            ('create_date', '<', date)
        ], order='create_date')

        total_quantity = 0
        total_value = 0

        # Loop through valuation layers to calculate the total value and total quantity
        for layer in valuation_layers:
            total_quantity += layer.quantity
            total_value += layer.value

        # Calculate the average cost
        if total_quantity != 0:
            average_cost = total_value / total_quantity
        else:
            average_cost = 0  # Default to 0 if there is no stock

        return average_cost

    def get_average_cost_of_orders(self, moves):
        total_cost = 0
        total_orders = sum(moves.mapped('qty_done'))

        for move in moves:
            # Fetch the cost for each sales order
            total_cost += self.get_sales_order_cost_from_account_move(move)

        # Calculate average cost
        if total_orders > 0:
            average_cost = total_cost / total_orders
        else:
            average_cost = 0  # Handle cases where no orders are present

        return average_cost

    def get_sales_order_cost_from_account_move(self, move):
        total_cost = 0

        # Get all related account.move entries for this sale order
        account_moves = move.mapped('move_id.account_move_ids').filtered(lambda move: move.state == 'posted')

        # Loop through account.move.lines and sum up the cost from the expense (COGS) account
        for move in account_moves:
            for line in move.line_ids:
                if line.account_id.account_type == 'expense':
                    total_cost += line.debit  # COGS is usually on the debit side
                else:
                    total_cost += line.credit

        return total_cost

    def print_report(self):
        product_type = "product"
        user_id = request.session.uid
        user = request.env['res.users'].browse(user_id)

        # Defining the domain for product search
        domain = [('active', '=', True), ('detailed_type', '=', product_type)]
        if self.product_ids:
            domain.append(('id', 'in', self.product_ids.ids))
        if self.categ_ids:
            domain.append(('categ_id', 'in', self.categ_ids.ids))

        products = self.env['product.product'].search(domain)
        initial_stock_total = 0
        final_stock_total = 0
        change_in_stock_total = 0
        initial_value_total = 0
        final_value_total = 0
        change_in_value_total = 0
        total_sales_qty = 0
        total_sales_value = 0
        total_po_qty = 0
        total_po_value = 0

        product_list = []
        for product in products:
            # Example data fetching logic, adjust as needed
            StockQuant = self.env['stock.quant']
            if self.location_ids:
                initial_stock_in = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '<', self.start_date),
                    ('location_id.usage', 'not in', ('internal', 'transit')),
                    ('location_dest_id.usage', 'in', ('internal', 'transit'))
                    , '|'
                    ('location_id', 'in', self.location_ids.id)
                    ('location_dest_id', 'in', self.location_ids.id)
                ])
                initial_stock_in = sum(initial_stock_in.mapped('qty_done'))
                initial_stock_out = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '<', self.start_date),
                    ('location_id.usage', 'in', ('internal', 'transit')),
                    ('location_dest_id.usage', 'not in', ('internal', 'transit')),
                    '|'
                    ('location_id', 'in', self.location_ids.id)
                    ('location_dest_id', 'in', self.location_ids.id)
                ])
                initial_stock_out = sum(initial_stock_out.mapped('qty_done'))

                initial_stock = initial_stock_in - initial_stock_out
            else:
                initial_stock_in = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '<', self.start_date),
                    ('location_id.usage', 'not in', ('internal', 'transit')),
                    ('location_dest_id.usage', 'in', ('internal', 'transit'))
                ])
                initial_stock_in = sum(initial_stock_in.mapped('qty_done'))
                initial_stock_out = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '<', self.start_date),
                    ('location_id.usage', 'in', ('internal', 'transit')),
                    ('location_dest_id.usage', 'not in', ('internal', 'transit'))
                ])
                initial_stock_out = sum(initial_stock_out.mapped('qty_done'))

                initial_stock = initial_stock_in - initial_stock_out

            initial_cost = self.get_average_cost_at_date(product.id, self.start_date)
            # initial_value=initial_stock * product.standard_price
            initial_value = initial_stock * initial_cost
            if self.location_ids:
                po_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.origin_returned_move_id', '=', False),
                    ('picking_id.picking_type_id.code', '=', 'incoming')
                    , ('location_id', 'in', self.location_ids.ids)
                ])
                return_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.origin_returned_move_id', '!=', False),
                    ('picking_id.picking_type_id.code', '=', 'outgoing')
                    , ('location_id', 'in', self.location_ids.ids)
                ])

                sale_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.sale_line_id', '!=', False),
                    ('move_id.origin_returned_move_id', '=', False),
                    ('picking_id.picking_type_id.code', '=', 'outgoing')
                    , ('location_id', 'in', self.location_ids.ids)
                ])
                return_so_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.origin_returned_move_id', '!=', False),
                    ('picking_id.picking_type_id.code', '=', 'incoming')
                    , ('location_id', 'in', self.location_ids.ids)
                ])

                change_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('location_dest_id.usage', '=', 'inventory')
                    , ('location_id', 'in', self.location_ids.ids)
                ])
                change_lines2 = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('location_id.usage', '=', 'inventory')
                    , ('location_id', 'in', self.location_ids.ids)
                ])

            else:
                po_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.origin_returned_move_id', '=', False),
                    ('picking_id.picking_type_id.code', '=', 'incoming')
                ])
                return_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.origin_returned_move_id', '!=', False),
                    ('picking_id.picking_type_id.code', '=', 'outgoing')
                ])

                sale_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.sale_line_id', '!=', False),
                    ('move_id.origin_returned_move_id', '=', False),
                    ('picking_id.picking_type_id.code', '=', 'outgoing')
                ])
                return_so_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('move_id.origin_returned_move_id', '!=', False),
                    ('picking_id.picking_type_id.code', '=', 'incoming')
                ])

                change_lines = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('location_dest_id.usage', '=', 'inventory')
                ])
                change_lines2 = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                    ('location_id.usage', '=', 'inventory')
                ])

            sales_qty = sum(sale_lines.mapped('qty_done'))
            return_sales_qty = sum(return_so_lines.mapped('qty_done'))
            # sale_lines=sale_lines.mapped(lambda line: line.qty_done * line.product_id.standard_price)
            # avg_sales_price =sum(sale_lines) / len(sale_lines) if sale_lines else 0
            avg_sales_price = self.get_average_cost_of_orders(sale_lines)
            sales_qty -= return_sales_qty
            sales_value = sales_qty * avg_sales_price
            po_qty = sum(po_lines.mapped('qty_done'))
            return_po_qty = sum(return_lines.mapped('qty_done'))
            # po_lines=po_lines.mapped(lambda line: line.qty_done * line.move_id.purchase_line_id.price_unit)
            # avg_po_price =sum(po_lines) / po_qty if po_qty>0 else 0
            avg_po_price = self.get_average_cost_of_orders(po_lines)
            print("avg_po_price", avg_po_price)
            po_qty -= return_po_qty
            po_value = avg_po_price * po_qty
            change_in_stock = sum(change_lines.mapped('qty_done'))
            change_price = self.get_average_cost_of_orders(change_lines)
            change_in_value = change_in_stock * change_price

            change_in_stock2 = -1 * sum(change_lines2.mapped('qty_done'))
            change_in_value2 = -1 * change_in_stock * self.get_average_cost_of_orders(change_lines2)

            change_in_stock = change_in_stock + change_in_stock2
            change_in_value = change_in_value + change_in_value2

            final_stock = initial_stock + po_qty - sales_qty - change_in_stock
            final_value = product.standard_price * final_stock

            product_list.append({
                'name': product.name,
                'nsn': product.default_code,
                'code': product.barcode,
                'uom': product.uom_id.name,
                'initial_stock': initial_stock,
                'cost_price': product.standard_price,
                'initial_cost': initial_cost,
                'initial_value': initial_value,
                'po_qty': po_qty,
                'po_value': po_value,
                'avg_po_price': avg_po_price,
                'change_in_stock': change_in_stock,
                'change_price': change_price,
                'change_in_value': change_in_value,
                'sales_qty': sales_qty,
                'list_price': product.list_price,
                'sales_value': sales_value,
                'avg_sales_price': avg_sales_price,
                'final_stock': final_stock,
                'final_value': final_value,
            })
            initial_stock_total += initial_stock
            final_stock_total += final_stock
            change_in_stock_total += change_in_stock
            initial_value_total += initial_value
            final_value_total += final_value
            change_in_value_total += change_in_value
            total_sales_qty += sales_qty
            total_sales_value += sales_value
            total_po_qty += po_qty
            total_po_value += po_value

        # Append totals to the product list for final row
        product_list.append({
            'name': 'Total',
            'initial_stock': initial_stock_total,
            'final_stock': final_stock_total,
            'change_in_stock': change_in_stock_total,
            'initial_value': initial_value_total,
            'final_value': final_value_total,
            'cost_price': 0,
            'avg_po_price': 0,
            'change_price': 0,
            'avg_sales_price': 0,
            'change_in_value': change_in_value_total,
            'sales_qty': total_sales_qty,
            'sales_value': total_sales_value,
            'po_qty': total_po_qty,
            'po_value': total_po_value,
        })

        return {'product_list': product_list}

    def export_to_excel(self):
        report = self.env.ref('casound.action_stock_inventory_report')
        return report.report_action(self, data={})



class StockInventoryReport(models.AbstractModel):
    _name = 'report.casound.stock_inventory_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wiz):
        worksheet = workbook.add_worksheet('Stock Inventory Report')

        # Set up the formats
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        header_format2 = workbook.add_format({'bold': True, 'border': 1, 'align': 'center','bg_color':"orange"})
        cell_format = workbook.add_format({'border': 1})

        worksheet.write(0, 0, "Item Description", cell_format)
        worksheet.write(0, 1, "OB Qty", cell_format)
        worksheet.write(0, 2, "OB Value", cell_format)
        worksheet.write(0, 3, "Qty In", cell_format)
        worksheet.write(0, 4, "Value In", cell_format)
        worksheet.write(0, 5, "Qty Out", cell_format)
        worksheet.write(0, 6, "Value Out", cell_format)
        worksheet.write(0, 7, " Quantity", cell_format)
        worksheet.write(0, 8, " Bal Value", cell_format)

        # Header row
        headers = [
            '', 'Opeining Balance', ' Opeining Value', 'Receving Quantity', 'Receving Value', 'Delivery Quantity',
            'Delivery Value', 'Remaing Quantity', 'Remaing Value'
        ]
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, header_format2)

        column_widths = [20, 15, 20, 10, 15, 15, 15, 10, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 20, 20, 30]
        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width)  # Set width for each column

        # Fetch data
        data = wiz.print_report()
        product_list = data['product_list']

        # Writing data rows
        for row_num, product in enumerate(product_list, start=2):
            if product['name']=='Total':
                worksheet.write(row_num, 0, product['name'], cell_format)
                worksheet.write(row_num, 1, product['initial_stock'], cell_format)
                worksheet.write(row_num, 2, product['initial_value'], cell_format)
                worksheet.write(row_num, 3, product['po_qty'], cell_format)
                worksheet.write(row_num, 4, product['po_value'], cell_format)
                worksheet.write(row_num, 5, product['sales_qty'] + product['change_in_stock'], cell_format)
                worksheet.write(row_num, 6, product['sales_value'] + product['change_in_value'], cell_format)
                worksheet.write(row_num, 7, product['final_stock'], cell_format)
                worksheet.write(row_num, 8, product['final_value'], cell_format)

            else:
                worksheet.write(row_num, 0, product['name'], cell_format)
                worksheet.write(row_num, 1, product['initial_stock'], cell_format)
                worksheet.write(row_num, 2, product['initial_value'], cell_format)
                worksheet.write(row_num, 3, product['po_qty'], cell_format)
                worksheet.write(row_num, 4, product['po_value'], cell_format)
                worksheet.write(row_num, 5, product['sales_qty']+product['change_in_stock'], cell_format)
                worksheet.write(row_num, 6, product['sales_value']+product['change_in_value'], cell_format)
                worksheet.write(row_num, 7, product['final_stock'], cell_format)
                worksheet.write(row_num, 8, product['final_value'], cell_format)