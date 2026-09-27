# Prompt Haiky IT26-F — Integración de guías de remisión en inventario

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 26-09-2026 (diagnóstico integral con énfasis en UI/UX de tropicalización a Ecuador, erradicación de referencias a Enterprise, plan Haiky IT26, contexto, AuditLock y prompts por fases).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRACION_TROPICALIZACION_IT26.md y docs/PLAN_HAIKY_INTEGRACION_TROPICALIZACION_IT26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **IT26-E**. Exigir cierre firmado válido de la dependencia en `integrationTropicalizationIT26` del AuditLock; no saltar de fase.
Hallazgos: IT26-04.

## Tareas y criterios de aceptación

1. **IT26-F.1** Mover la acción de Guías de Remisión al menú nativo de `Inventario -> Operaciones -> Guías de remisión SRI`.
2. **IT26-F.2** En `stock.picking`, asegurar que el botón de generación de guía en el header y el smart button de enlace a la guía emitida sigan el patrón estándar de Odoo.
3. **IT26-F.3** Retirar el acceso a guías del menú secundario de pruebas fiscales.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.

Reversión: las vistas de inventario y guías se revierten con git; las actualizaciones de instancia tienen respaldo previo.

## Validación y límites

Preservar avisos de bloqueo, ambiente real de emisión, identificación de datos sintéticos y límites de validación externa; solo las notas de desarrollo y la ayuda pasiva se trasladan o retiran. Mantener permisos por rol y empresa, controles del servidor y avisos de licencias legalmente exigibles. La consolidación visual no autoriza eliminar modelos, tablas, historiales ni conectores activos; cualquier migración funcional necesita alcance y reversión propios.

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/IT26/IT26-F-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `integrationTropicalizationIT26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: IT26-F task: IT26-F.Y`.
