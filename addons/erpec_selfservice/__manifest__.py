{
    'name': 'ERP EC · Autoservicio de altas',
    'version': '18.0.2.1.0',
    'license': 'Other proprietary',
    'author': 'SINKRONET S.A.S.',
    'depends': ['erpec_payphone', 'portal', 'auth_signup', 'website'],
    'data': ['security/ir.model.access.csv', 'views.xml', 'templates.xml', 'data/commercial.xml'],
    'assets': {'web.assets_frontend': ['erpec_selfservice/static/src/commercial.scss']},
    'installable': True,
}
