{
    'name': 'ERP EC · PayPhone',
    'version': '18.0.1.1.1',
    'license': 'Other proprietary',
    'depends': ['erpec_provision', 'erpec_secrets'],
    'data': ['security/ir.model.access.csv', 'views/payphone.xml', 'data/cron.xml'],
    'installable': True,
}
