"""Orientación comercial a partir de pedidos, entregas y facturas nativas."""
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    erpec_sale_guide = fields.Text('Siguiente paso', compute='_compute_erpec_sale_guide')

    @api.depends('state', 'delivery_status', 'invoice_status', 'picking_ids.state',
                 'picking_ids.location_id.usage', 'order_line.qty_to_invoice')
    def _compute_erpec_sale_guide(self):
        for order in self:
            if order.state in ('draft', 'sent'):
                message = 'Revisa cliente, productos, impuestos y condiciones. Confirma el pedido antes de entregar o preparar la factura.'
            elif order.state == 'cancel':
                message = 'Pedido cancelado. Revisa por separado entregas, facturas y cobros anteriores: cancelar el pedido no los revierte.'
            else:
                messages = []
                if order.delivery_status == 'pending':
                    messages.append('Abre Entregas y registra únicamente lo despachado. Revisa disponibilidad antes de validar.')
                elif order.delivery_status in ('partial', 'started'):
                    messages.append('Entrega parcial o en curso: revisa el traslado pendiente y las cantidades antes de dar por finalizado el pedido.')
                elif order.delivery_status == 'full':
                    messages.append('Traslados finalizados. Comprueba las cantidades entregadas y cualquier devolución.')
                else:
                    messages.append('Sin traslados activos. En servicios, revisa la política de facturación y las cantidades entregadas.')
                if any(p.state == 'done' and p.location_id.usage == 'customer' for p in order.picking_ids):
                    messages.append('Hay una devolución del cliente: revisa si corresponde abono; recibir mercancía no devuelve dinero ni revierte la factura.')
                if any(line.qty_to_invoice < 0 for line in order.order_line if not line.display_type):
                    messages.append('Hay cantidades negativas por facturar. Revisa el abono y su aplicación al saldo; no dupliques una nota de crédito existente.')
                elif order.invoice_status == 'to invoice':
                    messages.append('Hay cantidades facturables según la política del producto. Prepara y revisa el documento antes de publicarlo.')
                elif order.invoice_status == 'invoiced':
                    messages.append('Cantidades facturadas. Abre Facturas y abonos para revisar publicación, saldo y cobros; facturado no significa cobrado.')
                else:
                    messages.append('Sin cantidades facturables ahora. Un anticipo se prepara expresamente; no sustituye la factura final.')
                messages.append('Un cobro registrado requiere conciliación del extracto en Tesorería. La publicación contable no acredita autorización SRI.')
                message = ' '.join(messages)
            order.erpec_sale_guide = message
