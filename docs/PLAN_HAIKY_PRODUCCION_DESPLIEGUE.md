# ERPEC26-OP11 — Producción, despliegue y anexo ATS completo

## Origen

El titular compartió un "Diagnóstico Integral del Proyecto ERP EC" fechado 17-09-2026, con una sección de "Tareas Inmediatas" y otra de "Requisitos Previos al Despliegue en Producción". Antes de planificar, se verificó el estado real del repositorio: **la sección "Tareas Inmediatas" del diagnóstico ya está desactualizada** — OP10.A2 (reportes de nómina), OP10.A3 (envío del rol de pago), OP10.A4 (saldos iniciales) y OP10.B3 (reportes de visitas) se completaron y cerraron en esta misma sesión, con pruebas, ensayo real, evidencia y commits (`1c623b0`, `4a3e409`, `a32adfe`, `e48c8da`). El pendiente de aprovisionamiento (`erpec_payroll`/`erpec_field_routes` para clientes nuevos) también se cerró (`cd5a219`). Este plan cubre exclusivamente lo que el diagnóstico lista en **"B. Requisitos Previos al Despliegue en Producción (Cloud / Render)"**, que sí sigue genuinamente pendiente.

## Alcance: cuatro frentes, con distinto grado de bloqueo externo

### B1 — Generación completa del ATS (ejecutable ahora)

Brecha real, ya documentada en `docs/ALCANCE_ATS_RDEP.md`: el Catálogo ATS oficial ya está transcrito (`addons/erpec_fiscal_native/ats_catalog.py`), pero la generación de las secciones compras/ventas del ATS requiere clasificar, por cada documento, qué código de sustento tributario (Tabla 5 del catálogo, 16 códigos) le corresponde — una clasificación que no existía en ningún modelo del ERP.

**Fase B1a — COMPLETADA el 18-09-2026.** `ats_sustento_code` agregado a `erpec.tax.case` (motor de intersección de planes tributarios en `erpec_workspace/tax_intersection.py`, TX07), resuelto automáticamente por línea de factura de compra cuando los casos del tercero y del producto coinciden en el mismo código, editable a mano cuando no hay coincidencia o no está configurado. Solo aplica a compras/facturas de proveedor/importaciones — confirmado contra `ats.xsd`: `codSustento` es obligatorio únicamente en `detalleComprasType`, no en `detalleVentasType`.

Dos gaps reales encontrados al correr por primera vez la batería completa de `erpec_workspace` en una base verdaderamente aislada (nunca antes ejercitada así, solo contra bases con plan de cuentas EC ya aplicado): una prueba preexistente dependía implícitamente de que la empresa tuviera `country_id=Ecuador`, y del grupo de impuestos por defecto que eso cambiaba, dejando en cero la base de una retención de IVA. Ambos corregidos en el propio `setUp` de la prueba (país explícito + grupo de IVA explícito), sin tocar el motor de intersección. 7 pruebas nuevas (39 en total en el módulo, 0 fallos/errores). Reinstalado en demo con respaldo previo. **Ensayo real contra la demo** (XML-RPC, no simulado): una factura de compra real resuelve `erpec_ats_sustento_code='02'` automáticamente desde el caso configurado. Detalle: `docs/evidencias/ERPEC26-OP11-B1A-SUSTENTO-ATS-20260918.json`.

Fase B1b (siguiente incremento, no en este): agregador `erpec.fiscal.ats.report` por período/empresa que ensamble las secciones `compras` y `ventas` del XML raíz `ivaType` a partir de facturas/comprobantes ya contabilizados, validado contra `ats.xsd`, con el mismo patrón ya usado para RDEP (`erpec.payroll.rdep`). Se difieren explícitamente `exportaciones`, `recap`, `fideicomisos`, `anulados` y `rendFinancieros` a un tercer incremento, igual que RDEP se corrigió en varias pasadas — no se improvisa una sola pasada gigante sobre una estructura con más de 20 campos obligatorios por detalle.

