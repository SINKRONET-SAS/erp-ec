# ERPEC26-02 — Base Community y aislamiento

## Entrada y alcance
Leer RULES.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 01. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Preparar infraestructura local reproducible, módulo base propio y configuración Ecuador Community; aislar base, filestore, secretos, red y compañía.

## Criterios de aceptación
Arranque limpio, versión verificable, acceso UI, aislamiento entre dos organizaciones y restauración base+archivos. Sin fuentes Enterprise.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-02.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-02 y task: ERPEC26-02.N; no publicar secretos ni trabajo ajeno.
