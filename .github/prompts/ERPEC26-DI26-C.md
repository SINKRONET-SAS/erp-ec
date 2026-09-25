# Prompt Haiky DI26-C — Nómina: décimos

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 25-09-2026 (desplegar el plan DI26, ejecutar todos sus prompts, verificar y corregir, commit y push).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI26.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **DI26-B**. Exigir cierre firmado válido de la dependencia en `diagnosticImprovementDI26` del AuditLock; no saltar de fase.
Hallazgos: DI26-05.

## Tareas y criterios de aceptación

1. **DI26-C.1** Régimen del décimo cuarto (Sierra/Amazonía o Costa/Insular) por empleado con valor por defecto de la empresa.
2. **DI26-C.2** Liquidación de décimos: suma lo acumulado no pagado de los períodos contabilizados hasta el mes de corte, propone el corte y la fecha límite legal (décimo tercero: 24 de diciembre, art. 111 CT; décimo cuarto: 15 de marzo Costa/Insular y 15 de agosto Sierra/Amazonía), traslada el pasivo a nómina por pagar y permite registrar el pago por empleado sin duplicar lo ya liquidado.
3. **DI26-C.3** Pantallas, permisos y pruebas; el corte es editable porque el texto legal habla de "año calendario" y el corte de noviembre es práctica del Ministerio del Trabajo.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.

Reversión: la liquidación se revierte con asiento inverso mientras no tenga pagos conciliados.

## Validación y límites

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI26/DI26-C-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `diagnosticImprovementDI26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: DI26-C task: DI26-C.Y`.
