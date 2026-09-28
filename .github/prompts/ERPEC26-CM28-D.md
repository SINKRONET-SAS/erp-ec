# Prompt Haiky CM28-D — Monetización y aprovisionamiento

Autorización vigente: mandato del titular del 28-09-2026 de implementar CM28 completo y monetizar por cantidad de usuarios. No requiere nueva autorización para este alcance.

## Entrada y dependencia
Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/PLAN_HAIKY_COMERCIAL_MODULOS_ACTIVOS_CM28.md y docs/DIAGNOSTICO_COMERCIAL_MODULOS_ACTIVOS_CM28.md. Dependencia: CM28-C. Verificar node scripts/verify-governance.cjs y cierre firmado de la dependencia antes de modificar. Preservar cambios ajenos.

## Tareas y aceptación
Renovación sin débito automático, cola idempotente, módulos y usuarios contratados, derechos en servidor, estados derivados y activación de acceso de un uso.
Aplicar íntegramente las decisiones del plan. No adelantar fases. Reproducir defectos antes de corregir, evitar duplicación de autoridades y preservar APIs/datos históricos. Toda funcionalidad debe tener interfaz operable y permisos en servidor. Cantidad de usuarios incluida en cálculo y límite efectivo, sin contar portal ni técnicos.

## Verificación y reversión
Ejecutar pruebas focalizadas y suite correspondiente; registrar comandos, salida, fallos y omisiones. No sustituir pruebas por documentación. Cambios de datos requieren respaldo y reversión documentada; ensayar en copia aislada. Revisar UTF-8 sin BOM, mojibake, duplicaciones y regresiones. No modificar repositorios fuente ni enviar dinero, comprobantes o correos reales.

## Cierre
Registrar docs/evidencias/CM28/CM28-D-cierre.json con comprobado, pendiente y límites. Actualizar contexto conservando historia y commercialModulesAssetsCM28 en AuditLock. Sellar mediante scripts/seal-auditlock.cjs y verificar gobierno. No marcar completa si falta aceptación. Commit: phase: CM28-D task: CM28-D.N.
