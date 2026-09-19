{
    'name': 'ERP EC — Almacén de secretos cifrados',
    'version': '18.0.2.0.0',
    'license': 'Other proprietary',
    'author': 'SINKRONET S.A.S.',
    'summary': 'Cifrado en reposo (Fernet) con clave fuera de la base de datos y rotación de clave, compartido por los módulos con credenciales.',
    'depends': ['base'],
    'data': ['security/ir.model.access.csv', 'views.xml'],
    'installable': True,
}
