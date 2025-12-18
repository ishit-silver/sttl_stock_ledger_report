{
    'name': 'STTL Stock Ledger Report',
    'summary': 'Generate Stock Ledger Report',
    'description': 'Generate Stock Ledger Report',
    'author': 'STTL',
    'depends': ['base', 'stock', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/menuitem.xml',
        'report/stock_pdf.xml',
        'views/wizard_form.xml',
        'views/report_action.xml',
    ],

    'installable': True,
    'application': True,
}
