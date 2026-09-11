# Contabilidad Community y demo comercial

El titular pidió completar los entregables fiscales, mejorar la entrada de Contabilidad, crear una empresa demo comercial y reservar el RUC de SINKRONET exclusivamente para el emisor de Facturador/Founder. Este incremento no cierra las fases 05–07 ni elimina sus obligaciones.

## Flujo instalado

El módulo propio `erpec_withholding_accounting` agrega **Contabilidad ERP EC** como aplicación y menú. Incluye accesos a asientos, movimientos/mayor, cuentas, diarios (según permisos), facturas de clientes/proveedores y retenciones. El administrador del cliente piloto recibe el grupo contable que permite mostrar estas funciones.

El balance de comprobación agrupa exclusivamente apuntes contabilizados de la empresa y período seleccionados. Separa saldo inicial, debe, haber y saldo final; permite abrir los movimientos de cada cuenta. No pretende sustituir estados financieros completos, ATS o declaraciones tributarias. Cambiar los filtros en pantalla limpia el resultado anterior y exige recalcular.

Las retenciones son documentos contables independientes con factura, fecha, referencia, conceptos, bases, porcentajes verificados y cuentas tributarias. Las emitidas debitan proveedores y acreditan cuentas tributarias de pasivo; las recibidas debitan cuentas tributarias de activo y acreditan clientes. El asiento queda balanceado y se concilia con el saldo pendiente. No hay tarifas legales elegidas automáticamente.

La acción de contabilizar es idempotente por documento: repetirla abre el mismo asiento. Se rechaza superar el saldo pendiente. La reversión exige fecha y motivo, crea un asiento inverso y restituye el saldo de esa retención; conserva otras conciliaciones. Los documentos, líneas y asientos generados se protegen frente a modificaciones, borrado, retorno a borrador y eliminación directa de conciliaciones. Se bloquean documento y factura antes de contabilizar/revertir; los tests realizados son secuenciales, no una prueba de carga concurrente.

El alcance contable de este incremento es una factura por retención y moneda USD para factura y empresa. El registro contable no declara autorización ni anulación ante el SRI. La referencia la introduce el responsable y debe contrastarse con el comprobante fiscal. Las líneas preliminares del módulo anterior no se contabilizan automáticamente.

En compras, las líneas marcadas **Reembolso de gastos** deben tener sustentos vinculados a esa misma factura. Antes de contabilizar se comprueba que subtotales e impuestos del respaldo coincidan con los importes de las líneas calculados por Odoo. No se duplica el asiento ni el motor de impuestos. El tratamiento fiscal completo, los códigos ATS, la validación del XML del sustento y su transmisión al Facturador siguen siendo entregables obligatorios de la fase fiscal; esta comparación no acredita cumplimiento integral.

## Demo comercial

`scripts/create-demo.py` crea una base y un usuario PostgreSQL propios (`erpec_demo`), archivos separados y un servidor local en el puerto **8369**. No clona datos del cliente 8186 ni expone servicios a Internet. La cuenta Odoo se llama **demo**; la contraseña aleatoria se guarda exclusivamente en `.cache/windows/demo/ACCESO_DEMO.txt`.

La empresa se llama **Comercial Andina DEMO — Datos ficticios**, no tiene RUC y presenta clientes, proveedores, cotización, venta, compra, facturas y retenciones sintéticas. Los porcentajes del ejemplo sirven para mostrar el flujo, no como una recomendación tributaria. No hay un conector fiscal instalado en la demo ni tareas programadas habilitadas. No se incorporan credenciales de Founder o PayPhone.

El script usa una marca persistente para no volver a sembrar ni cambiar contraseñas al arrancar una demo ya inicializada. La demo no se borra ni restaura automáticamente: cualquier reinicio de datos debe planificarse conservando primero su base y filestore. Para detenerla, identificar su proceso mediante `.cache/windows/demo/pid` y comprobar que utiliza `.cache/windows/demo/odoo.conf`; no detener PostgreSQL ni otros clientes.

## Emisor local reservado para Founder

Por indicación expresa del titular, `scripts/create-test-issuer.cjs` creó la cuenta `info@sinkronet.com.ec` y el RUC `1793235327001` únicamente en la base local de Facturador `sinkronet_fact` (PostgreSQL 5432). El usuario y su Empresa quedaron en ambiente **1 — pruebas**. Se conservaron los identificadores independientes de usuario, Empresa y Workspace, obtenidos del servicio de estructura comercial del producto.

No se trasladó ese RUC a Odoo. No se cambió otro emisor, no se otorgó SUPERADMIN, no se aceptaron contratos, no se simuló un pago y no se enviaron correos. No se crearon claves API activas ni se emitieron comprobantes. El alta no acredita identidad por correo, firma, punto de emisión ni habilitación de API: esas verificaciones deben completarse antes del ensayo real. La cuenta no se marcó como emisor de facturación del proveedor; la configuración definitiva de Founder permanece separada.

La clave de acceso local queda en `.cache/windows/facturador-test-issuer.json`; nunca se agrega al repositorio. Una futura credencial para esta integración deberá ser `PRUEBAS`, con alcance mínimo y correspondencia explícita de Empresa/Workspace. No basta el correo o el RUC para resolver la asociación.

## Validación, entrega y reversión

`verify-accounting.py` prueba el módulo en una copia aislada del cliente; `install-accounting.py` exige hashes y resultado positivo, respalda base/filestore y reinicia únicamente 8186. La evidencia distingue pruebas automatizadas, instalación y demo. La rama conserva los locks históricos sin declarar cierre de fases.

Para revertir funcionalmente una retención se usa **Revertir asiento**, nunca se borra el comprobante. Para retirar el incremento después de haber contabilizado, conservar el módulo y sus datos para consulta; una restauración técnica exige detener el cliente afectado y restaurar juntos el respaldo de base, filestore y versión de módulos compatible. No se proporciona ni ejecuta un borrado automático de esos datos.

Referencia de requisitos externos: [Facturación electrónica del SRI](https://www.sri.gob.ec/facturacion-electronica). La emisión de pruebas y la producción son ambientes distintos; las verificaciones locales descritas aquí no equivalen a una autorización SRI.
