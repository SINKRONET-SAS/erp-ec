# Plan HAIKY — Nómina segunda pasada y control de visitas de vendedores

Autorizado por el titular el 17-09-2026. Dos frentes planificados juntos, ejecutados por fases: (A) segunda pasada sobre `erpec_payroll` (envío de roles, parametrización de beneficios legales, reportes, saldos iniciales) y (B) una funcionalidad nueva — control de visitas/asistencia de vendedores por zona — que hoy no existe en el ERP. El titular pidió tomar como referencia `C:\proyectos web\nuevo_nomina` y `C:\proyectos web\sinkroniq-mobile`, adaptando patrones ya maduros de esos dos productos reales, sin conectar los sistemas en vivo (mismo patrón de todo el proyecto: leer, entender, portar el diseño, no copiar código ni depender del sistema externo).

## Investigación previa (agentes de solo lectura, sin modificar ninguna referencia)

**Estado actual de `erpec_payroll` (verificado directamente en este repositorio):** los beneficios legales (décimo tercero/cuarto, vacaciones, fondo de reserva) y el impuesto a la renta mensual ya se calculan, con parámetros 2026 bien fuenteados (`parameters_ec2026.py`, `SOURCES` con URLs oficiales). Confirmado que faltan por completo: reportes (el manifest no declara ningún archivo de reporte), envío de roles (solo `mail.thread` para chatter interno, sin plantilla de correo ni PDF), y carga de saldos iniciales (sin mecanismo alguno). Los parámetros legales viven en un diccionario Python fijo por año, no en un registro editable por un contable.

**`nuevo_nomina` (backend Node.js/Prisma):**
- Envío de roles: PDF (`payrollRolePdfService`) + email (`communicationService`, con auditoría y bloqueo de envíos falsos en producción) — pero disparado por evento ("al cerrar nómina"), no por un cron independiente.
- Beneficios legales: **patrón fuerte a adoptar** — `legal_parameter_versions` (una fila por país/año/parámetro/vigencia, con `validation_status` oficial/pendiente, fuente y URL trazables, override por cliente, y un gate `assertLegalParametersReadyForProduction()` que bloquea producción si algo no está validado oficialmente).
- Impuesto a la renta: integrado en el cálculo mensual con tablas versionadas — el límite de gastos personales es un número plano, sin escalar por cargas familiares/Galápagos (confirma que nuestro RDEP ya está por delante ahí).
- Saldos iniciales: **patrón fuerte a adoptar** — `initialBalanceService` con flujo CSV/XLSX → validación fila por fila (dry-run) → aplicación (`commit`) → reversión (`revert`), idempotente por hash de origen, auditado.
- Reportes: catálogo declarativo amplio (`payroll-report-catalog.json`) — resumen, detalle tabular, ficha de beneficios por empleado, puente contable (provisión/costo laboral), conciliación bancaria, exportables en PDF/XLSX/CSV.
- Control de visitas: existe una implementación propia (`routeVisitService.js`, geocerca Haversine, excepciones revisables, reportes de cumplimiento) — confirma que el patrón es genérico y ya se ha construido dos veces de forma independiente.

**`sinkroniq-mobile` (backend Node.js/Prisma + app móvil React Native):**
- **Control de visitas ("Rutas"), patrón fuerte a adoptar**: cinco entidades — `RouteSite` (zona/cliente con lat/lng, radio de geocerca, precisión GPS mínima), `RouteDay` (día planificado de un vendedor), `RouteStop` (parada planificada u ocasional, secuenciada), `RouteVisitMark` (marca de check-in/check-out con GPS, distancia Haversine, `withinGeofence`), `RouteException` (violación de geocerca u otra excepción, revisable pendiente/aprobada/rechazada). El dueño/administrador planifica el día (sitios y paradas); el vendedor ejecuta contra ese plan, con marcas fuera de geocerca guardadas igual pero marcadas para revisión (no bloqueadas de forma dura). Métricas: tasa de cumplimiento (paradas completadas/planificadas), tasa dentro de geocerca, excepciones pendientes. Reportes exportables CSV/XLSX/PDF.
- Proformas: flujo lineal borrador→enviada→aprobada→convertida, conceptualmente compatible con `sale.order`→`account.move` de Odoo (sin soportar facturación parcial ni múltiples facturas por proforma) — relevante solo como contexto de por qué el titular ve viable una integración conceptual más amplia; no es parte del alcance de este plan.

