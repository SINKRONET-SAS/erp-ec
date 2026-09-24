# Aceptación operativa y salida controlada — DI25-07

Fecha: 24-09-2026. Fase: DI25-07 (dependencia DI25-06). Evidencia consolidada en `docs/evidencias/DI25/DI25-07-cierre.json`. Este documento no sustituye la aceptación de negocio del titular ni convierte pruebas locales en cumplimiento legal.

## Qué se libera y qué queda excluido (DI25-07.6)

**Liberado con evidencia** (sin P1 abiertos en estas funciones): ciclos operativos de ventas, compras, producción, importación, nómina (cálculo, asiento, pago, reversión), visitas y plan SaaS -> cobro -> aprovisionamiento; facturación electrónica nativa y su preparación en ambiente de pruebas (firma, cola, RIDE, estados, una autoridad por comprobante); agregador ATS y matriz fiscal como ensayo local; registros de protección de datos (RAT, derechos con conservación fiscal de 7 años, brechas, encargados, evaluación del DPD); inicio por empresa, roles y accesibilidad medida; respaldo y restauración aislada.

**Excluido, deshabilitado o bloqueado de forma explícita (no se marca como cumplido):**

| Función | Estado | Por qué | Siguiente acción |
|---|---|---|---|
| SRI en producción | Excluida; no autorizada por el titular | Genera documentos tributarios reales; requiere el certificado de la empresa emisora (no el de un colaborador de pruebas, que se eliminó a propósito en OP22) y presencia del responsable; el mecanismo para habilitarla ya existe y está probado (erpec.fiscal.point, 90/90 pruebas, endpoint de producción disponible en sri_client.py) pero deliberadamente deshabilitado en el código hasta que un responsable contable lo confirme de forma expresa y auditada, punto de emisión por punto de emisión. No depende de ningún archivo .env externo a este ERP: el certificado de esta empresa se carga y cifra dentro del propio ERP (erpec.fiscal.certificate, erpec_secrets) | El titular aporta certificado y autoriza una emisión supervisada |
| Presentación oficial del ATS/RDEP ante el SRI | Excluida (el talón local del DIMM ya se generó: docs/evidencias/DI25/DI25-07/talon-dimm-ats-ensayo.json) | No es un bloqueo del sistema: el talón y el acuse se generan con la interfaz del DIMM (C:\SRI-DIMM\Dimm\dimm.exe, con su propio JRE de 32 bits incluido, que corre en este Windows); lo único no automatizable es invocarla desde un proceso de 64 bits sin la GUI, y no se opera la GUI ni se presenta al SRI desde aquí. Además ventas ATS sin emisión autorizada en este ambiente: la autorización real de celcer (PRUEBAS) ya se obtuvo el 17-09-2026 (docs/evidencias/ERPEC26-OP09-PRIMERA-AUTORIZACION-REAL-20260917.json), pero el certificado prestado se eliminó a propósito el 20-09-2026 (OP22) y no hay otro cargado | El responsable abre el DIMM, carga el XML y genera el talón (presentar ante el SRI es una declaración real); cargar un certificado propio para emitir ventas de prueba en celcer |
| RDEP: casos D5 y C10 y otros ingresos no gravados | Bloqueados por el motor | El catálogo RDEP 2026 ya está en el DIMM (coincide con los parámetros); el validador oficial del plugin acepta el XML a nivel de esquema (docs/evidencias/DI25/DI25-07/validacion-rdep-dimm.json) y el formato del Formulario 107 fue entregado; queda la crítica semántica del DIMM y contrastar los campos 301-407 | Publicación del SRI; datos del responsable tributario |
| Exportación y homologación bancaria | **Parcial**: nómina implementada para Pichincha, Produbanco y Rumiñahui (ficha oficial verificada, mismo banco del beneficiario); proveedores y los otros 4 bancos siguen excluidos | Pichincha/Produbanco/Rumiñahui: falta la aceptación real en el validador del banco con una carga del canal contratado. Guayaquil: ficha identificada pero sin delimitador confirmado. Pacífico/Internacional/Bolivariano: sin ficha técnica pública de columnas. Proveedores: alcance no implementado todavía | El titular confirma el delimitador de Guayaquil con el banco, aporta ficha de Pacífico/Internacional/Bolivariano y autoriza una carga real de prueba en el canal contratado |
| Envío masivo de correo comercial | No existe el mecanismo | La preferencia de exclusión se respeta cuando exista | Diseñar campañas consultando la exclusión |
| Publicación pública del sitio | Condicionada | Faltan destinos legales reales (política de privacidad/términos) y datos de contacto reales de la empresa; el teléfono de la cabecera es el de ensayo | El responsable aporta los textos y datos |

