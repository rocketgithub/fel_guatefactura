# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

import datetime
from lxml import etree
import base64
import logging
from requests import Session
from requests.auth import HTTPBasicAuth
import zeep
from zeep.transports import Transport
import html

class AccountInvoice(models.Model):
    _inherit = "account.move"

    nombre_cliente_fel = fields.Char('Nombre Cliente FEL', copy=False)
    direccion_cliente_fel = fields.Char('Dirección Cliente FEL', copy=False)
    telefono_cliente_fel = fields.Char('Telefono Cliente FEL', copy=False)
    destino_venta_fel = fields.Char('Destino Venta FEL', copy=False)
    
    def _post(self, soft=True):
        if self.certificar():
            return super(AccountMove, self)._post(soft)

    def post(self):
        if self.certificar():
            return super(AccountMove, self).post()

    def certificar(self):
        for factura in self:
            if factura.requiere_certificacion():
                self.ensure_one()

                if factura.error_pre_validacion():
                    return
                    
                DocElectronico = etree.Element("DocElectronico")
                Encabezado = etree.SubElement(DocElectronico, "Encabezado")
                Receptor = etree.SubElement(Encabezado, "Receptor")

                NITReceptor = etree.SubElement(Receptor, "NITReceptor")
                if factura.journal_id.tipo_documento_fel == 5:
                    NITReceptor.tag = "NITVendedor"

                nit = factura.partner_id.vat
                NITReceptor.text = nit.replace('-','')
                if nit == "CF":
                    Nombre = etree.SubElement(Receptor, "Nombre")
                    if factura.journal_id.tipo_documento_fel == 5:
                        Nombre.tag = "NombreVendedor"

                    Nombre.text = factura.partner_id.name
                    if factura.partner_id.nombre_facturacion_fel:
                        Nombre.text = factura.partner_id.nombre_facturacion_fel
                    Direccion = etree.SubElement(Receptor, "Direccion")
                    Direccion.text = factura.partner_id.street or "."

                InfoDoc = etree.SubElement(Encabezado, "InfoDoc")

                TipoVenta = etree.SubElement(InfoDoc, "TipoVenta")
                TipoVenta.text = "B" if factura.tipo_gasto == "compra" else "S"
                DestinoVenta = etree.SubElement(InfoDoc, "DestinoVenta")
                DestinoVenta.text = factura.destino_venta_fel if factura.destino_venta_fel else "1"
                Fecha = etree.SubElement(InfoDoc, "Fecha")
                Fecha.text = factura.invoice_date.strftime("%d/%m/%Y") if factura.invoice_date else fields.Date.context_today(self).strftime("%d/%m/%Y")
                Moneda = etree.SubElement(InfoDoc, "Moneda")
                Moneda.text = "1" if factura.currency_id.id == factura.company_id.currency_id.id else "2"
                Tasa = etree.SubElement(InfoDoc, "Tasa")
                Tasa.text = "1" if factura.currency_id.id == factura.company_id.currency_id.id else str(factura.company_id.currency_id.rate/factura.currency_id.rate)

                if factura.journal_id.tipo_documento_fel == 5:
                    TipoDocIdentificacion = etree.SubElement(InfoDoc, "TipoDocIdentificacion")
                    TipoDocIdentificacion.text = "2"
                    NumeroIdentificacion = etree.SubElement(InfoDoc, "NumeroIdentificacion")
                    NumeroIdentificacion.text = factura.partner_id.cui
                    PaisEmision = etree.SubElement(InfoDoc, "PaisEmision")
                    PaisEmision.text = factura.partner_id.pais_emision_fel
                    DepartamentoEmision = etree.SubElement(InfoDoc, "DepartamentoEmision")
                    DepartamentoEmision.text = factura.partner_id.departamento_emision_fel
                    MunicipioEmision = etree.SubElement(InfoDoc, "MunicipioEmision")
                    MunicipioEmision.text = factura.partner_id.municipio_emision_fel
                    PorcISR = etree.SubElement(InfoDoc, "PorcISR")
                    PorcISR.text = "0.05"

                Referencia = etree.SubElement(InfoDoc, "Referencia")
                Referencia.text = str(factura.id)
                NumeroAcceso = etree.SubElement(InfoDoc, "NumeroAcceso")
                NumeroAcceso.text = str(factura.id+100000000)
                SerieAdmin = etree.SubElement(InfoDoc, "SerieAdmin")
                SerieAdmin.text = ""
                NumeroAdmin = etree.SubElement(InfoDoc, "NumeroAdmin")
                NumeroAdmin.text = ""
                Reversion = etree.SubElement(InfoDoc, "Reversion")

                total_exento = 0
                total_neto = 0
                total_con_impuestos = 0
                total_sin_impuestos = 0
                for linea in factura.invoice_line_ids:
                    precio_unitario = linea.price_unit * (100-linea.discount) / 100
                    precio_unitario_base = linea.price_subtotal / linea.quantity

                    total_linea = factura.currency_id.round(precio_unitario * linea.quantity)
                    total_linea_base = factura.currency_id.round(precio_unitario_base * linea.quantity)

                    total_linea_impuestos = factura.currency_id.round(total_linea - total_linea_base)

                    total_con_impuestos += total_linea
                    total_sin_impuestos += total_linea_base
                    if total_linea_impuestos > 0:
                        total_neto += total_linea_base
                    else:
                        total_exento += total_linea

                total_isr = 0
                if factura.journal_id.tipo_documento_fel == 5:
                    total_isr += abs(factura.amount_tax)

                Totales = etree.SubElement(Encabezado, "Totales")

                Bruto = etree.SubElement(Totales, "Bruto")
                Bruto.text = "%.2f" % total_con_impuestos
                Descuento = etree.SubElement(Totales, "Descuento")
                Descuento.text = "0"
                Exento = etree.SubElement(Totales, "Exento")
                Exento.text = "%.2f" % total_exento
                Otros = etree.SubElement(Totales, "Otros")
                Otros.text = "0"
                Neto = etree.SubElement(Totales, "Neto")
                Neto.text = "%.2f" % total_neto
                Isr = etree.SubElement(Totales, "Isr")
                Isr.text = str(total_isr)
                Iva = etree.SubElement(Totales, "Iva")
                Iva.text = "%.2f" % (total_con_impuestos - total_sin_impuestos)
                Total = etree.SubElement(Totales, "Total")
                Total.text = "%.2f" % total_con_impuestos
                
                if factura.tipo_gasto == 'importacion':
                    DatosAdicionales = etree.SubElement(Encabezado, "DatosAdicionales")
                    INCOTERM = etree.SubElement(DatosAdicionales, "INCOTERM")
                    INCOTERM.text = factura.incoterm_fel or "-"
                    DESTINATARIO = etree.SubElement(DatosAdicionales, "DESTINATARIO")
                    DESTINATARIO.text = factura.consignatario_fel.name if factura.consignatario_fel else "-"
                    CODIGODESTINA = etree.SubElement(DatosAdicionales, "CODIGODESTINA")
                    CODIGODESTINA.text = factura.consignatario_fel.ref or "-" if factura.consignatario_fel else "-"
                    NOMBCOMPRADOR = etree.SubElement(DatosAdicionales, "NOMBCOMPRADOR")
                    NOMBCOMPRADOR.text = factura.comprador_fel.name if factura.comprador_fel else "-"
                    DIRCOMPRADOR = etree.SubElement(DatosAdicionales, "DIRCOMPRADOR")
                    DIRCOMPRADOR.text = factura.comprador_fel.street or "-" if factura.comprador_fel else "-"
                    CODCOMPRADOR = etree.SubElement(DatosAdicionales, "CODCOMPRADOR")
                    CODCOMPRADOR.text = factura.comprador_fel.ref or "-" if factura.comprador_fel else "-"
                    OTRAREF = etree.SubElement(DatosAdicionales, "OTRAREF")
                    OTRAREF.text = "-"
                    CODEXPORT = etree.SubElement(DatosAdicionales, "CODEXPORT")
                    CODEXPORT.text = factura.exportador_fel.ref or "-" if factura.exportador_fel else "-"
                    DIRDEST = etree.SubElement(DatosAdicionales, "DIRDEST")
                    DIRDEST.text = factura.consignatario_fel.street or "-" if factura.consignatario_fel else "-"

                subtotal = 0
                total = 0
                Detalles = etree.SubElement(DocElectronico, "Detalles")
                for linea in factura.invoice_line_ids:
                    if linea.price_unit != 0 and linea.quantity != 0:

                        precio_unitario = linea.price_unit * (100-linea.discount) / 100
                        precio_unitario_base = linea.price_subtotal / linea.quantity

                        total_linea = factura.currency_id.round(precio_unitario * linea.quantity)
                        total_linea_base = factura.currency_id.round(precio_unitario_base * linea.quantity)

                        total_linea_impuestos = factura.currency_id.round(total_linea - total_linea_base)
                        tasa = "12" if total_linea_impuestos > 0 else "0"

                        total_isr_linea = 0
                        if factura.journal_id.tipo_documento_fel == 5:
                            total_isr_linea = linea.price_subtotal / total_sin_impuestos * total_isr

                        Productos = etree.SubElement(Detalles, "Productos")

                        Producto = etree.SubElement(Productos, "Producto")
                        if factura.journal_id.tipo_documento_fel != 5:
                            Producto.text = 'P'+str(linea.product_id.id)
                        else:
                            Producto.text = "1"
                        Descripcion = etree.SubElement(Productos, "Descripcion")
                        Descripcion.text = linea.name
                        Medida = etree.SubElement(Productos, "Medida")
                        Medida.text = "1"
                        Cantidad = etree.SubElement(Productos, "Cantidad")
                        Cantidad.text = str(linea.quantity)
                        Precio = etree.SubElement(Productos, "Precio")
                        Precio.text = "%.6f" % precio_unitario
                        PorcDesc = etree.SubElement(Productos, "PorcDesc")
                        PorcDesc.text = "0"
                        ImpBruto = etree.SubElement(Productos, "ImpBruto")
                        ImpBruto.text = "%.2f" % total_linea
                        ImpDescuento = etree.SubElement(Productos, "ImpDescuento")
                        ImpDescuento.text = "0"
                        ImpExento = etree.SubElement(Productos, "ImpExento")
                        ImpExento.text = "%.2f" % total_linea_base if total_linea_impuestos == 0 else "0"
                        ImpOtros = etree.SubElement(Productos, "ImpOtros")
                        ImpOtros.text = "0"
                        ImpNeto = etree.SubElement(Productos, "ImpNeto")
                        ImpNeto.text = "%.2f" % total_linea_base if total_linea_impuestos > 0 else "0"
                        ImpIsr = etree.SubElement(Productos, "ImpIsr")
                        ImpIsr.text = str(total_isr_linea)
                        ImpIva = etree.SubElement(Productos, "ImpIva")
                        ImpIva.text = "%.2f" % total_linea_impuestos
                        ImpTotal = etree.SubElement(Productos, "ImpTotal")
                        ImpTotal.text = "%.2f" % total_linea
                        DatosAdicionalesProd = etree.SubElement(Productos, "DatosAdicionalesProd")
                        TipoVentaDet = etree.SubElement(Productos, "TipoVentaDet")
                        TipoVentaDet.text = "S" if linea.product_id.type == "service" else "B"

                        total += total_linea
                        subtotal += total_linea_base

                DocAsociados = etree.SubElement(Detalles, "DocAsociados")
                DASerie = etree.SubElement(DocAsociados, "DASerie")
                if factura.journal_id.tipo_documento_fel in [6, 9, 10]:
                    DASerie.text = factura.factura_original_id.serie_fel
                DAPreimpreso = etree.SubElement(DocAsociados, "DAPreimpreso")
                if factura.journal_id.tipo_documento_fel in [6, 9, 10]:
                    DAPreimpreso.text = factura.factura_original_id.numero_fel

                xmls = etree.tostring(DocElectronico, encoding="UTF-8")
                logging.warn(xmls)
                datos = base64.b64encode(b" "+xmls)
                factura.documento_xml_fel = datos
                factura.documento_xml_fel_name = "documento_xml_fel.xml"

                session = Session()
                session.verify = False
                session.auth = HTTPBasicAuth('usr_guatefac', 'usrguatefac')
                session.http_auth = HTTPBasicAuth('usr_guatefac', 'usrguatefac')
                session.headers.update({'Authorization': 'Basic dXNyX2d1YXRlZmFjOnVzcmd1YXRlZmFj'})
                transport = Transport(session=session)
                wsdl = 'https://dte.guatefacturas.com/webservices63/fel/Guatefac?WSDL'
                if factura.company_id.pruebas_fel:
                    wsdl = 'https://dte.guatefacturas.com/webservices63/feltest/Guatefac?WSDL'
                client = zeep.Client(wsdl=wsdl, transport=transport)

                resultado = client.service.generaDocumento(factura.company_id.usuario_fel, factura.company_id.clave_fel, factura.company_id.nit_fel, factura.journal_id.codigo_establecimiento, factura.journal_id.tipo_documento_fel, factura.journal_id.id_maquina_fel, "D", xmls)
                logging.warn(resultado)

                if resultado.find("dte:SAT ClaseDocumento") >= 0:
                    resultado = resultado.replace("&", "&amp;")
                    resultado = resultado.replace("<Resultado>", "")
                    resultado = resultado.replace("</Resultado>", "")
                    datos = base64.b64encode(b" "+(resultado.encode("utf-8")))
                    factura.resultado_xml_fel = datos
                    factura.resultado_xml_fel_name = "resultado_xml_fel.xml"

                    resultadoXML = etree.XML(resultado.encode("utf-8"))
                    numero_autorizacion = resultadoXML.xpath("//*[local-name() = 'NumeroAutorizacion']")[0]
                    nombre_receptor = resultadoXML.xpath("//*[local-name() = 'Receptor']")[0]
                    direccion_receptor = resultadoXML.xpath("//*[local-name() = 'DireccionReceptor']/*[local-name() = 'Direccion']")

                    factura.firma_fel = numero_autorizacion.text
                    factura.name = numero_autorizacion.get("Serie")+"-"+numero_autorizacion.get("Numero")
                    factura.serie_fel = numero_autorizacion.get("Serie")
                    factura.numero_fel = numero_autorizacion.get("Numero")
                    factura.nombre_cliente_fel = nombre_receptor.get("NombreReceptor")
                    factura.direccion_cliente_fel = direccion_receptor[0].text if len(direccion_receptor) > 0 else ''
                else:
                    factura.error_certificador(resultado)
                    return
                    
        return True

    def action_cancel(self):
        result = super(AccountMove, self).button_cancel()
        for factura in self:
            if factura.requiere_certificacion() and factura.firma_fel:
                session = Session()
                session.verify = False
                session.auth = HTTPBasicAuth('usr_guatefac', 'usrguatefac')
                session.http_auth = HTTPBasicAuth('usr_guatefac', 'usrguatefac')
                session.headers.update({'Authorization': 'Basic dXNyX2d1YXRlZmFjOnVzcmd1YXRlZmFj'})
                transport = Transport(session=session)
                wsdl = 'https://dte.guatefacturas.com/webservices63/fel/Guatefac?WSDL'
                if factura.company_id.pruebas_fel:
                    wsdl = 'https://dte.guatefacturas.com/webservices63/feltest/Guatefac?WSDL'
                client = zeep.Client(wsdl=wsdl, transport=transport)

                resultado = client.service.anulaDocumento(factura.company_id.usuario_fel, factura.company_id.clave_fel, factura.company_id.nit_fel, factura.serie_fel, factura.numero_fel, factura.partner_id.vat, datetime.date.today().strftime("%Y%m%d"), factura.motivo_fel)
                resultado = resultado.replace("&", "&amp;")
                logging.warn(resultado)
                resultadoXML = etree.XML(resultado)

                if len(resultadoXML.xpath("//ESTADO")) != 0 and resultadoXML.xpath("//ESTADO")[0].text != "ANULADO":
                    if len(resultadoXML.xpath("//ERROR")) != 0 and resultadoXML.xpath("//ERROR")[0].text != "DOCUMENTO ANULADO PREVIAMENTE":
                        raise UserError("Error en Guatefacturas: "+etree.tostring(resultadoXML))

class AccountJournal(models.Model):
    _inherit = "account.journal"

    tipo_documento_fel = fields.Integer('Tipo de Documento FEL', copy=False)
    id_maquina_fel = fields.Integer('ID Maquina FEL', copy=False)

class ResCompany(models.Model):
    _inherit = "res.company"

    usuario_fel = fields.Char('Usuario FEL', copy=False)
    clave_fel = fields.Char('Clave FEL', copy=False)
    nit_fel = fields.Char('NIT FEL', copy=False)
    pruebas_fel = fields.Boolean('Modo de Pruebas FEL')