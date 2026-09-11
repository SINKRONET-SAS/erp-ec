# ERPEC26-05 — Conector Odoo–Facturador de pruebas

## Entrega local y autorización

El usuario solicitó continuar el plan y autorizó expresamente SINKRONET SAS (info@sinkronet.com.ec, RUC 1793235327001) como emisor del ensayo. No se copia el RUC a res.company en Odoo y no se vincula la demo comercial. El emisor permanece en la base local de Facturador: usuario 14, Empresa 167 y Workspace 167, todos obtenidos del alta autorizada y de una consulta posterior. Ambiente usuario y Empresa: 1. No se crean credenciales, puntos de emisión ni vínculos con valores inventados.

El incremento adelanta el trabajo funcional autorizado sin cerrar los gates históricos de infraestructura ni la fase fiscal. Se conserva AuditLock. Código propio Community; no se incorpora Enterprise.

## Flujo visible

En el piloto 8186 aparece **Facturación electrónica → Bandeja de pruebas / Configurar conexión**. En una factura de venta contabilizada está **Facturador — Pruebas → Preparar / abrir envío fiscal**. El panel operativo informa que el conector está instalado y qué falta para el ensayo.

La preparación guarda una solicitud persistente con UUID, contenido fiscal y vínculo a la factura. La confirmación de esta transacción ocurre antes de que otra acción o ejecución programada pueda enviarla. Repetir la preparación devuelve la misma solicitud. Se bloquean cambios relevantes y el retorno a borrador de la factura ya preparada. No se crea otra factura contable al consultar resultados.

Cada procesamiento verifica contrato 1.0, origen registrado CUSTOM, identidad Empresa/Workspace, clave sk_test_, ambiente PRUEBAS y ambiente 1 tanto de Empresa como de emisor; exige emit:factura y read:comprobantes. Primero consulta por referencia y solo envía si no existe solicitud o si el servicio la mantiene bloqueada para revalidación. Reutiliza el mismo contenido e Idempotency-Key. Los cortes y errores transitorios conservan la solicitud y fijan espera creciente; cinco intentos por ciclo, con revisión explícita para reabrir. Los bloqueos de filas serializan operaciones sobre el mismo documento y destino. Las pruebas fueron secuenciales, no de carga concurrente.

Una respuesta recibida/procesando no se muestra autorizada. La autorización requiere referencia e idempotencia coincidentes, estado invoice_authorized y rawStatus AUTORIZADA, ID remoto, número fiscal y clave de 49 dígitos con ambiente de pruebas. Un estado terminal no retrocede. No se acepta editar manualmente los estados ni consultar otra compañía mediante las acciones. La credencial solo es accesible al administrador; no se copia a solicitudes ni logs. Los enlaces XML/RIDE deben pertenecer al origen configurado.

El cron se instala inactivo y el piloto mantiene sus tareas programadas deshabilitadas. El procesamiento manual es una acción separada y trazable. El contrato vigente de Facturador todavía devuelve XML/RIDE nulos: la pantalla lo indica, sin inventar archivos.

## Alcance y ensayos obligatorios

Este contrato cubre factura de venta en USD, importes positivos, descuento por unidad y un IVA porcentual explícito por línea compatible con los grupos indicados del catálogo local. No convierte exento o no objeto en IVA 0. ICE, IRBPNR, monedas adicionales, pagos divididos, notas de crédito, retenciones electrónicas y reembolsos fiscales requieren sus contratos completos. Los porcentajes del catálogo no constituyen una recomendación tributaria.

La equivalencia final debe validar redondeo, fecha de emisión (actualmente el servicio determina su fecha), secuenciales, XML/RIDE, firma y autorización. El número contable Odoo se conserva y el número fiscal se muestra separado; no se introduce una segunda autoridad de secuenciales. Las pruebas técnicas no acreditan cumplimiento fiscal integral ni un envío SRI.

Verificación final: nueve pruebas Odoo aprobadas en una copia aislada; cubren duplicados, contenido conservado, timeout y consulta recuperada, estados pendientes/rechazados, autorización incompleta o de otro ambiente, orden de resultados, límites de reintento, transporte, permisos y aislamiento. Se vacía la caché para comprobar lectura persistente; no se afirma un ensayo de caída física de proceso. Las respuestas fiscales son simuladas. Facturador: 19 pruebas aprobadas, salida 0, contrato ampliado en commit 13d84039, rama codex/erpec26-fiscal-contract. Se preservaron los cambios ajenos en su checkout principal.

La instalación del piloto usa respaldo de base/filestore, exige hashes coincidentes con los tests y vuelve a arrancar únicamente 8186. Se comprobó HTTP 200, módulo instalado, cero conexiones y solicitudes reales, y la bandeja en el navegador. La demo 8369 no fue modificada.

## Firma y siguiente paso

La firma pertenece a **Facturador → Administración → Firma Electrónica**. Permite seleccionar .p12/.pfx, introducir la clave, validar antes de guardar y cargarla. No se almacena en Odoo. La cuenta creada es local; usar una app contra otro servidor no modifica esta base.

Consulta directa del emisor después de la autorización: usuario y Empresa en pruebas, sin certificado, sin dirección matriz, sin puntos de emisión activos y sin claves API activas. Se necesitan esos datos y la capacidad API autorizada antes del ensayo. No se evaden contratos o planes. No hubo envío SRI ni cambios de ambiente.

Para detener el flujo, desactivar el cron y no procesar nuevos trabajos. No borrar solicitudes ni cambiar su destino para reintentarlas en otra empresa. Una restauración debe coordinarse con Facturador: conservar/reconciliar referencias previas antes de reenviar. El respaldo no borra ni anula comprobantes externos. Mantener la versión instalada para consulta si ya hubiera solicitudes fiscales.
