# ERPEC26-06 — Nómina y contabilidad

## Entrada y alcance
Leer RULES.md, .github/CODEX/_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 05. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Conectar SKNOMINA con Odoo; validar capacidades, mapear empleados/cuentas/centros y publicar resultados de nómina mediante contrato específico sin replicar datos innecesarios.

## Criterios de aceptación
Asiento balanceado trazable a cierre, sin duplicados; reapertura/reversión controlada, rechazo de período no cerrado y credencial ajena; revisión UI.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-06.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-06 y task: ERPEC26-06.N; no publicar secretos ni trabajo ajeno.
