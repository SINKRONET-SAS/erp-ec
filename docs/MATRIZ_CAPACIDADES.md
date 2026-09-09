# Matriz de capacidades y dependencias

Evidencia: manifiestos locales y servicios de los dos productos. No equivale a validación funcional. Dependencias transitivas declaradas en evidencias/localizacion-ecuador.json; completar auditoría de bibliotecas en fase 01.

| ID | Capacidad y referencia | Licencia/dependencias observadas | Decisión inicial y falta por cubrir |
|---|---|---|---|
| EC01 | l10n_ec: cuentas, impuestos, documentos, bancos, identificaciones, pagos SRI | LGPL-3; account, base_iban, account_debit_note, l10n_latam_invoice_document, l10n_latam_base, base | Obtener del Community oficial; validar vigencia de catálogos, configuración por compañía y migración |
| EC02 | l10n_ec_stock | LGPL-3; l10n_ec, stock | Reutilizar versión oficial compatible y probar inventario por compañía |
| EC03 | l10n_ec_website_sale | LGPL-3; website_sale, l10n_ec | Reutilizar cuando comercio electrónico forme parte del alcance |
| EC04 | l10n_ec_edi: XML, firma, RIDE, autorización y retenciones | OPL-1; account_edi, certificate, l10n_ec | Cubrir con Facturador y módulo propio; auditar dependencias de certificate; no copiar fuentes |
| EC05 | l10n_ec_edi_stock: guías de remisión | OPL-1; stock_account, l10n_ec_edi | Conectar entregas con Facturador; API externa de guías aún no acreditada |
| EC06 | l10n_ec_edi_pos | OEEL-1; point_of_sale, l10n_ec_edi | Diseñar integración propia POS después del piloto de facturas |
| EC07 | l10n_ec_reports: balance/resultados | OPL-1; account_reports, l10n_ec | Evaluar reportes Community/OCA con licencias y cobertura verificadas, o desarrollo propio |
| EC08 | l10n_ec_reports_ats | OPL-1; l10n_ec_edi, l10n_ec_reports | Reutilizar motor ATS del Facturador si cubre todos los datos Odoo; comprobar API y compras externas |
| EC09 | SKNOMINA: empleados, marcas, novedades, nómina | API propia con permisos y plan; no equivale a API de asientos | Conector propio; definir cierre/reversión y mapeo contable, sin copiar hr_payroll Enterprise |
| EC10 | Facturador: solicitud/consulta factura externa | /api/integrations/v1; clave por empresa, referencia externa e idempotencia | Contratos, pruebas SRI y recuperación; registrar origen Odoo o decidir CUSTOM explícitamente |
| EC11 | SKNOMINA factura suscripciones mediante Facturador | facturadorClient.js, fiscalInvoiceService.js; ruta especializada /api/integrations/sknomina/invoices | Conservar separado de facturas comerciales emitidas por cada cliente |
| EC12 | Planes, usuarios y empresas en ambos productos | Modelos e identificadores diferentes; ver fuentes locales | Crear correspondencia y contrato de derechos por producto, sin mezclar credenciales ni cuotas |

Pruebas de referencia identificadas: retenciones básicas, múltiples facturas, pagos parciales y bases imponibles; ATS de ventas, compras, anulados y reembolsos. Usar estas categorías para diseñar pruebas propias con datos sintéticos y especificaciones vigentes; no incorporar fixtures propietarios.

Faltan: comparación contra commit oficial, licencias de dependencias y titularidad de código propio, validación normativa vigente, capacidades reales por API de cada comprobante, conector Odoo, administración SaaS y evidencia extremo a extremo. La existencia de un módulo o test no acredita su ejecución ni cumplimiento actual.
