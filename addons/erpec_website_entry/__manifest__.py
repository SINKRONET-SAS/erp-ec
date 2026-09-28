{
    'name': 'ERP EC — Entrada pública del sitio',
    'version': '18.0.1.1.0',
    'license': 'Other proprietary',
    'author': 'SINKRONET S.A.S.',
    'depends': ['erpec_workspace', 'website', 'erpec_data_protection', 'erpec_selfservice'],
    'data': ['rights_templates.xml', 'data.xml'],
    'assets': {'web.assets_frontend': ['erpec_website_entry/static/src/entry.scss']},
    'auto_install': True,
    'installable': True,
}
