# Prompt Haiky DI26-E — Español de Ecuador, UI y accesibilidad

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 25-09-2026 (desplegar el plan DI26, ejecutar todos sus prompts, verificar y corregir, commit y push).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI26.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **DI26-D**. Exigir cierre firmado válido de la dependencia en `diagnosticImprovementDI26` del AuditLock; no saltar de fase.
Hallazgos: DI26-07, DI26-08, DI26-09, DI26-14, DI26-16, P3.

## Tareas y criterios de aceptación

1. **DI26-E.1** Idioma por defecto es_EC y zona America/Guayaquil para contactos y empresas; el aprovisionamiento lo aplica a cada inquilino; migración para bases existentes.
2. **DI26-E.2** Ningún campo propio visible con etiqueta automática en inglés.
3. **DI26-E.3** Avisos veraces en la factura (vista previa) y en el RDEP.
4. **DI26-E.4** Alertas con `role` en todas las vistas propias; el sitio público usa es_EC por defecto.
5. **DI26-E.5** La demo retira módulos ajenos al producto sin romper dependencias del ERP, con respaldo previo.
6. **DI26-E.6** Observaciones P3: mojibake de `install-fiscal.py`, tildes, usuario de prueba activo, advertencia de `compute_sudo`.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.


## Validación y límites

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI26/DI26-E-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `diagnosticImprovementDI26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: DI26-E task: DI26-E.Y`.
