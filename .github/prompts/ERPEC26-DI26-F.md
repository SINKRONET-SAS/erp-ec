# Prompt Haiky DI26-F — Coherencia documental y aceptación

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 25-09-2026 (desplegar el plan DI26, ejecutar todos sus prompts, verificar y corregir, commit y push).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI26.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **DI26-E**. Exigir cierre firmado válido de la dependencia en `diagnosticImprovementDI26` del AuditLock; no saltar de fase.
Hallazgos: DI26-10, DI26-11 (menús e ingresos), regresión de todos.

## Tareas y criterios de aceptación

1. **DI26-F.1** Las afirmaciones falsas de DI25 (certificado propio, talón, ventas ATS, envío masivo) se corrigen con nota fechada, sin borrar la historia.
2. **DI26-F.2** Una sola entrada de menú para las retenciones contables; las dos vías de ingresos no gravados quedan explicadas en la UI.
3. **DI26-F.3** Regresión integral: suite completa, desfase de esquema 0 en todas las instancias, recorrido de menús y batería de roles sin errores, CI verde.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.


## Validación y límites

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI26/DI26-F-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `diagnosticImprovementDI26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: DI26-F task: DI26-F.Y`.
