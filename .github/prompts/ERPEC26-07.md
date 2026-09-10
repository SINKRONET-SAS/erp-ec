# ERPEC26-07 — Cobertura Ecuador ampliada

## Entrada y alcance
Leer RULES.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 06. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Cerrar EC04–EC08: retenciones, notas, liquidaciones, reembolsos, guías, ATS y reportes. Priorizar motores propios existentes; implementar APIs faltantes y decidir alcance POS/ecommerce.

## Criterios de aceptación
Casos propios por documento, compras/ventas/anulados/reembolsos ATS, conciliación contable-fiscal, pruebas contra especificaciones vigentes. Funciones no homologadas bloqueadas con siguiente acción.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-07.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-07 y task: ERPEC26-07.N; no publicar secretos ni trabajo ajeno.
