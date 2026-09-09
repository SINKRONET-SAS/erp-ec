# ERPEC26-03 — Organizaciones, identidad y planes

## Entrada y alcance
Leer RULES.md, .github/CODEX/_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 02. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Definir autoridad de cobro, identidad, vinculación autorizada de clientes existentes y derechos de ERP/nómina/facturador. Implementar catálogo y suscripciones sin duplicar cobros.

## Criterios de aceptación
Pruebas de alta, vencimiento, cambio de versión, rechazo de organización ajena y límites; UI coherente y migración explícita de contratos existentes.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-03.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-03 y task: ERPEC26-03.N; no publicar secretos ni trabajo ajeno.
