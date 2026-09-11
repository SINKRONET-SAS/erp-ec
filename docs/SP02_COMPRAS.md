# SP02 — Compras, recepción y facturación

Primer recorrido de aceptación transversal, 11/09/2026. No cierra SP02 ni acredita cumplimiento fiscal.

## Cambios de producto

La orden presenta «Seguimiento de la compra», derivado de sus estados nativos. Distingue solicitud, cancelación, recepción parcial, traslados finalizados, servicios, cantidades por facturar y devoluciones. Los accesos a recepciones y documentos del proveedor quedan dentro de la ficha, visibles también cuando las acciones de cabecera se agrupan.

Facturado no significa pagado; una devolución física no revierte la factura. La preparación reutiliza la acción nativa de factura/nota de crédito. Se oculta el botón alternativo de cabecera que ofrecía crear factura sin cantidades facturables. No se alteran métodos públicos, cálculo, contabilidad ni permisos nativos.

## Pruebas automatizadas en copia aislada

Siete pruebas del módulo: las cinco del centro más dos de compras.
- Comprador confirma dos productos de cinco unidades a 10 por unidad.
- Bodega recibe dos de cada uno; queda un traslado pendiente. Contabilidad genera factura de 40.
- Bodega recibe los tres restantes de cada producto; contabilidad genera factura de 60.
- Pagos registrados de 15 y 25 liquidan la cuenta por pagar de la primera factura. La segunda conserva saldo 60.
- Repetir crear factura sin cantidades pendientes produce error y conserva dos facturas.
- Bodega devuelve una unidad de cada producto. La cantidad neta recibida baja a cuatro por producto; la factura pagada conserva saldo cero.
- Contabilidad prepara y registra la nota de crédito de 20, que queda abierta. No se inventa un reembolso bancario ni se concilia automáticamente contra otro documento.
- Caso de servicio sin traslados; cuentas de gasto explícitas y asientos balanceados.
- El perfil de bodega no puede leer saldos de facturas.

Los importes sin impuestos son datos de regresión, no parámetros tributarios de la demo. Se verifica conciliación de la cuenta por pagar; falta el recorrido de extracto y conciliación bancaria. No se valida aquí valoración automática del inventario ni normativa fiscal.

## Hallazgo en datos históricos

La compra P00001 conduce al documento inicial Tiq 001-001-000000002:
- El servicio aparece imputado a 110307 Mercaderías en tránsito.
- El tipo documental es un tiquete.
- La semilla inicial aplicó una retención ficticia de 2 %, explícita en scripts/seed-demo.py.

No se adopta este documento como modelo de una compra correcta. Se muestra un aviso en los dos documentos de esa semilla vinculados por sus identificadores técnicos, sin cambiar asientos publicados ni extender el aviso a documentos ajenos.

Pendiente prioritario SP02-D01: sanear la semilla histórica, corregir su trazabilidad contable mediante el flujo de reversión correspondiente y sustituir los escenarios inválidos. No alterar silenciosamente asientos conciliados ni inventar tarifas legales para completar una demostración.

## Revisión de interfaz

Se revisan compra de servicios P00001 y compra parcial P00002, el acceso a la factura ya existente y el acceso a los dos traslados. Los resultados concretos y las capturas quedan en ERPEC26-SP02-COMPRAS.json.

La revisión de navegador no equivale a ejecutar desde la UI todos los pasos del ensayo automatizado. Quedan pendientes la aceptación por usuarios de cada rol, las pantallas de pago/conciliación y la corrección de datos históricos. Los ciclos de ventas, producción, importaciones ampliadas y nómina mantienen sus pendientes del plan.

## Repetición y reversión

Verificar con scripts/verify-workspace.py; instalar con scripts/install-fiscal-native-demo.py --workspace bajo el propietario de las sesiones, después de aprobar las siete pruebas y sus hashes. El instalador guarda respaldo de base, filestore y módulos. No desinstalar solamente el módulo para revertir los menús; recuperar el respaldo completo, primero en copia aislada, conforme a SEGUNDA_PASADA_PRODUCTO.md.
