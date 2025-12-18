import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError
from odoo import models, fields, api
from io import BytesIO
import xlsxwriter

_logger = logging.getLogger(__name__)


class StockLedgerReportWizard(models.TransientModel):
    _name = 'stock.ledger.report.wizard'
    _description = 'Stock Ledger Report Wizard'

    report_by = fields.Boolean('Location')
    date = fields.Date(string='Date')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    location_ids = fields.Many2many('stock.location', string='Location', required=True, domain="[('usage', 'in', ['internal', 'transit'])]")

    product_ids = fields.Many2many('product.product', string='Product')
    categ_ids = fields.Many2many('product.category', string='Product Category')

    def print_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/stock_ledger_report/%s' % (self.id),
            'target': 'new',
        }

    def generate_stock_ledger_xlsx_report(self):
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        sheet = workbook.add_worksheet("Stock Ledger Report")
        bold = workbook.add_format({'bold': True})

        headers = [
            'Date', 'Product', 'Category','Location',
            'Opening Stock', 'Sale', 'Purchase', 'Sales Return', 'Purchase Return',
            'Internal In', 'Internal Out', 'Transit In', 'Transit Out',
            'Production In', 'Production Out', 'Adjustment In', 'Adjustment Out',
            'Closing Stock'
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)
            width = max(len(header), 10)  # minimum width of 15
            sheet.set_column(col, col, width)

        data = {
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M:%S') if self.start_date else False,
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M:%S') if self.end_date else False,
            'location_ids': [l.id for l in self.location_ids],
            'product_ids': [p.id for p in self.product_ids],
            'categ_ids': [c.id for c in self.categ_ids],
            'report_by': self.report_by,
        }
        results = self.env['stock.ledger.report.helper'].get_report_data(data)

        if not isinstance(results, list):
            results = []

        if not results:
            sheet.write(1, 0, "No data found matching the selected criteria.")
            return

        row = 1
        for res in results:
            sheet.write(row, 0, str(res['date']))
            sheet.write(row, 1, res['product_name'])
            sheet.write(row, 2, res['category_name'])
            sheet.write(row, 3, res['location_name'])
            sheet.write(row, 4, res['opening_qty'])
            sheet.write(row, 5, res['sale_qty'])
            sheet.write(row, 6, res['purchase_qty'])
            sheet.write(row, 7, res['sale_return_qty'])
            sheet.write(row, 8, res['purchase_return_qty'])
            sheet.write(row, 9, res['internal_in_qty'])
            sheet.write(row, 10, res['internal_out_qty'])
            sheet.write(row, 11, res['transit_in_qty'])
            sheet.write(row, 12, res['transit_out_qty'])
            sheet.write(row, 13, res['production_in_qty'])
            sheet.write(row, 14, res['production_out_qty'])
            sheet.write(row, 15, res['adjustment_in_qty'])
            sheet.write(row, 16, res['adjustment_out_qty'])
            sheet.write(row, 17, res['closing_qty'])
            row += 1

        workbook.close()
        return fp.getvalue()

    def action_generate_pdf_report(self):
        self.ensure_one()  # Ensure it's a single record

        # Use the same report_data as in action_generate_xlsx_report
        report_data = {
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M:%S') if self.start_date else False,
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M:%S') if self.end_date else False,
            'location_ids': [l.id for l in self.location_ids],
            'product_ids': [p.id for p in self.product_ids],
            'categ_ids': [c.id for c in self.categ_ids],
            'report_by': self.report_by,
        }

        # Call the new PDF report
        return self.env.ref('sttl_stock_ledger_report.stock_ledger_report_pdf').report_action(self, data=report_data)
