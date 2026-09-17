# ERPEC26-OP09 — Facturación electrónica nativa: firma real + transmisión SOAP al SRI

Leer AGENTS.md, RULES.md, el contexto histórico, docs/PLAN_HAIKY_FACTURACION_NATIVA.md, docs/FACTURACION_LOCAL.md y docs/DOCUMENTOS_FISCALES.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Construir la vía nativa completa de emisión de comprobantes electrónicos: firma XAdES real → transmisión SOAP real al SRI (ambiente PRUEBAS) → autorización → RIDE, como segunda autoridad de emisión independiente de `erpec_fiscal_connector` (que delega en un Facturador externo), gobernada por la misma regla "una autoridad por comprobante". Motivo: no duplicar el costo de correr dos servicios en Render.

No inventar campos, códigos o estructuras del SRI sin fuente primaria. Confirmar contra la Ficha Técnica oficial vigente (hoy versión 2.34, sri.gob.ec) antes de asumir cualquier detalle de protocolo no evidente en el código ya existente. No declarar una autorización real lograda sin un certificado genuino emitido por una entidad certificadora acreditada por el SRI — un rechazo real por certificado no confiable es una prueba válida del canal, no una autorización.

## Criterios de aceptación

Cada incremento de esta fase debe: (1) no perder la regla de una sola autoridad de emisión por comprobante; (2) mantener el ambiente de producción (`cel.sri.gob.ec`) deshabilitado en el código hasta una activación explícita separada; (3) probarse en base aislada nueva, con las llamadas SOAP simuladas en la batería automática (sin tocar la red real en cada corrida); (4) documentar cualquier ensayo real contra el SRI con su resultado exacto, sin fabricar una autorización que no ocurrió. Un incremento que no pueda cumplir (1)-(3) se limita a documentación, sin código.

## Verificación y cierre

Añadir pruebas significativas y evidencia en docs/evidencias/. Instalar solo con respaldo previo. Commits con phase: ERPEC26-OP09 y task: ERPEC26-OP09.N. No cerrar la fase por un incremento: el certificado real, la guarda recíproca en `erpec_fiscal_connector`, la activación de producción y la conformidad visual completa del RIDE permanecen pendientes hasta autorización y entrega explícitas.

## Primer incremento autorizado — 16-09-2026

El titular pidió la vía nativa completa, tomando como referencia sinkroniq-mobile (facturación) y nuevo_nomina (nómina/RDEP) — investigación que confirmó que nuestro RDEP ya está por delante de esa segunda referencia, así que no se portó nada de nómina. Se entrega: pruebas nuevas para `xades.py` (huérfano hasta ahora); nuevo addon `erpec_fiscal_sri` con `erpec.fiscal.certificate`, `erpec.fiscal.emission`, `sri_client.py` (SOAP real contra `celcer.sri.gob.ec`) y `ride.py` (RIDE con reportlab), sin modificar `erpec_fiscal_connector`/`erpec_fiscal_native` (en edición concurrente) más allá de la nueva prueba de `xades.py`. Verificado contra la Ficha Técnica 2.34 oficial (clave de acceso, estructura de mensajes). 32/32 pruebas; instalado en demo con respaldo. Ensayo real (no mockeado) contra el SRI: RECIBIDA en recepción, rechazada en autorización exactamente por certificado no confiable (código 39) — confirma el canal completo funcionando de punta a punta. Detalle completo en docs/PLAN_HAIKY_FACTURACION_NATIVA.md.

## Segundo incremento autorizado — 16/17-09-2026

Retomado tras confirmar el clúster de PostgreSQL local en marcha. Único pendiente de OP09 sin depender de la sesión concurrente ni de un certificado del titular: conformidad visual del RIDE contra la Ficha Técnica 2.34, cuyo ejemplo es una imagen incrustada. Un agente en segundo plano descargó el PDF oficial y renderizó esa imagen (página 60, Anexo 2) para inspeccionarla campo por campo. El titular pidió usar como referencia de consulta el renderizador RIDE real de sinkroniq-mobile (`classicRideStrategy.js`/`baseRideRenderer.js`, ya en producción). Se reescribió `addons/erpec_fiscal_sri/ride.py` con esa arquitectura de dos columnas con recuadros (reportlab, sin copiar código ni datos de sinkroniq-mobile, sin dependencias nuevas), agregando AMBIENTE, EMISIÓN, etiquetas oficiales, clave de acceso bajo el código de barras, y los campos de emisor/comprador/ítem que faltaban — cada nombre de campo XML confirmado contra el XSD oficial del proyecto antes de usarlo. 3 pruebas nuevas (24 en total en el addon, 0 fallos); reinstalado en demo con respaldo. Detalle completo en docs/PLAN_HAIKY_FACTURACION_NATIVA.md (sección "Segundo incremento").
