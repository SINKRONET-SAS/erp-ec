# Arquitectura propuesta y contratos por cerrar

## Decisiones iniciales
Odoo Community 18 oficial, módulos propios separados del núcleo y instalación Windows nativa reproducible para desarrollo local. Producción en Render con contenedores Linux, PostgreSQL y servicios separados; Cloudflare para DNS/proxy del dominio futuro. PAYPHONE es el proveedor de cobro seleccionado. Véase PRODUCCION_RENDER_CLOUDFLARE.md. La referencia Enterprise local no será distribuida. Mantener inicialmente los motores de SKNOMINA y Facturador por API. Portar lógica propia solo con una decisión documentada de costo, licencia, equivalencia, migración y autoridad única.

Portal de suite → control de organizaciones, planes y aprovisionamiento → instancia Odoo y conexiones a los dos productos. El controlador de infraestructura debe estar aislado del frontend y no aceptar comandos arbitrarios. Base y archivos aislados por cliente, PostgreSQL con permisos mínimos, host asociado a base, HTTPS y administrador de bases no expuesto. Probar restauración de base y filestore juntos.

## Autoridad de datos
| Objeto | Autoridad inicial propuesta | Intercambio |
|---|---|---|
| Organización y productos contratados | Control de suite | Mapeo explícito hacia cada producto, autorización antes de vincular |
| Venta, compra, inventario y asiento contable | Odoo | Solicitud fiscal y recepción de estado; no crear segunda factura por reintento |
| Empleado, novedades y cálculo de nómina | SKNOMINA | Identificadores y resumen/asiento aprobado; mínima información personal |
| Clave de acceso, secuencial fiscal, XML y autorización | Facturador | Resultado fiscal vinculado al documento Odoo; no generar dos secuenciales |
| Cobro del servicio de suite | Responsable obligatorio por contrato, sin cargo automático (docs/CONTRATOS_SUITE.md) | Evitar doble suscripción/cargo; conservar contratos existentes |

La correspondencia debe incluir organizationId, sknominaTenantId, facturadorEmpresaId, instancia Odoo y companyId. No tratar esos identificadores como intercambiables. Resolver altas y vinculación de cuentas existentes mediante autorización de sus administradores. Definir acceso común con identidad federada; no compartir JWT ni claves maestras entre productos.

## Contratos observados
- Facturador: GET /api/integrations/v1/capabilities, POST /api/integrations/v1/invoices, GET /api/integrations/v1/invoices/:externalReference. Autenticación API por empresa y origen; el catálogo observado no declara ODOO. El payload y los errores deben fijarse con pruebas antes del conector.
- Facturador: webhooks con HMAC-SHA256; examinar persistencia de entrega, reinicios, firma sobre bytes originales, expiración, replay y consulta de respaldo. La firma por sí sola no garantiza entrega durable.
- SKNOMINA: rutas externas /employees, /attendance/marks, /novelties, /payroll/:anio/:mes. Confirmar prefijo montado en fase 01. No se observó en ese router una API explícita para asientos contables.
- Los conectores propuestos deben incluir organizationId validado por credencial, eventId, externalReference, schemaVersion, correlationId y clave de idempotencia cuando corresponda. Estos campos son una propuesta, no un contrato vigente de los productos.

## Flujos de aceptación
1. Pago verificado o alta comercial autorizada → derechos por producto → trabajo durable de aprovisionamiento → comprobación de salud → acceso visible. Reintento no crea otra instancia ni otro cargo.
2. Documento aprobado en Odoo → outbox → Facturador → estado pendiente visible → autorización/rechazo → conciliación. Nunca mostrar autorizado por recibir HTTP 200/202.
3. Nómina cerrada → mapeo de cuentas y centros → asiento borrador balanceado → revisión/aprobación → trazabilidad al período. Cambio o reversión genera operación controlada; no sobrescribe asiento publicado.
4. Vencimiento → política comercial visible → suspensión reversible de operaciones nuevas según contrato, conservando acceso a documentos/exportaciones exigibles. No borrar datos por impago.

## Operación y monetización
Planes deben separar productos, aplicaciones, usuarios, empresas, almacenamiento, documentos fiscales, capacidad API, soporte, respaldo y vigencia. Publicar límites concretos y costo de implementación aparte de recurrencia. No fijar precios hasta medir infraestructura, licencias de complementos, soporte, cobro y margen.

Paneles mínimos: productos contratados, instancia y dominio, permisos, conexiones, bandeja de errores/reintentos, estado fiscal, conciliación, uso de cuotas y respaldos. Texto de capacidad depende del derecho real; nunca mostrar incluido y bloqueado simultáneamente.

Antes de producción: pruebas de aislamiento y permisos, recuperación tras caída, restauración, observabilidad, políticas de datos y retención, revisión de licencias y formatos SRI vigentes. Secretos y certificados nunca se incluyen en documentación ni repositorios.
