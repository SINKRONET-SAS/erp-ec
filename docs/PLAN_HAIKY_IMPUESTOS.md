# Plan HAIKY — Plan de impuestos transversal
Autorizado por el titular el 13/09/2026. Complementa SP02; no cierra las fases históricas ni acredita cumplimiento tributario.

## Modelo funcional
El catálogo de impuestos es la autoridad de definiciones. Sus reparticiones de factura y devolución enlazan las cuentas de registro. Los impuestos predeterminados de una cuenta son otra relación. Los artículos aportan impuestos de venta/compra; proveedores y clientes aportan posiciones fiscales. Odoo resuelve y transforma los impuestos; el plan permite consultar ese cruce y abrir sus configuraciones.

No duplicar el motor, mantener tasas nativas y aislamiento por empresa. Los escenarios guardados son consultas de configuración vigente, no reglas paralelas ni evidencia histórica inmutable. Compras, ventas, facturas de proveedores e importaciones comparten la configuración nativa. Fabricación consume valoración: no añadir un impuesto independiente a la orden de fabricación. Nómina mantiene su autoridad laboral; retenciones específicas y sustento ATS requieren sus propios modelos.

| Fase | Dependencia | Entrega y criterio |
|---|---|---|
| TX00 | Gobierno vigente | Este plan y prompt; diagnóstico de relaciones nativas. Documental. |
| TX01 | TX00 | Plan visible por empresa/artículo/tercero/operación; origen, posición fiscal, impuestos resultantes, cuentas y advertencias; enlaces al catálogo y al plan de cuentas. Pruebas de transformación, vacíos y aislamiento. |
| TX02 | TX01 verificada | Instalación con respaldo, aceptación visual, evidencia, gobierno, commit/push. |

## Límites y validación
El escenario no reproduce excepciones introducidas manualmente en un pedido/factura ni la dirección de entrega de una venta. Mostrarlo en pantalla. No inferir exención de un campo vacío. Mostrar retirada explícita por posición fiscal y falta de cuenta como revisión, no como invalidez legal automática (Odoo permite usar cuenta de línea). Un impuesto agrupado debe mostrar sus impuestos componentes.

La clasificación/régimen real del emisor, tratamiento específico por producto/proveedor, retenciones, sustento ATS y vigencia legal no se asignan por deducción. Quedan sujetos a validación contable; las consultas no autorizan emisión SRI.

## Resultado de ejecución
TX00 documental, TX01 probado y TX02 instalado/verificado: completados para este incremento local. Evidencia: evidencias/ERPEC26-SP02-IMPORTACIONES-VALORACION.json. 32/32 pruebas y navegación contable revisada. Los límites tributarios y SP02 permanecen abiertos.
