{
    'name': 'STTL Stock Ledger Report',
    'summary': 'Generate Stock Ledger Report',
    'description': 'Generate Stock Ledger Report',
    'author': 'Silver Touch Technologies Limited',
    'depends': ['base', 'stock', 'report_xlsx', 'mrp'],

    'data': [
        'security/ir.model.access.csv',
        'views/menuitem.xml',
        'report/stock_pdf.xml',
        'views/wizard_form.xml',
        'views/report_action.xml',
        'report/ir_actions_report.xml',
    ],

    'images': ['static/description/banner.png'],

    'installable': True,
    'application': True,
}
