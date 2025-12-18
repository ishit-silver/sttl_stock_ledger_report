from odoo import http
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
from odoo.http import request


class DownloadXlsInventoryReports(http.Controller):

    @http.route('/web/stock_ledger_report/<model("stock.ledger.report.wizard"):model>',
                type='http', auth="user")
    @serialize_exception
    def download_inventory_report_xls(self, model, **kw):
        data = model.generate_stock_ledger_xlsx_report()

        filename = 'Stock Ledger Report'
        if not data:
            return request.not_found()
        else:
            return request.make_response(
                data,
                [('Content-Type', 'application/octet-stream'),
                 ('Content-Disposition', content_disposition(
                     filename + '.xlsx'))])