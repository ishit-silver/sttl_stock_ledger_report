from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockLedgerReportPDF(models.AbstractModel):
    _name = 'report.sttl_stock_ledger_report.stock_ledger_report_template'
    _description = 'Stock Ledger PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Get the report data using the helper model
        report_data = self.env['stock.ledger.report.helper'].get_report_data(data)

        if not isinstance(report_data, list):
            report_data = []


        # Make sure we're using the correct model name
        model = 'stock.ledger.report.wizard'

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data,
            'docs': self.env[model].browse(docids),
            'report_data': report_data,
        }