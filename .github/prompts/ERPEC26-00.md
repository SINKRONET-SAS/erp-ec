# ERPEC26-00 — Gobierno y diagnóstico

## Entrada y alcance
Leer RULES.md, .github/CODEX/_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: Ninguna. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Crear reglas, inventario, arquitectura, fases y cadena de gobierno.

## Criterios de aceptación
Documentos, fuentes y hashes verificables; no presentar implementación como realizada.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-00.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-00 y task: ERPEC26-00.N; no publicar secretos ni trabajo ajeno.
