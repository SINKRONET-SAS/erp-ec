"""Orientación de compras derivada de documentos nativos, sin estados paralelos."""
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    erpec_purchase_guide = fields.Text('Siguiente paso', compute='_compute_erpec_purchase_guide')

    @api.depends('state', 'receipt_status', 'invoice_status', 'picking_ids.state',
                 'picking_ids.location_dest_id.usage')
    def _compute_erpec_purchase_guide(self):
        for order in self:
            if order.state in ('draft', 'sent', 'to approve'):
                message = 'Revisa proveedor, productos, cantidades y condiciones. Confirma o solicita aprobación antes de recibir o facturar.'
            elif order.state == 'cancel':
                message = 'Compra cancelada. Revisa por separado cualquier recepción o factura ya realizada.'
            else:
                messages = []
                if order.receipt_status == 'pending':
                    messages.append('Abre Recepciones y registra únicamente lo que llegó.')
                elif order.receipt_status == 'partial':
                    messages.append('Recepción parcial: revisa el traslado pendiente antes de dar por completo el abastecimiento.')
                elif order.receipt_status == 'full':
                    messages.append('Traslados finalizados. Revisa las cantidades y cualquier devolución.')
                else:
                    messages.append('Sin traslados activos. En servicios, verifica la cantidad recibida o la política de facturación.')
                if any(p.state == 'done' and p.location_dest_id.usage == 'supplier' for p in order.picking_ids):
                    messages.append('Hay devoluciones al proveedor: revisa si corresponde una nota de crédito; devolver mercancía no revierte la factura.')
                if order.invoice_status == 'to invoice':
                    messages.append('Hay cantidades por facturar o abonar. Revisa si corresponde factura o nota de crédito y contrástala con el documento del proveedor.')
                elif order.invoice_status == 'invoiced':
                    messages.append('Facturas generadas. Abre Facturas del proveedor para revisar su validación, saldo y pagos; facturado no significa pagado.')
                else:
                    messages.append('Sin cantidades facturables ahora. Revisa recepción y política de facturación antes de crear una factura.')
                message = ' '.join(messages)
            order.erpec_purchase_guide = message
