# ERPEC26-01 — procedencia y contratos

Autorización: el usuario solicita ejecutar todas las fases, verificar, commit y push. Posteriormente solicita instalación Windows; esta instrucción sustituye la preferencia Linux del diseño.

Community oficial descargado en caché, revisión b1fd3a9eee5d575848ac649d2f5103537d8de7a4. No se copian fuentes Enterprise. scripts/audit-community.py comprueba revisión y cierre de dependencias de los módulos seleccionados mediante AST literal; informe community-audit.json. La copia Enterprise de referencia no acredita procedencia del Community instalado.

Soporte: Odoo publica septiembre 2027 como fin previsto de soporte estándar de 18.0: https://www.odoo.com/documentation/18.0/administration/supported_versions.html . Esto no concede soporte contractual Enterprise.

Fuente fiscal consultada 2026-09-09: https://www.sri.gob.ec/facturacion-electronica publica ficha offline 2.34, julio 2026. El índice de búsqueda mostraba 2.32; se contrastó la página actual. No usar los catálogos de la copia 2025 como prueba de vigencia. ATS: catálogo y esquema vigente aún requieren validación antes de fase 07; el PDF 2016 encontrado no es suficiente. No se declara homologación.

Contratos reales: Facturador expone POST /api/integrations/v1/invoices y GET /api/integrations/v1/invoices/:externalReference. Exige Idempotency-Key, correlación, identificación/nombre/dirección, items y pagos. El emisor deriva de la API key y la empresa; requiere certificado y punto de emisión habilitados. CUSTOM es un origen admitido; ODOO no lo es todavía. Elegir CUSTOM para el primer conector evita modificar el catálogo fuente sin necesidad.

SKNOMINA expone nómina paginada por período con importes/estado por empleado; no incluye mapa de cuentas ni un contrato de cierre contable. Es necesario ampliar el contrato antes de automatizar asientos. Facturación de las suscripciones propias de SKNOMINA usa una ruta de emisor proveedor distinta de la API genérica por cliente.

Brechas funcionales: guías, retenciones, notas, liquidaciones y ATS existen en el producto fiscal, pero no se acreditan en su router de API externa. No se incluirán como endpoints inventados. El estado HTTP de solicitud no acredita autorización SRI. No se tocaron repositorios fuente ni datos de clientes.

Licencia del nuevo código propio pendiente de titular: no publicar un módulo instalable con una licencia abierta supuesta. Las pruebas y automatizaciones internas son privadas en este repositorio. Bibliotecas: instalar en entorno aislado y registrar versiones/licencias antes de cerrar la fase.