## Ciclos operativos (DI25-07.1 y DI25-07.2)

Cada paso apunta a la prueba que lo ejercita; `addons/erpec_acceptance/tests/test_matrix.py` comprueba que ninguna referencia se pudra y la suite integrada acredita que pasan. El ciclo de compras con retención entre factura y pago no existía como una sola prueba y se agregó (`test_purchase_cycle_with_withholding_between_bill_and_payment`).

| Ciclo | Paso | Prueba (módulo · archivo · método) |
|---|---|---|
| ventas: entrega parcial -> factura -> nota de crédito -> cobro | entrega parcial, facturas, cobros parciales, devolución y nota de crédito | `erpec_treasury` · test_sales_flow.py · `test_delivery_invoices_partial_collections_return_and_credit` |
| ventas: entrega parcial -> factura -> nota de crédito -> cobro | mercadería sin entregar no se factura como entregada | `erpec_treasury` · test_sales_flow.py · `test_undelivered_stock_cannot_be_invoiced_as_delivered` |
| ventas: entrega parcial -> factura -> nota de crédito -> cobro | pedido cancelado conserva la factura publicada | `erpec_treasury` · test_sales_flow.py · `test_cancelled_order_preserves_published_invoice` |
| compras: recepción parcial -> factura -> retención -> pago -> devolución | recepción parcial, facturas, pagos parciales, devolución y nota de crédito | `erpec_workspace` · test_purchase_flow.py · `test_partial_receipt_payment_and_supplier_return` |
| compras: recepción parcial -> factura -> retención -> pago -> devolución | ciclo completo con retención entre factura y pago (cruza módulos) | `erpec_acceptance` · test_cycles.py · `test_purchase_cycle_with_withholding_between_bill_and_payment` |
| compras: recepción parcial -> factura -> retención -> pago -> devolución | retención emitida: contabilizar, repetir sin duplicar, revertir | `erpec_withholding_accounting` · test_accounting.py · `test_issued_post_idempotent_reverse` |
| producción: faltantes -> parcial -> desperdicio -> valoración | parcial, terminado, desperdicio, desarmado y costo | `erpec_manufacturing` · test_manufacturing.py · `test_partial_complete_scrap_unbuild_and_cost` |
| producción: faltantes -> parcial -> desperdicio -> valoración | faltante revierte y se puede recuperar | `erpec_manufacturing` · test_manufacturing.py · `test_shortage_rolls_back_and_can_recover` |
| producción: faltantes -> parcial -> desperdicio -> valoración | compra -> fabricación -> venta con contabilidad | `erpec_manufacturing` · test_manufacturing.py · `test_purchase_manufacture_sale_with_accounting` |
| importación: multiproducto, divisa y costos | costo parcial, contabilización e inverso | `erpec_imports` · test_imports.py · `test_partial_cost_accounting_and_inverse` |
| importación: multiproducto, divisa y costos | divisa extranjera y mercadería ya vendida | `erpec_imports` · test_imports.py · `test_currency_and_sold_goods` |
| importación: multiproducto, divisa y costos | pagos parciales a proveedor y diferencia cambiaria | `erpec_imports` · test_imports.py · `test_partial_supplier_payments_and_exchange_difference` |
| nómina: novedades -> beneficios -> anticipo -> asiento -> pago -> reversión | beneficio bloqueado una vez calculado | `erpec_payroll` · test_benefits_advances.py · `test_benefit_line_locked_once_calculated` |
| nómina: novedades -> beneficios -> anticipo -> asiento -> pago -> reversión | anticipo aprobado inmutable | `erpec_payroll` · test_benefits_advances.py · `test_approved_advance_is_immutable_and_protected` |
| nómina: novedades -> beneficios -> anticipo -> asiento -> pago -> reversión | recalcular no descuenta dos veces | `erpec_payroll` · test_benefits_advances.py · `test_recalculating_same_period_does_not_double_deduct` |
| nómina: novedades -> beneficios -> anticipo -> asiento -> pago -> reversión | cerrar, contabilizar, repetir, revertir y corregir | `erpec_payroll` · test_payroll.py · `test_close_post_repeat_reverse_correct` |
| nómina: novedades -> beneficios -> anticipo -> asiento -> pago -> reversión | pagos parciales de dos empleados y extracto | `erpec_treasury` · test_treasury.py · `test_two_employees_partial_payment_and_statement` |
| visitas: planificadas, omitidas y excepciones | visita completa dentro de la geocerca | `erpec_field_routes` · test_routes.py · `test_full_visit_within_geofence_no_exception` |
| visitas: planificadas, omitidas y excepciones | omitir exige motivo y crea excepción | `erpec_field_routes` · test_routes.py · `test_omit_requires_reason_and_creates_exception` |
| visitas: planificadas, omitidas y excepciones | flujo de aprobar y rechazar excepciones | `erpec_field_routes` · test_routes.py · `test_exception_approve_and_reject_flow` |
| plan SaaS -> cobro -> aprovisionamiento sin duplicar | cadena completa hasta el trabajo de aprovisionamiento | `erpec_selfservice` · test_selfservice.py · `test_full_chain_to_provision_job` |
| plan SaaS -> cobro -> aprovisionamiento sin duplicar | confirmación del servidor y aprovisionamiento duplicado | `erpec_payphone` · test_payphone.py · `test_server_confirmation_and_duplicate_provision` |
| plan SaaS -> cobro -> aprovisionamiento sin duplicar | reinicio duplicado y resultado obsoleto | `erpec_provision` · test_provision.py · `test_duplicate_restart_and_stale_result` |

