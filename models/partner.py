# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

class Partner(models.Model):
    _inherit = 'res.partner'

    nit_especifico = fields.Char('NIT específico')
    numero_identificacion_fel = fields.Char('DPI o Pasaporte')
    pais_emision_fel = fields.Char('País de emisión')
    departamento_emision_fel = fields.Char('Departamento de emisión')
    municipio_emision_fel = fields.Char('Municipio de emisión')
