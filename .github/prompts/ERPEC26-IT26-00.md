# Prompt Haiky IT26-00 — Diagnóstico y despliegue de gobierno

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 26-09-2026 (diagnóstico integral con énfasis en UI/UX de tropicalización a Ecuador, erradicación de referencias a Enterprise, plan Haiky IT26, contexto, AuditLock y prompts por fases).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRACION_TROPICALIZACION_IT26.md y docs/PLAN_HAIKY_INTEGRACION_TROPICALIZACION_IT26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: Ninguna; es la fase de diagnóstico y despliegue del plan.
Hallazgos: Todos (IT26-01 a IT26-10).

## Tareas y criterios de aceptación

1. **IT26-00.1** Diagnóstico técnico integral publicado con evidencia (`docs/DIAGNOSTICO_INTEGRACION_TROPICALIZACION_IT26.md`, `docs/evidencias/IT26/hallazgos.json`).
2. **IT26-00.2** Plan Haiky IT26, prompts `ERPEC26-IT26-*.md`, `.github/CODEX_CONTEXT.md` y `.vscode/AuditLock.json` desplegados y verificados con `node scripts/verify-governance.cjs`.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.

## Validación y límites

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/IT26/IT26-00-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `integrationTropicalizationIT26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: IT26-00 task: IT26-00.Y`.