Las cinco pruebas de Tesorería que se omitían en una base limpia por requerir la demo sembrada se ejecutaron completas (12 pruebas, 0 fallos, 0 errores, 0 omisiones) sobre una copia aislada de la demo con `scripts/test-seeded-copy.py` (evidencia: `docs/evidencias/DI25/DI25-07/tesoreria-sobre-copia-sembrada.json`).

## Roles, multiempresa, errores, vacíos, reintentos y concurrencia (DI25-07.3)

| Rol / aspecto | Prueba (módulo · archivo · método) |
|---|---|
| vendedor (límites de rol en ventas) | `erpec_treasury` · test_sales_flow.py · `test_service_invoice_and_role_boundaries` |
| comprador y bodega | `erpec_workspace` · test_purchase_flow.py · `test_partial_receipt_payment_and_supplier_return`<br>`erpec_imports` · test_imports.py · `test_company_and_stock_role_access` |
| operario y supervisor | `erpec_manufacturing` · test_manufacturing.py · `test_partial_operations_operator_and_supervisor` |
| nómina | `erpec_payroll` · test_annex_rdep.py · `test_access_requires_payroll_manager` |
| contador | `erpec_treasury` · test_treasury.py · `test_wrong_amount_partner_journal_and_role` |
| administrador | `erpec_base` · test_workspace.py · `test_only_system_administrators_can_access` |
| lector interno sin permisos | `erpec_workspace` · test_uiux.py · `test_reader_does_not_gain_sales_access` |
| multiempresa (aislamiento y cambio de empresa) | `erpec_workspace` · test_workspace.py · `test_company_switch`<br>`erpec_field_routes` · test_routes.py · `test_company_and_rep_isolation`<br>`erpec_fiscal_sri` · test_emission.py · `test_permissions_and_isolation` |
| errores y reintentos | `erpec_fiscal_sri` · test_emission.py · `test_connection_error_retries_then_blocks`<br>`erpec_treasury` · test_treasury.py · `test_outbound_inbound_repeat_and_undo` |
| doble acción concurrente | `erpec_fiscal_sri` · test_di25_concurrency.py · `test_both_orders_with_real_independent_transactions`<br>`erpec_field_routes` · test_routes.py · `test_double_checkin_blocked` |

