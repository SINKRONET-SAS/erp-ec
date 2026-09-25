# Prompt Haiky DI26-B — Integridad fiscal y de pagos

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 25-09-2026 (desplegar el plan DI26, ejecutar todos sus prompts, verificar y corregir, commit y push).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI26.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **DI26-A**. Exigir cierre firmado válido de la dependencia en `diagnosticImprovementDI26` del AuditLock; no saltar de fase.
Hallazgos: DI26-02, DI26-03, DI26-12, DI26-11 (cuentas e identificación).

## Tareas y criterios de aceptación

1. **DI26-B.1** Leer los avisos del plan de impuestos no altera el sustento ATS guardado; el sustento solo se recalcula al cambiar producto, tercero o empresa, y nunca pisa un valor manual.
2. **DI26-B.2** La exportación bancaria usa el tipo de identificación declarado; conserva pasaportes alfanuméricos y rechaza identificaciones que no cumplan el formato del banco.
3. **DI26-B.3** La cuenta propia de la empresa se toma de la cuenta del diario bancario de nómina (una sola autoridad); se retira `erpec.bank.company.account`.
4. **DI26-B.4** Una empresa puede marcarse como de ensayo; sus archivos XML de anexos se nombran como ensayo no presentable y la UI lo advierte. La empresa ficticia de la demo queda marcada.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.

Reversión: migración de datos de cuentas propias documentada; restaurar desde respaldo si se requiere el modelo retirado.

## Validación y límites

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI26/DI26-B-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `diagnosticImprovementDI26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: DI26-B task: DI26-B.Y`.
