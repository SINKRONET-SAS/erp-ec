# ERPEC26-01 — Procedencia y alcance Ecuador

## Entrada y alcance
Leer RULES.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 00. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Obtener Community oficial con commit fijo; comparar manifiestos locales, completar licencias transitivas y matriz EC01–EC12. Auditar contratos reales de ambos productos y catalogar qué documentos externos admiten.

## Criterios de aceptación
Inventario reproducible, dependencias compatibles y decisión por capacidad; descartar OEEL/OPL no autorizadas. Registrar normativa vigente y vacíos sin inventar cumplimiento.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-01.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-01 y task: ERPEC26-01.N; no publicar secretos ni trabajo ajeno.
