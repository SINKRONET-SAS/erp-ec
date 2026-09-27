# Prompt Haiky IT26-E — Integración orgánica de nómina y empleados

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 26-09-2026 (diagnóstico integral con énfasis en UI/UX de tropicalización a Ecuador, erradicación de referencias a Enterprise, plan Haiky IT26, contexto, AuditLock y prompts por fases).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRACION_TROPICALIZACION_IT26.md y docs/PLAN_HAIKY_INTEGRACION_TROPICALIZACION_IT26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **IT26-D**. Exigir cierre firmado válido de la dependencia en `integrationTropicalizationIT26` del AuditLock; no saltar de fase.
Hallazgos: IT26-05.

## Tareas y criterios de aceptación

1. **IT26-E.1** Añadir smart buttons en `hr.employee`: `[Roles de Pago]` (abre las líneas de nómina del empleado), `[Décimos y Beneficios]` (abre las liquidaciones acumuladas) y `[Anticipos / Préstamos]` (abre las cuotas del colaborador).
2. **IT26-E.2** Limpiar la pestaña `Anexo RDEP` en `hr.employee` y `res.company`, transformando las alertas legales en campos ordenados con tooltips informativos.
3. **IT26-E.3** Mejorar la vista de períodos de nómina (`erpec.payroll.period`), reemplazando banners de alerta por estados de flujo y diseño profesional.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.

Reversión: las vistas de empleados y nómina se revierten con git; las actualizaciones de instancia tienen respaldo previo.

## Validación y límites

Preservar avisos de bloqueo, ambiente real de emisión, identificación de datos sintéticos y límites de validación externa; solo las notas de desarrollo y la ayuda pasiva se trasladan o retiran. Mantener permisos por rol y empresa, controles del servidor y avisos de licencias legalmente exigibles. La consolidación visual no autoriza eliminar modelos, tablas, historiales ni conectores activos; cualquier migración funcional necesita alcance y reversión propios.

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/IT26/IT26-E-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `integrationTropicalizationIT26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: IT26-E task: IT26-E.Y`.
