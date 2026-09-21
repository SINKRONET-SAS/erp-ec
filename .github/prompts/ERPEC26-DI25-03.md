# Prompt Haiky DI25-03 — Nómina, correcciones y RDEP

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Su publicación no inicia correcciones.

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI25.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI25.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **DI25-02**. Exigir cierre firmado válido de la dependencia en diagnosticImprovement del AuditLock; no saltar de fase.
Hallazgos: DI25-04, DI25-05, DI25-06. Cálculo anual conciliado, beneficios conservados, cuotas reversibles y bases laborales justificadas; no reutilizar el mismo motor como único oráculo.
Responsables y reversión específicos: consultar la sección de esta fase en el plan.

## Tareas y criterios de aceptación

1. **DI25-03.1** Caso salarial variable reproduce la diferencia actual y queda conciliado contra cálculo independiente; creación fuera de orden no altera el año.
2. **DI25-03.2** Reversión/corrección conserva beneficios y saldo de préstamo; no duplica cuotas ni gastos; repetir acción es idempotente.
3. **DI25-03.3** Casos de otros empleadores, exenciones, acumulados, cambio de sueldo, ausencias y cierre anual tienen oráculo aprobado; bloquear regímenes no cubiertos.
4. **DI25-03.4** Frontend permite revisar bases, acumulados, ajustes y diferencias, con política/versionado; XSD RDEP y contenido económico se verifican por separado.

Reproducir cada defecto o riesgo con datos ficticios/copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad, migración reversible y equivalencia. No duplicar autoridades ni estados. Exponer rutas, pantallas, permisos, vacío, carga, error y bloqueo externo con siguiente acción. Validar navegación y carga/compilación de vistas.

## Validación y límites

Ejecutar criterios de esta fase y pruebas pertinentes, incluida suite integrada al cambiar comportamiento. Registrar número de pruebas, fallos, errores, omisiones, entorno y commit. Exigir código de salida, no solo resumen verde.
Respaldar antes de instalar y verificar en copia aislada; aplicar reversión específica del plan. No reescribir asientos ni usar restauración como anulación fiscal.
No modificar repositorios fuente. No enviar comprobantes/correos/fondos reales para probar riesgos. No publicar secretos ni pedir los ya disponibles. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI25/DI25-03-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar sección vigente del contexto conservando historia. Archivar bytes exactos del AuditLock anterior con nombre único; registrar SHA256 y firma SHA256(bytes anteriores + updatedAt UTF-8); hashes de entregables excluyen el lock. Binarios mediante manifiesto con hashes.
Guardar UTF-8 sin BOM, verificando `Buffer.from(text, 'utf8').toString('utf8') === text` en cada escritura.
Actualizar diagnosticImprovement; conservar fases maestras y pendientes externos. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial/bloqueada y causa; no cerrar ficticiamente ni comenzar sucesora. Commits solo autorizados con `phase: DI25-03 task: DI25-03.Y`.
