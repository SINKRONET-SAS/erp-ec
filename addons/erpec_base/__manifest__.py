{
    'name': 'ERP EC — Estado de la suite',
    'version': '18.0.1.0.2',
    'license': 'Other proprietary',
    'author': 'SINKRONET S.A.S.',
    'depends': ['base', 'web', 'l10n_ec'],
    'data': ['security/ir.model.access.csv', 'views/workspace.xml', 'views/company.xml'],
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
}
