# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    tipo_bien_fel = fields.Selection([('bien', 'Bien'), ('servicio', 'Servicio')])
