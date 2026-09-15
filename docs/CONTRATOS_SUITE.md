# Contratos de la suite

El catálogo versiona productos ERP, SKNOMINA y Facturador por separado del acceso API. Las cuotas de conexiones, solicitudes, usuarios y empresas son explícitas. No se inventan tarifas; las condiciones remiten al acuerdo comercial.

La autoridad de cobro se registra obligatoriamente por contrato: conservar el contrato/cobrador existente, o alta comercial administrada sin cargo automático. Deben constar responsable, referencia del contrato y autorización. El módulo no cobra, no emite facturas ni toma el retorno de un navegador como confirmación de pago. Elegir un cobro central automático sigue pendiente de acuerdo comercial y de una integración verificable.

Un plan con contratos queda congelado. Crear una nueva versión conserva las condiciones anteriores. Para una migración: revisar condiciones y cobrador, crear el contrato sustituto con su evidencia, suspender el anterior y autorizar el nuevo. El sistema rechaza vigencias superpuestas; no cancela ni duplica contratos en SKNOMINA o Facturador. Si falla la sustitución, reactivar el anterior después de suspender el nuevo. No borrar contratos.

Los derechos efectivos se calculan por fecha, autorización y suspensión. El catálogo es un control comercial local; aplicar las cuotas al aprovisionamiento y a los productos externos corresponde a las fases 04–06. No se ofrece SSO: el acceso actual utiliza usuarios Odoo y sus compañías autorizadas.

La vinculación exige identificadores externos explícitos y evidencia de autorización del administrador. Permanece pendiente de conexión; no se infiere identidad por correo o RUC. No se almacenan secretos en estos campos.

Pantallas: ERP EC → Planes y versiones, Contratos y derechos, Vínculos de productos. Administradores gestionan; reglas de compañía restringen lectura y operaciones de los registros. El control comercial definitivo debe residir en la instancia del operador, sin permisos administrativos para los clientes.

**Actualización 14-09-2026 (autoservicio):** desde `erpec_selfservice`, un visitante público SÍ puede iniciar un alta (elegir plan publicado, completar sus datos, pagar) desde `erpec_fundador` — la instancia operadora real, no un piloto de prueba. Esto no contradice el principio anterior: el visitante nunca obtiene sesión ni permisos Odoo; todas las escrituras privilegiadas (crear el contrato, el pago, activarlo, encolar el aprovisionamiento) las ejecuta el controlador bajo el usuario administrador (sudo), exactamente igual que ya hacía `/payment/payphone/return`. Los planes solo se exponen si un administrador los marca `published=True` explícitamente; ningún plan existente se publica por accidente. Ver docs/ALCANCE_AUTOSERVICIO.md para el detalle completo.
