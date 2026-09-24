"""Matriz de aceptación DI25-07: cada paso de cada ciclo y cada rol apunta a la prueba automatizada que lo
ejercita (módulo, archivo, método). test_matrix.py comprueba que cada referencia existe, de modo que la matriz no
se pudre en silencio; que las pruebas pasen lo acredita la suite integrada, no este archivo."""

# (paso, módulo, archivo de prueba, método)
CYCLES = {
    'ventas: entrega parcial -> factura -> nota de crédito -> cobro': [
        ('entrega parcial, facturas, cobros parciales, devolución y nota de crédito', 'erpec_treasury', 'test_sales_flow.py',
         'test_delivery_invoices_partial_collections_return_and_credit'),
        ('mercadería sin entregar no se factura como entregada', 'erpec_treasury', 'test_sales_flow.py',
         'test_undelivered_stock_cannot_be_invoiced_as_delivered'),
        ('pedido cancelado conserva la factura publicada', 'erpec_treasury', 'test_sales_flow.py',
         'test_cancelled_order_preserves_published_invoice'),
    ],
    'compras: recepción parcial -> factura -> retención -> pago -> devolución': [
        ('recepción parcial, facturas, pagos parciales, devolución y nota de crédito', 'erpec_workspace', 'test_purchase_flow.py',
         'test_partial_receipt_payment_and_supplier_return'),
        ('ciclo completo con retención entre factura y pago (cruza módulos)', 'erpec_acceptance', 'test_cycles.py',
         'test_purchase_cycle_with_withholding_between_bill_and_payment'),
        ('retención emitida: contabilizar, repetir sin duplicar, revertir', 'erpec_withholding_accounting', 'test_accounting.py',
         'test_issued_post_idempotent_reverse'),
    ],
    'producción: faltantes -> parcial -> desperdicio -> valoración': [
        ('parcial, terminado, desperdicio, desarmado y costo', 'erpec_manufacturing', 'test_manufacturing.py',
         'test_partial_complete_scrap_unbuild_and_cost'),
        ('faltante revierte y se puede recuperar', 'erpec_manufacturing', 'test_manufacturing.py',
         'test_shortage_rolls_back_and_can_recover'),
        ('compra -> fabricación -> venta con contabilidad', 'erpec_manufacturing', 'test_manufacturing.py',
         'test_purchase_manufacture_sale_with_accounting'),
    ],
    'importación: multiproducto, divisa y costos': [
        ('costo parcial, contabilización e inverso', 'erpec_imports', 'test_imports.py', 'test_partial_cost_accounting_and_inverse'),
        ('divisa extranjera y mercadería ya vendida', 'erpec_imports', 'test_imports.py', 'test_currency_and_sold_goods'),
        ('pagos parciales a proveedor y diferencia cambiaria', 'erpec_imports', 'test_imports.py',
         'test_partial_supplier_payments_and_exchange_difference'),
    ],
    'nómina: novedades -> beneficios -> anticipo -> asiento -> pago -> reversión': [
        ('beneficio bloqueado una vez calculado', 'erpec_payroll', 'test_benefits_advances.py', 'test_benefit_line_locked_once_calculated'),
        ('anticipo aprobado inmutable', 'erpec_payroll', 'test_benefits_advances.py', 'test_approved_advance_is_immutable_and_protected'),
        ('recalcular no descuenta dos veces', 'erpec_payroll', 'test_benefits_advances.py', 'test_recalculating_same_period_does_not_double_deduct'),
        ('cerrar, contabilizar, repetir, revertir y corregir', 'erpec_payroll', 'test_payroll.py', 'test_close_post_repeat_reverse_correct'),
        ('pagos parciales de dos empleados y extracto', 'erpec_treasury', 'test_treasury.py', 'test_two_employees_partial_payment_and_statement'),
    ],
    'visitas: planificadas, omitidas y excepciones': [
        ('visita completa dentro de la geocerca', 'erpec_field_routes', 'test_routes.py', 'test_full_visit_within_geofence_no_exception'),
        ('omitir exige motivo y crea excepción', 'erpec_field_routes', 'test_routes.py', 'test_omit_requires_reason_and_creates_exception'),
        ('flujo de aprobar y rechazar excepciones', 'erpec_field_routes', 'test_routes.py', 'test_exception_approve_and_reject_flow'),
    ],
    'plan SaaS -> cobro -> aprovisionamiento sin duplicar': [
        ('cadena completa hasta el trabajo de aprovisionamiento', 'erpec_selfservice', 'test_selfservice.py', 'test_full_chain_to_provision_job'),
        ('confirmación del servidor y aprovisionamiento duplicado', 'erpec_payphone', 'test_payphone.py',
         'test_server_confirmation_and_duplicate_provision'),
        ('reinicio duplicado y resultado obsoleto', 'erpec_provision', 'test_provision.py', 'test_duplicate_restart_and_stale_result'),
    ],
}

# rol / aspecto -> (módulo, archivo, método)
ROLES = {
    'vendedor (límites de rol en ventas)': [('erpec_treasury', 'test_sales_flow.py', 'test_service_invoice_and_role_boundaries')],
    'comprador y bodega': [('erpec_workspace', 'test_purchase_flow.py', 'test_partial_receipt_payment_and_supplier_return'),
                           ('erpec_imports', 'test_imports.py', 'test_company_and_stock_role_access')],
    'operario y supervisor': [('erpec_manufacturing', 'test_manufacturing.py', 'test_partial_operations_operator_and_supervisor')],
    'nómina': [('erpec_payroll', 'test_annex_rdep.py', 'test_access_requires_payroll_manager')],
    'contador': [('erpec_treasury', 'test_treasury.py', 'test_wrong_amount_partner_journal_and_role')],
    'administrador': [('erpec_base', 'test_workspace.py', 'test_only_system_administrators_can_access')],
    'lector interno sin permisos': [('erpec_workspace', 'test_uiux.py', 'test_reader_does_not_gain_sales_access')],
    'multiempresa (aislamiento y cambio de empresa)': [('erpec_workspace', 'test_workspace.py', 'test_company_switch'),
                                                        ('erpec_field_routes', 'test_routes.py', 'test_company_and_rep_isolation'),
                                                        ('erpec_fiscal_sri', 'test_emission.py', 'test_permissions_and_isolation')],
    'errores y reintentos': [('erpec_fiscal_sri', 'test_emission.py', 'test_connection_error_retries_then_blocks'),
                             ('erpec_treasury', 'test_treasury.py', 'test_outbound_inbound_repeat_and_undo')],
    'doble acción concurrente': [('erpec_fiscal_sri', 'test_di25_concurrency.py', 'test_both_orders_with_real_independent_transactions'),
                                 ('erpec_field_routes', 'test_routes.py', 'test_double_checkin_blocked')],
}
