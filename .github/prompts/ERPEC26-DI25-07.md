# Prompt Haiky DI25-07 — Aceptación operativa y salida controlada

Ejecutar exclusivamente esta fase cuando se invoque este prompt con autorización. Su publicación no inicia correcciones.

## Entrada y dependencia

Leer RULES.md, AGENTS.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, docs/DIAGNOSTICO_INTEGRAL_DI25.md y docs/PLAN_HAIKY_DIAGNOSTICO_MEJORA_DI25.md.
Ejecutar `node scripts/verify-governance.cjs` antes de modificar; revisar git status y preservar cambios ajenos.
Dependencia: **DI25-06**. Exigir cierre firmado válido de la dependencia en diagnosticImprovement del AuditLock; no saltar de fase.
Hallazgos: DI25-20 y regresión de todos. Validar ciclos operativos y despliegue real empaquetado; recuperación, CI, SMTP, SRI y bancos según alcance contratado. Sin gates aprobados no hay cierre comercial.
Responsables y reversión específicos: consultar la sección de esta fase en el plan.

## Tareas y criterios de aceptación

1. **DI25-07.1** Ventas→entrega parcial→factura→nota→cobro; compras→recepción parcial→factura→retención→pago→devolución; producción→faltantes→parcial→desperdicio→valoración.
2. **DI25-07.2** Importación multiproducto/divisa/costos; nómina→novedades→beneficios→anticipo→asiento→pago→reversión; visitas planificadas/omitidas/excepciones; plan SaaS→cobro→aprovisionamiento sin duplicar.
3. **DI25-07.3** Roles vendedor/comprador/bodega/operario/supervisor/nómina/contador/administrador: permisos, multiempresa, errores, vacíos, reintentos y doble acción concurrente.
4. **DI25-07.4** Imagen final sin montajes, CI remoto del commit final, respaldo DB+filestore+clave separada y restauración aislada con RPO/RTO medidos.
5. **DI25-07.5** SRI producción supervisada por responsable, SMTP con destinatario autorizado y homologación por banco/servicio solo con autorización específica; cada externo tiene acuse o bloqueo explícito.
6. **DI25-07.6** Salida por alcance: cero P1 abiertos en funciones liberadas, regresión aprobada, aceptación de negocio y evidencia legal/operativa. Una función bloqueada queda deshabilitada/claramente excluida, nunca marcada como cumplida.

Reproducir cada defecto o riesgo con datos ficticios/copia aislada antes de corregir; si no se confirma, documentarlo. Verificar usos de funciones públicas, compatibilidad, migración reversible y equivalencia. No duplicar autoridades ni estados. Exponer rutas, pantallas, permisos, vacío, carga, error y bloqueo externo con siguiente acción. Validar navegación y carga/compilación de vistas.

## Validación y límites

Ejecutar criterios de esta fase y pruebas pertinentes, incluida suite integrada al cambiar comportamiento. Registrar número de pruebas, fallos, errores, omisiones, entorno y commit. Exigir código de salida, no solo resumen verde.
Respaldar antes de instalar y verificar en copia aislada; aplicar reversión específica del plan. No reescribir asientos ni usar restauración como anulación fiscal.
No modificar repositorios fuente. No enviar comprobantes/correos/fondos reales para probar riesgos. No publicar secretos ni pedir los ya disponibles. No convertir XSD, simulación o documentación en cumplimiento legal.

## Cierre y gobierno

Crear `docs/evidencias/DI25/DI25-07-cierre.json` solo tras ejecutar validaciones; separar comprobadas, pendientes y límites.
Actualizar sección vigente del contexto conservando historia. Archivar bytes exactos del AuditLock anterior con nombre único; registrar SHA256 y firma SHA256(bytes anteriores + updatedAt UTF-8); hashes de entregables excluyen el lock. Binarios mediante manifiesto con hashes.
Guardar UTF-8 sin BOM, verificando `Buffer.from(text, 'utf8').toString('utf8') === text` en cada escritura.
Actualizar diagnosticImprovement; conservar fases maestras y pendientes externos. Repetir `node scripts/verify-governance.cjs` al cierre.
Si falta un criterio, registrar fase parcial/bloqueada y causa; no cerrar ficticiamente ni comenzar sucesora. Commits solo autorizados con `phase: DI25-07 task: DI25-07.Y`.
