# ERPEC26-08 — Piloto, operación y publicación

## Entrada y alcance
Leer RULES.md, .github/CODEX/_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 07. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Ejecutar recorridos completos, carga, aislamiento, seguridad, restauración, observabilidad, costos y soporte. Preparar despliegue y manual operativo con reversión por repositorio.

## Criterios de aceptación
Dos clientes aislados, backup restaurado, sin doble cargo/emisión/asiento, evidencias UI y pruebas automatizadas. Publicación productiva solo con autorización y requisitos externos cubiertos.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-08.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-08 y task: ERPEC26-08.N; no publicar secretos ni trabajo ajeno.
