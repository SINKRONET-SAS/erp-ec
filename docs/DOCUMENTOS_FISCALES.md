# Documentos Ecuador dentro de ventas y compras

Incremento local autorizado por el titular el 10 de septiembre de 2026. Implementado sobre Odoo Community, sin dependencia Enterprise. La prioridad funcional adelanta preparación documental mientras sigue pendiente la infraestructura cloud de la fase 04; no cierra ni reescribe las fases bloqueadas del AuditLock.

## Uso en el cliente piloto

Abrir una factura de cliente o proveedor y seleccionar la pestaña **Ecuador**. Allí se muestran los pedidos de venta o compra que originaron las líneas y, cuando corresponde, el documento rectificado mediante el vínculo nativo de Odoo.

En facturas de proveedor de empresas de Ecuador, en USD:

- **Preparación de retenciones:** elegir un concepto del catálogo de retenciones de compras, indicar su base y documentar la revisión de vigencia. Se calcula un importe preliminar. No se selecciona automáticamente una tarifa ni se acredita que el catálogo heredado esté actualizado legalmente. No genera asiento, pago, XML, autorización ni reducción del saldo.
- **Reembolso de gastos:** registrar emisor, tipo, número, fecha e importes de los comprobantes de sustento antes de contabilizar la factura. Se evita repetir el mismo número normalizado, emisor y tipo dentro de la empresa. No reparte un sustento entre varias facturas ni recalcula líneas o impuestos de la factura. No es una nota de crédito ni una devolución de compra.

Los registros pertenecen a la empresa de su factura y requieren permisos de facturación y escritura sobre ella. No se copian al duplicar la factura. Cambiar empresa, moneda, proveedor o tipo exige resolver antes los respaldos existentes. Los sustentos de reembolso quedan bloqueados al contabilizar. Las retenciones siguen siendo preparación editable, incluso sobre facturas contabilizadas, porque aún no existe emisión ni asiento propio.

## Pendientes expresos

1. Tratamiento contable de retenciones: documento emitido, cuentas, contrapartida de proveedor, conciliación y reversión; retenciones recibidas en ventas.
2. Tratamiento completo del reembolso: impuestos, distribución y conciliación con líneas contables; identidad fiscal del emisor y duplicados entre fichas de proveedor distintas.
3. Validación de tipos, identificaciones, numeración, fechas y tarifas contra la normativa vigente. Actualmente los campos capturan respaldo y aplican controles básicos, no validación fiscal integral.
4. Conector fiscal de factura, notas, retención, liquidación y guía con estados, firma, autorización, reintentos e idempotencia. La API externa del Facturador revisada expone facturas; sus otras rutas internas no constituyen todavía ese contrato externo.
5. Pruebas integrales en ambiente SRI de pruebas, XML/RIDE y correspondencia con el asiento. PayPhone es una integración de cobro distinta de la autorización fiscal.
6. Incorporar el módulo al aprovisionamiento de futuros clientes y a los contenedores Linux; este incremento se aplica al cliente Windows piloto 8186.

La referencia oficial es [Facturación electrónica del SRI](https://www.sri.gob.ec/facturacion-electronica), que al consultar mostraba ficha técnica 2.34 de julio de 2026. La ficha PDF no pudo descargarse en esta revisión; no se declara conformidad con ella. No se enviaron documentos al SRI.

## Verificación y despliegue local

`scripts/verify-fiscal.py` clona la base y su filestore, instala el módulo propio en esa copia y ejecuta pruebas con datos sintéticos, sin tareas programadas y con puerto HTTP efímero limitado a localhost (Odoo puede activar su servidor durante pruebas). `scripts/install-fiscal.py` exige resultado aprobado y coincidencia de archivos, comprueba la identidad del proceso, respalda base y filestore del cliente y reinicia exclusivamente el puerto 8186.

Los respaldos y credenciales permanecen privados en `.cache/windows`; la evidencia publicable registra alcance, hashes y resultado sin secretos. No se modifican PostgreSQL 5432, el operador 8169 ni los repositorios fuente.
