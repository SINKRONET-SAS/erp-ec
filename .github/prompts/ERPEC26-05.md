# ERPEC26-05 — Facturación desde Odoo

## Entrada y alcance
Leer RULES.md, .github/CODEX/_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 04. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Crear conector propio Odoo–Facturador, contratos de factura y consulta, origen registrado, secretos por empresa y conciliación durable de resultados.

## Criterios de aceptación
Venta sintética en pruebas, entrega duplicada, timeout, reinicio, eventos fuera de orden, rechazo y autorización; XML/RIDE vinculados. Ensayo real SRI requiere ambiente y credenciales autorizados.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-05.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-05 y task: ERPEC26-05.N; no publicar secretos ni trabajo ajeno.