**No se portará**: cifrado/infra de mensajería (WhatsApp Cloud API, SMTP con marca blanca) — se usará el `mail.template`/`ir.cron` nativo de Odoo; el esquema de base de datos exacto de ninguno de los dos proyectos — se diseñan modelos Odoo propios inspirados en la misma lógica, no una migración de esquema.

## Fases (orden acordado: A1 → B1-B2 → A2-A4 → B3)

1. **A1 — Parametrización versionada de beneficios legales.** Nuevo modelo `erpec.payroll.legal.parameter` (o similar): un registro por año/parámetro/vigencia, con estado de validación oficial, fuente/URL, y un gate que bloquea el cálculo si se usa un parámetro no validado. Sustituye (sin perder) el `PARAMS` actual de `parameters_ec2026.py`, que pasa a ser el seed/dato inicial versionado, no la única fuente.
2. **B1 — Modelo de datos de control de visitas.** Nuevo addon (`erpec_field_routes` o nombre similar): sitio con geocerca, día de ruta planificado, parada, marca de visita, excepción — inspirado en `RouteSite/RouteDay/RouteStop/RouteVisitMark/RouteException` de sinkroniq-mobile, adaptado a modelos Odoo (`res.partner`/`hr.employee` como referencias en vez de tablas propias de cliente/vendedor).
3. **B2 — Registro de marcas de visita.** Acción de check-in/check-out (web, sin app móvil nativa en este alcance salvo que se pida aparte) con cálculo de distancia Haversine, validación de precisión GPS, y creación automática de excepción revisable cuando la marca cae fuera de la geocerca — sin bloquear de forma dura, igual que la referencia.
4. **A2 — Reportes de nómina.** Rol de pago en PDF (QWeb), resumen de nómina, ficha de beneficios acumulados por empleado, puente contable — inventario de reportes inspirado en `payroll-report-catalog.json`, ajustado a lo que el motor actual ya calcula.
5. **A3 — Envío automático del rol de pago.** Plantilla de correo + adjunto PDF, disparado al cerrar el período de nómina (evento, como la referencia) — no un cron independiente salvo que se decida lo contrario más adelante.
6. **A4 — Carga de saldos iniciales.** Patrón dry-run → commit → revert, idempotente por hash de origen, para altas de empresa/empleado a mitad de año (vacaciones acumuladas, décimos, fondo de reserva, préstamos/anticipos pendientes).
7. **B3 — Reportes de control de visitas.** Cumplimiento por vendedor/zona/día, tasa dentro de geocerca, excepciones pendientes — exportable, inspirado en los reportes de ruta de la referencia.

## Verificación y cierre

Cada fase: pruebas en base aislada y nueva, instalación en demo con respaldo previo, evidencia en `docs/evidencias/`, cierre de `AuditLock.json`, commit `phase: ERPEC26-OP10 task: <fase>` y push. No se cierra este plan por una fase — cada incremento documenta explícitamente lo que queda pendiente de las fases siguientes.

## Límites explícitos

No se conecta este ERP a nuevo_nomina ni a sinkroniq-mobile como sistemas vivos (decisión explícita del titular: solo referencia y portación de diseño). No se construye app móvil nativa en esta ronda — el control de visitas se opera desde la interfaz web de Odoo. No se activa envío real de correo en producción sin credenciales SMTP provistas por el titular (mismo patrón que el resto del proyecto: probado con mocks, ensayo real solo si el titular provee credenciales).
