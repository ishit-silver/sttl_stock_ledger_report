import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError
from odoo import models, fields, api

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

    def action_generate_xlsx_report(self):
        self.ensure_one()  # Ensure it's a single record

        report_data = {
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M:%S') if self.start_date else False,
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M:%S') if self.end_date else False,
            'location_ids': [l.id for l in self.location_ids],
            'product_ids': [p.id for p in self.product_ids],
            'categ_ids': [c.id for c in self.categ_ids],
            'report_by': self.report_by,
        }

        return self.env.ref('sttl_stock_ledger_report.stock_ledger_report_xlsx').report_action(self, data=report_data)

