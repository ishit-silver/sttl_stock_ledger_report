from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class StockLedgerXlsxReport(models.AbstractModel):
    _name = 'report.sttl_stock_ledger_report.stock_ledger_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard):
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

        # Get data using the helper model
        stock_ledger_data = self.env['stock.ledger.report.helper']
        results = stock_ledger_data.get_report_data(data)

        if not isinstance(results, list):
            results = []

        if not results:
            sheet.write(1, 0, "No data found matching the selected criteria.")
            return

        # Write data to worksheet
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