En navegador real (Chrome, Playwright) se recorrió el Inicio con nueve roles (administrador, básico, vendedor, comprador, bodega, operario, supervisor, nómina y contador) en 360, 768, 1280 y 640 px a densidad 2 (equivalente a zoom 200 %): sin desbordamiento, sin errores de JavaScript, foco visible en cada parada de Tab y axe-core (WCAG 2.x A/AA) sin violaciones; cada rol ve solo sus áreas. El cambio de empresa en la interfaz cambia el estado fiscal mostrado (`docs/evidencias/DI25/DI25-06/recorrido-roles-9.json`). El error de acceso se muestra en español al usuario configurado en es_EC.

## Respaldo y restauración aislada (DI25-07.4)

`scripts/backup-restore-drill.py` respalda la base y el filestore, guarda la clave maestra en un directorio **aparte**, restaura en una base, rol y directorio propios (prefijo reservado), arranca Odoo real sobre la copia sin cron ni correo y verifica integridad. Resultado sobre la demo (24-09-2026): respaldo en **6,3 s** (volcado de 9,8 MB y filestore de 1.214 archivos, 101,7 MB); la clave no aparece en el volcado ni en el filestore; restauración en **27,2 s** y Odoo sirviendo el login a los **9,0 s**: **RTO medido 36,2 s**. Conteo de filas idéntico en las 10 tablas de control (0 de diferencia), el certificado cifrado se descifra con la clave restaurada y una clave incorrecta se rechaza, y ningún adjunto tiene su archivo faltante. **RPO**: la ventana propia del respaldo es de 6,3 s; hoy los respaldos son manuales y no hay programación, así que el RPO efectivo es el intervalo entre respaldos (el respaldo previo de ese día tenía 1 h 48 min: 6.472 s). Un RPO acotado exige programar el respaldo (por ejemplo, este mismo script en el Programador de tareas); no se instaló ninguna tarea. Evidencia: `docs/evidencias/DI25/DI25-07/simulacro-respaldo-restauracion-demo.json`.

Imagen final sin montajes y CI remoto del commit final: el CI ejecuta la suite integrada sobre la imagen sin fuentes montadas y el arranque real de las imágenes controller y customer; el resultado del commit final se registra en el cierre.

## Externos (DI25-07.5): acuse o bloqueo explícito

| Externo | Resultado |
|---|---|
| SMTP con destinatario autorizado | **Acuse real.** Un solo correo ficticio a la dirección que el titular autorizó, enviado por SMTP (smtp.gmail.com:587, STARTTLS) con las credenciales del .env sin copiarlas ni mostrarlas: EHLO 250, STARTTLS 220, autenticación 235, mensaje aceptado sin destinatarios rechazados en 5,9 s; el titular confirmó su recepción en la bandeja (asunto y referencia 6792defa69 coinciden). Prueba directa por SMTP: el ERP mantiene el servidor de correo de Odoo desactivado por diseño |
| SRI producción supervisada | **Bloqueo explícito**: no autorizada; sin certificado real utilizable |
| Homologación bancaria | **Parcial**: nómina con Pichincha, Produbanco y Rumiñahui implementada y probada (`addons/erpec_treasury/bank_export.py`, `docs/evidencias/DI25/bancario/`); falta la aceptación real de cada banco, proveedores y los otros 4 bancos |

## Reversión

Vuelta al despliegue anterior con los respaldos comprobados (demo: `.cache/windows/backups/di25-07-sync-demo-*`; fundador: `fundador-sync-di25-07-*`); un documento autorizado por el SRI o un pago real no se deshacen con una restauración técnica.