### B2 — Infraestructura Cloud (Render + Cloudflare): parcialmente ejecutable

Ya existe trabajo real de una fase anterior (OP04 segunda pasada, ver `docs/LINUX_RENDER.md` y `docs/PRODUCCION_RENDER_CLOUDFLARE.md`): imagen Linux reproducible, verificador Docker, plantilla `deployment/render.customer.example.yaml`. Lo que sigue pendiente y **bloqueado por falta de acceso real**: "Acceso al proyecto/espacio de Render y elección de región y recursos" (textual, `docs/PRODUCCION_RENDER_CLOUDFLARE.md` línea 25) — sin una cuenta/espacio de Render provisto por el titular, no se puede desplegar de verdad, solo seguir preparando código y configuración localmente. Lo ejecutable sin esa cuenta: adaptar el trabajador de aprovisionamiento (`scripts/provision-worker.py`, hoy exclusivo de Windows/`msvcrt`) a un patrón compatible con background workers de Render (cola idempotente, sin locks de archivo específicos de Windows), y agregar `wkhtmltopdf` a la imagen Linux (`deployment/linux/Dockerfile`), ya que el ensayo Docker registrado documenta explícitamente su ausencia.

### B3 — Producción fiscal SRI (bloqueado, solo documentado)

Cargar el certificado `.p12` definitivo de la empresa emisora en producción y habilitar `cel.sri.gob.ec` requiere un certificado de producción real, que solo el titular puede proveer (mismo límite ya aplicado en OP09: el certificado usado hasta ahora es de un Founder/colaborador de confianza, válido solo para el ambiente de pruebas `celcer.sri.gob.ec`). El mecanismo de activación de producción ya existe en el código y está deliberadamente deshabilitado (ver `AuditLock.json`, pendiente ya registrado desde OP09). No se ejecuta nada en este incremento; se deja documentado.

### B4 — Homologación bancaria (bloqueado, solo documentado)

Generar y validar lotes reales de pago en los formatos específicos de Banco Pichincha y Produbanco requiere credenciales/especificaciones de prueba de esos bancos, que el titular no ha provisto. `erpec_treasury` ya tiene las fichas técnicas de 7 bancos mapeadas (ver diagnóstico, sección E) pero sin homologación real. No se ejecuta nada en este incremento; se deja documentado como pendiente externo.

## Orden de ejecución de este incremento

1. **B1a** (ATS: sustento tributario por línea de compra) — código, pruebas en base aislada, instalación en demo con respaldo, ensayo real.
2. Verificación de regresiones sobre `erpec_workspace` completo (motor de intersección TX07, planes de impuestos, flujo de compras) y sobre los módulos tocados en el resto de la sesión (`erpec_payroll`, `erpec_field_routes`).
3. Cierre de gobierno: `AuditLock.json`, `CODEX_CONTEXT.md`, evidencia en `docs/evidencias/`, commit y push.

B1b, B2 (adaptación Render), B3 y B4 quedan explícitamente pendientes de este plan, con su bloqueo documentado arriba — no se fabrica evidencia de ejecución sobre lo que depende de un recurso externo no provisto.

## Criterios de aceptación

Igual que el resto del proyecto: (1) probar en base aislada y nueva antes de instalar en demo; (2) instalar solo con respaldo previo; (3) no declarar una homologación bancaria, una activación de producción SRI o un despliegue real sin decirlo explícitamente; (4) documentar exactamente qué queda pendiente y por qué.

## Verificación y cierre

Commits con `phase: ERPEC26-OP11` y `task: ERPEC26-OP11.<fase>` (p. ej. `ERPEC26-OP11.B1a`). No se cierra este plan por un incremento: B1b, B2, B3 y B4 permanecen pendientes hasta que se levanten sus bloqueos reales o el titular decida un alcance distinto.
