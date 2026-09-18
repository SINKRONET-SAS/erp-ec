{
    'name': 'ERP EC — Facturación nativa: firma y transmisión SRI',
    'version': '18.0.1.3.0',
    'license': 'Other proprietary',
    'author': 'SINKRONET S.A.S.',
    'depends': ['erpec_fiscal_native'],
    'external_dependencies': {'python': ['zeep', 'reportlab']},
    'data': ['security/ir.model.access.csv', 'security/security.xml', 'views.xml', 'data/cron.xml'],
    'installable': True,
}
