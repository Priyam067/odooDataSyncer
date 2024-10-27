{
    'name': 'Odoo Data Sync',
    'version': '17.0.0.1.0',
    'summary': 'Synchronize odoo data between two Odoo instances.',
    'depends': ['base'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/odoo_data_sync_views.xml',
        'wizard/select_related_models_wizard.xml'
    ],
    'installable': True,
    'application': True,
}
