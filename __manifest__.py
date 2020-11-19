# -*- encoding: utf-8 -*-

{
    'name': 'FEL Guatefactura',
    'version': '1.0',
    'category': 'Custom',
    'description': """ Integración con factura electrónica de Guatefactura """,
    'author': 'aquíH',
    'website': 'http://aquih.com/',
    'depends': ['fel_gt'],
    'data': [
        'views/account_view.xml',
        'views/partner_view.xml',
        'views/product_view.xml',
    ],
    'demo': [],
    'installable': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
