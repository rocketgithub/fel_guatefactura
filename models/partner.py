# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

class Partner(models.Model):
    _inherit = 'res.partner'

    nit_especifico = fields.Char('Nit específico')
