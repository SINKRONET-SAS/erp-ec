# Prompt Haiky DI26-A — Operación, esquema y validación reproducible

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Autorización vigente: pedido del titular del 25-09-2026 (desplegar el plan DI26, ejecutar todos sus prompts, verificar y corregir, commit y push).

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI26.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI26.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **DI26-00**. Exigir cierre firmado válido de la dependencia en `diagnosticImprovementDI26` del AuditLock; no saltar de fase.
Hallazgos: DI26-01, DI26-13.

## Tareas y criterios de aceptación

1. **DI26-A.1** Cada módulo propio con cambios de modelo posteriores a su última versión sube de versión; la verificación de versiones queda en una prueba.
2. **DI26-A.2** `scripts/check-schema-drift.py` compara el registro de Odoo con las columnas de cada instancia y sale con código distinto de cero si hay desfase.
3. **DI26-A.3** `scripts/update-instance.py` respalda y actualiza todos los módulos `erpec_*` instalados de una instancia; `manage-odoo.py update()` deja de actualizar solo `erpec_base`.
4. **DI26-A.4** El sellado del AuditLock (`scripts/seal-auditlock.cjs`) y los recorridos de UI (`scripts/ui-menu-crawl.py`, `scripts/ui-roles-battery.py`) viven en el repositorio y son reproducibles.
5. **DI26-A.5** Las pruebas de Tesorería y exportación bancaria crean su propia política de nómina y se ejecutan en una base limpia (y por tanto en CI); solo las pruebas de saneamiento de la demo siguen requiriéndola.

Reproducir cada defecto con datos ficticios o copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad y migración reversible. No duplicar autoridades ni estados. Exponer en frontend lo que afecte al usuario (RULES.md §8), con mensajes en español de Ecuador.

Reversión: las versiones y scripts se revierten con git; las actualizaciones de instancia tienen respaldo previo.

## Validación y límites

Ejecutar las pruebas del módulo afectado y la suite integrada al cambiar comportamiento; registrar pruebas, fallos, errores, omisiones, entorno y commit, exigiendo código de salida.
Respaldar antes de actualizar instancias (demo, fundador, inquilinos) y comprobar el desfase de esquema al terminar.
No modificar repositorios fuente. No enviar comprobantes, correos ni fondos reales. No publicar secretos. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI26/DI26-A-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar la sección vigente del contexto conservando historia y sellar el AuditLock con `scripts/seal-auditlock.cjs` (bytes del lock anterior archivados, SHA256 y firma; hashes de entregables sin el propio lock). UTF-8 sin BOM y LF.
Actualizar `diagnosticImprovementDI26`. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial o bloqueada con causa; no cerrar ficticiamente. Commits con `phase: DI26-A task: DI26-A.Y`.
