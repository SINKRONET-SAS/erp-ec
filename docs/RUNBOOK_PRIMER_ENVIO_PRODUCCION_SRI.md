# Runbook: primer envío real a producción del SRI (supervisado)

**No se ha ejecutado ningún envío a producción en este proyecto.** Este documento es el procedimiento que debe seguir el responsable del cliente; el sistema lo permite técnicamente (endpoint `cel.sri.gob.ec` disponible y con WSDL alcanzable) pero un documento enviado a producción es **fiscalmente real e irreversible** (solo se corrige con nota de crédito, anulación ante el SRI o retención según el caso).

## Requisitos previos (todos)
1. RUC, establecimiento y punto de emisión reales, y régimen/obligación contable verificados en la empresa; agente de retención configurado si aplica.
2. Certificado de firma **de producción** (entidad reconocida) cargado, verificado y con "Firma de prueba" exitosa en Fiscal > Certificado de firma.
3. Establecimiento y punto de emisión registrados en Fiscal > Establecimientos y puntos de emisión, con dirección real.
4. Migración de diarios a puntos aplicada (ver `PLAN_MIGRACION_DIARIOS_PUNTOS_EMISION.md`) y último secuencial usado en producción conocido (para no repetir numeración).
5. Los mismos tipos de comprobante ya autorizados en PRUEBAS con los datos reales de la empresa (mismo certificado, mismo RUC).

## Procedimiento
1. Un usuario con rol de **responsable contable** abre el punto de emisión y pulsa **Habilitar producción**; lee y confirma la advertencia. Queda registrado quién y cuándo. Se crea/activa el diario de producción del punto (consecutivo independiente del de pruebas).
2. Emitir **un solo comprobante** de bajo monto y bajo riesgo (idealmente una factura real a un cliente de confianza, con su consentimiento) usando el diario de producción.
3. Firmar y transmitir; procesar la cola hasta ver **Autorizada**. Verificar en el portal del SRI (consulta de comprobantes) el número de autorización y la clave de acceso (posición 24 = 2).
4. Verificar el RIDE (datos del emisor, punto, autorización, ambiente PRODUCCIÓN).
5. Solo entonces habilitar el resto de tipos de comprobante y usuarios.

## Si algo falla
- **Devuelta/No autorizada**: leer el mensaje del SRI en la emisión; corregir el dato y emitir un comprobante nuevo (el secuencial usado no se reutiliza).
- **Volver a pruebas**: botón "Volver a pruebas" en el punto; se usa el diario de pruebas y su propio consecutivo. No revierte lo ya autorizado en producción.
- **Autorizada por error**: emitir nota de crédito en producción según normativa; no editar ni borrar.

## Lo que este documento NO garantiza
- Que todas las reglas de negocio del SRI en producción coincidan con las de pruebas para cada tipo de comprobante.
- La homologación de proveedores o la certificación de la solución; consultar con el SRI y con el asesor tributario del cliente.
