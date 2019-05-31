# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

#import odoo.addons.l10n_gt_extra.a_letras

from datetime import datetime
from lxml import etree
import base64
import logging
from requests import Session
from requests.auth import HTTPBasicAuth
import zeep
from zeep.transports import Transport

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    firma_fel = fields.Char('Firma FEL', copy=False)
    # pdf_fel = fields.Binary('PDF FEL', copy=False)
    serie_fel = fields.Char('Serie FEL', copy=False)
    numero_fel = fields.Char('Numero FEL', copy=False)
    nombre_cliente_fel = fields.Char('Nombre Cliente FEL', copy=False)
    direccion_cliente_fel = fields.Char('Nombre Cliente FEL', copy=False)
    telefono_cliente_fel = fields.Char('Nombre Cliente FEL', copy=False)
    factura_original_id = fields.Many2one('account.invoice', string="Factura original FEL")

    def invoice_validate(self):
        detalles = []
        subtotal = 0
        for factura in self:
            if factura.journal_id.usuario_fel and not factura.firma_fel and factura.amount_total != 0:

                DocElectronico = etree.Element("DocElectronico")

                Encabezado = etree.SubElement(DocElectronico, "Encabezado")

                Receptor = etree.SubElement(Encabezado, "Receptor")
                NITReceptor = etree.SubElement(Receptor, "NITReceptor")
                NITReceptor.text = factura.partner_id.vat.replace('-','')
                if factura.partner_id.vat == "C/F":
                    Nombre = etree.SubElement(Receptor, "Nombre")
                    Nombre.text = factura.partner_id.name
                    Direccion = etree.SubElement(Receptor, "Direccion")
                    Direccion.text = factura.partner_id.street or "."

                InfoDoc = etree.SubElement(Encabezado, "InfoDoc")

                TipoVenta = etree.SubElement(InfoDoc, "TipoVenta")
                TipoVenta.text = "B" if factura.tipo_gasto == "compra" else "S"
                DestinoVenta = etree.SubElement(InfoDoc, "DestinoVenta")
                DestinoVenta.text = "1"
                Fecha = etree.SubElement(InfoDoc, "Fecha")
                Fecha.text = fields.Date.from_string(factura.date_invoice).strftime("%d/%m/%Y")
                Moneda = etree.SubElement(InfoDoc, "Moneda")
                Moneda.text = "1"
                Tasa = etree.SubElement(InfoDoc, "Tasa")
                Tasa.text = "1"
                Referencia = etree.SubElement(InfoDoc, "Referencia")
                Referencia.text = str(10000+factura.id)
                Referencia = etree.SubElement(InfoDoc, "NumeroAcceso")
                Referencia = etree.SubElement(InfoDoc, "SerieAdmin")
                Referencia = etree.SubElement(InfoDoc, "NumeroAdmin")
                Referencia = etree.SubElement(InfoDoc, "Reversion")

                Totales = etree.SubElement(Encabezado, "Totales")

                Bruto = etree.SubElement(Totales, "Bruto")
                Bruto.text = "%.2f" % factura.amount_total
                Descuento = etree.SubElement(Totales, "Descuento")
                Descuento.text = "0"
                Exento = etree.SubElement(Totales, "Exento")
                Exento.text = "0"
                Otros = etree.SubElement(Totales, "Otros")
                Otros.text = "0"
                Neto = etree.SubElement(Totales, "Neto")
                Neto.text = "%.2f" % factura.amount_untaxed
                Isr = etree.SubElement(Totales, "Isr")
                Isr.text = "0"
                Iva = etree.SubElement(Totales, "Iva")
                Iva.text = "%.2f" % (factura.amount_total - factura.amount_untaxed)
                Total = etree.SubElement(Totales, "Total")
                Total.text = "%.2f" % factura.amount_total

                subtotal = 0
                total = 0
                Detalles = etree.SubElement(DocElectronico, "Detalles")
                for linea in factura.invoice_line_ids:
                    if linea.price_unit != 0 and linea.quantity != 0:
                        precio_unitario = linea.price_unit * (100-linea.discount) / 100
                        precio_unitario_base = linea.price_subtotal / linea.quantity

                        total_linea = precio_unitario * linea.quantity
                        total_linea_base = precio_unitario_base * linea.quantity

                        total_impuestos = total_linea - total_linea_base
                        tasa = "12" if total_impuestos > 0 else "0"

                        Productos = etree.SubElement(Detalles, "Productos")

                        Producto = etree.SubElement(Productos, "Producto")
                        # Producto.text = linea.product_id.default_code or "-"
                        Producto.text = 'P'+str(linea.product_id.id)
                        Descripcion = etree.SubElement(Productos, "Descripcion")
                        Descripcion.text = linea.name
                        Medida = etree.SubElement(Productos, "Medida")
                        Medida.text = "1"
                        Cantidad = etree.SubElement(Productos, "Cantidad")
                        Cantidad.text = str(linea.quantity)
                        Precio = etree.SubElement(Productos, "Precio")
                        Precio.text = "%.2f" % precio_unitario
                        PorcDesc = etree.SubElement(Productos, "PorcDesc")
                        PorcDesc.text = "0"
                        ImpBruto = etree.SubElement(Productos, "ImpBruto")
                        ImpBruto.text = "%.2f" % total_linea
                        ImpDescuento = etree.SubElement(Productos, "ImpDescuento")
                        ImpDescuento.text = "0"
                        ImpExento = etree.SubElement(Productos, "ImpExento")
                        ImpExento.text = "0"
                        ImpOtros = etree.SubElement(Productos, "ImpOtros")
                        ImpOtros.text = "0"
                        ImpNeto = etree.SubElement(Productos, "ImpNeto")
                        ImpNeto.text = "%.2f" % total_linea_base
                        ImpIsr = etree.SubElement(Productos, "ImpIsr")
                        ImpIsr.text = "0"
                        ImpIva = etree.SubElement(Productos, "ImpIva")
                        ImpIva.text = "%.2f" % (total_linea - total_linea_base)
                        ImpTotal = etree.SubElement(Productos, "ImpTotal")
                        ImpTotal.text = "%.2f" % total_linea
                        DatosAdicionalesProd = etree.SubElement(Productos, "DatosAdicionalesProd")
                        TipoVentaDet = etree.SubElement(Productos, "TipoVentaDet")
                        TipoVentaDet.text = "B" if linea.product_id.type == "product" else "S"

                        total += total_linea
                        subtotal += total_linea_base

                DocAsociados = etree.SubElement(Detalles, "DocAsociados")
                DASerie = etree.SubElement(DocAsociados, "DASerie")
                if factura.journal_id.tipo_documento_fel > 1:
                    DASerie.text = factura.factura_original_id.serie_fel
                DAPreimpreso = etree.SubElement(DocAsociados, "DAPreimpreso")
                if factura.journal_id.tipo_documento_fel > 1:
                    DAPreimpreso.text = factura.factura_original_id.numero_fel

                xmls = etree.tostring(DocElectronico, xml_declaration=True, encoding="UTF-8", pretty_print=True)
                logging.warn(xmls)

                session = Session()
                session.verify = False
                session.auth = HTTPBasicAuth('usr_guatefac', 'usrguatefac')
                session.http_auth = HTTPBasicAuth('usr_guatefac', 'usrguatefac')
                session.headers.update({'Authorization': 'Basic dXNyX2d1YXRlZmFjOnVzcmd1YXRlZmFj'})
                transport = Transport(session=session)
                # wsdl = 'https://pdte.guatefacturas.com/webservices63/feltest/Guatefac?WSDL'
                wsdl = 'https://pdte.guatefacturas.com/webservices63/fel/Guatefac'
                client = zeep.Client(wsdl=wsdl, transport=transport)

                resultado = client.service.generaDocumento(factura.journal_id.usuario_fel, factura.journal_id.clave_fel, factura.journal_id.nit_fel, factura.journal_id.establecimiento_fel, factura.journal_id.tipo_documento_fel, factura.journal_id.id_maquina_fel, "R", xmls)
                resultado = resultado.replace("&", "&amp;")
                logging.warn(resultado)
                resultadoXML = etree.XML(resultado)

                if len(resultadoXML.xpath("//NumeroAutorizacion")) > 0:
                    numero = resultadoXML.xpath("//Serie")[0].text+'-'+resultadoXML.xpath("//Preimpreso")[0].text
                    factura.firma_fel = resultadoXML.xpath("//NumeroAutorizacion")[0].text
                    factura.name = numero
                    factura.serie_fel = resultadoXML.xpath("//Serie")[0].text
                    factura.numero_fel = resultadoXML.xpath("//Preimpreso")[0].text
                    factura.nombre_cliente_fel = resultadoXML.xpath("//Nombre")[0].text
                    factura.direccion_cliente_fel = resultadoXML.xpath("//Direccion")[0].text
                else:
                    raise UserError(resultadoXML.xpath("//Resultado")[0].text)

        return super(AccountInvoice,self).invoice_validate()

class AccountJournal(models.Model):
    _inherit = "account.journal"

    usuario_fel = fields.Char('Usuario FEL', copy=False)
    clave_fel = fields.Char('Clave FEL', copy=False)
    nit_fel = fields.Char('NIT FEL', copy=False)
    establecimiento_fel = fields.Char('Establecimiento FEL', copy=False)
    tipo_documento_fel = fields.Integer('Tipo de Documento FEL', copy=False)
    id_maquina_fel = fields.Integer('ID Maquina FEL', copy=False)
    # serie_fel = fields.Char('Serie FEL', copy=False)
    # numero_resolucion_fel = fields.Char('Numero Resolución FEL', copy=False)
    # fecha_resolucion_fel = fields.Date('Fecha Resolución FEL', copy=False)
    # rango_inicial_fel = fields.Integer('Rango Inicial FEL', copy=False)
    # rango_final_fel = fields.Integer('Rango Final FEL', copy=False)
    # dispositivo_fel = fields.Char('Dispositivo FEL', copy=False)
    # nombre_documento_fel = fields.Selection([('Factura', 'Factura'), ('Nota de crédito', 'Nota de crédito'), ('Nota de débito', 'Nota de débito')], 'Tipo de Documento FEL', copy=False)
