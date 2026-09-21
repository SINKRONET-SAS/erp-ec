# Prompt Haiky DI25-00 — Diagnóstico y planificación

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Su publicación no inicia correcciones.

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI25.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI25.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **—**. Conservar predecesor válido; alcance de diagnóstico/documentación.
Hallazgos: Todos. Informe, fuentes, reproducciones, capturas, plan y gobierno. Completada solo como diagnóstico/documentación; no corrige aplicación.
Responsables y reversión específicos: consultar la sección de esta fase en el plan.

## Tareas y criterios de aceptación

1. **DI25-00.1** Leer reglas y validar gobierno antes de editar.
2. **DI25-00.2** Diagnosticar con código, capturas actuales y fuentes oficiales; separar pruebas nuevas de historia.
3. **DI25-00.3** Publicar informe, plan, evidencia y gobierno; no corregir aplicación ni cerrar fases funcionales.

No cambiar código de negocio ni datos reales. Capturar pantallas y declarar límites de la revisión.

## Validación y límites

Ejecutar criterios de esta fase y pruebas pertinentes, incluida suite integrada al cambiar comportamiento. Registrar número de pruebas, fallos, errores, omisiones, entorno y commit. Exigir código de salida, no solo resumen verde.
Respaldar antes de instalar y verificar en copia aislada; aplicar reversión específica del plan. No reescribir asientos ni usar restauración como anulación fiscal.
No modificar repositorios fuente. No enviar comprobantes/correos/fondos reales para probar riesgos. No publicar secretos ni pedir los ya disponibles. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI25/DI25-00-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar sección vigente del contexto conservando historia. Archivar bytes exactos del AuditLock anterior con nombre único; registrar SHA256 y firma SHA256(bytes anteriores + updatedAt UTF-8); hashes de entregables excluyen el lock. Binarios mediante manifiesto con hashes.
Guardar UTF-8 sin BOM, verificando `Buffer.from(text, 'utf8').toString('utf8') === text` en cada escritura.
Actualizar diagnosticImprovement; conservar fases maestras y pendientes externos. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial/bloqueada y causa; no cerrar ficticiamente ni comenzar sucesora. Commits solo autorizados con `phase: DI25-00 task: DI25-00.Y`.
