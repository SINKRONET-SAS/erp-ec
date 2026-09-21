# DI25-02 — Integridad fiscal: diseño, compatibilidad y operación

Estado: implementación en validación; este documento no cierra la fase.

## Defectos reproducidos

En ec_integrated_test_d8ffefe6c8f2, la batería reportó 95 pruebas, 3 fallos y 0 errores (salida 1). Los tres casos DI25 demostraron hambre de cola con diez emisiones bloqueadas, aceptación del conector externo después de una emisión nativa y modificación del concepto firmado. Datos sintéticos; sin red SRI.

## Cambios y contratos

- La fila account_move es el punto común de serialización de emisión y cambios económicos. Una actualización sin cambio de valor en write_date genera una versión PostgreSQL; una instantánea REPEATABLE READ antigua debe reintentarse y revisar la autoridad ya confirmada. Un SELECT FOR UPDATE aislado no bastaba para este caso.
- Las dos creaciones internas también verifican la exclusión. Se conservan sus acciones y respuestas públicas; no se crea un estado de autoridad paralelo. Los vínculos existentes determinan la autoridad.
- La protección de factura y líneas incluye la emisión nativa. El destino de una línea y de un sustento también se verifica. Se permiten notas/operaciones de corrección mediante los flujos existentes; una cancelación contable no equivale a anulación fiscal.
- Vista previa y emisión comparten identificación y validación de líneas. La vista previa conserva ambiente de pruebas, clave reproducible y carácter no fiscal. Los formatos del conector remoto y los sustentos de importación/reembolso siguen separados porque tienen contratos y significados distintos.
- La cola nativa selecciona estados procesables, por antigüedad, con próxima fecha elegible. Cada trabajo tiene un punto de restauración transaccional; un error inesperado detiene ese trabajo con correlación, sin ocultarlo ni revertir los demás. Los errores de serialización se propagan para el reintento de Odoo.
- Se conserva un lote de diez, con presupuesto temporal entre trabajos y notificación de pendientes. Crear una emisión firmada registra un disparador transaccional de Odoo; el trabajador se despierta después del commit. La operación depende de que el cron esté activo y disponible.
- La recuperación de un documento bloqueado/devuelto consulta la misma clave. No cambia XML, no firma otra vez y no retransmite silenciosamente.
- La bandeja muestra autoridad, ambiente, correlación, edad, primer/último intento y error. La demora mide el inicio del intento, no la recepción efectiva del SRI ni una tolerancia legal.

## Pruebas y límites

La concurrencia se ensaya en un proceso Odoo independiente para evitar los bloqueos globales del arnés TransactionCase. Usa dos conexiones PostgreSQL REPEATABLE READ, ambos órdenes de autoridad y reintento tras conflicto; al finalizar verifica una sola autoridad y limpia únicamente sus registros sintéticos.

El primer arnés con hilos dentro de TransactionCase se bloqueó; se detuvo exclusivamente su proceso y el ejecutor limpió su base/rol. Esa ejecución no se acredita como prueba aprobada.

En ec_integrated_test_1b3d7bc90466: 161 pruebas, un fallo de compatibilidad del texto de bloqueo de reembolsos, cero errores. La exclusión concurrente y los ocho escenarios DI25 pasaron; se corrigió el texto y se inició suite completa. No sustituir este resultado por un cierre antes de terminar la regresión.

## Actualización y reversión

Los campos de seguimiento son aditivos. No se reescriben XML, claves, consecutivos, asientos ni estados históricos. Una emisión anterior sin primer intento registrado no tiene medición retrospectiva. Antes de actualizar una instancia con datos, conservar respaldo de base, filestore, código y configuración privada y ensayar la actualización en una copia con cron detenido.

Para revertir código en una copia aislada, usar el commit anterior 96e5a44; actualizar los módulos afectados con el cron detenido. Las columnas aditivas pueden permanecer sin uso: no borrar evidencia para volver a una versión anterior. Restituir vistas y código juntos. No reabrir la emisión productiva con una versión que carece de las protecciones corregidas; conservar el bloqueo operativo hasta verificar un reemplazo seguro. Restaurar una base nunca anula un comprobante emitido.

## Referencia legal

El [comunicado oficial del SRI](https://www.sri.gob.ec/detalle-noticias?idnoticia=1240&marquesina=1), consultado el 21-09-2026 UTC, exige transmisión inmediata desde el 01-01-2026. El disparador y las métricas son controles técnicos; no certifican cumplimiento jurídico ni autorizan una tolerancia de cola. Validar operación, contingencias y aceptación supervisada antes de producción.
