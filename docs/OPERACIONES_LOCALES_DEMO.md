# Operaciones locales: importación, fabricación y nómina

La demo usa empleados y movimientos ficticios con parámetros laborales reales Ecuador 2026. No se generan pagos bancarios, planillas IESS ni declaraciones oficiales. La empresa conserva el RUC vacío.

## Recorridos disponibles

- **Importaciones comerciales**: abrir IMPORTACION-DEMO-001. Compra de 10 unidades a USD 10, primera recepción de 5 y flete capitalizable de USD 10. Costo unitario resultante USD 12, con valoración y asiento nativos. El expediente enlaza compra, recepción, comprobante del gasto, documentación y costo; permite preparar un ajuste inverso trazable. Los números de embarque y declaración son ejemplos sin validez aduanera.
- **Nómina local → Períodos y novedades**: agosto 2026 tiene un cierre y asiento publicados; septiembre permite revisar empleado, sueldo, horas y descuentos. Marcar las novedades como aprobadas, calcular, aprobar cierre y contabilizar. Para cambiar un cálculo sin cierre, usar Corregir novedades. Para un cierre publicado, revertir el asiento y crear la corrección; se conservan ambas versiones.
- **Nómina local → Versiones y autoridad**: abrir Ecuador 2026 · privado general v1 y revisar Parámetros aplicados, fuentes y cuentas. La versión activa no se sobrescribe.
- **Producción y trabajo / Fabricación**: continúan las órdenes anteriores. La pausa registra un intervalo separado y su motivo; reanudar cierra la pausa. El motor nativo incluye la ocupación del centro, incluidas pausas, en el costo horario; no se anuncia una exclusión contable de pausas.

## Parámetros reales cargados

Perfil: trabajador privado general continental, jornada mensual completa, sin cargas familiares, discapacidad ni exenciones especiales. No representa automáticamente regímenes públicos, parciales, sectoriales o Galápagos.

| Concepto | Valor 2026 | Fuente |
|---|---:|---|
| SBU | USD 482 | [Acuerdo MDT-2025-195](https://www.trabajo.gob.ec/wp-content/plugins/download-monitor/download.php?force=1&id=4933) |
| IESS personal / patronal | 9,45 % / 11,15 % | [IESS](https://www.iess.gob.ec/es/preguntas-frecuentes-afiliacion) |
| Reserva, cumplido el período de elegibilidad | 8,33 % | [IESS](https://www.iess.gob.ec/web/afiliado/fondos-de-reserva) |
| Contribución IECE/SECAP | 1 % patronal adicional | [Código Monetario, disposición general undécima](https://www.epam.gob.ec/wp-content/uploads/2016/03/CODIGO-ORGANICO-MONETARIO-Y-FINANCIERO.pdf) |
| Divisor salarial / recargos | 240; suplementaria 50 %, extraordinaria 100 %, nocturna 25 % | [Calculadora del Ministerio](https://calculadoras.trabajo.gob.ec/valor) |
| Décimos | 1/12 de remuneración; 1/12 del SBU | [Ministerio del Trabajo](https://www.trabajo.gob.ec/29-cual-es-el-plazo-y-como-se-debe-realizar-la-solicitud-para-la-acumulacion-del-pago-de-la-decima-tercera-y-decima-cuarta-remuneracion/) |
| Vacaciones ordinarias | Provisión 1/24 | [Código del Trabajo, art. 71](https://www.gob.ec/sites/default/files/regulations/2018-10/C%C3%B3digo-del-Trabajo.pdf) |
| Renta | Diez tramos 2026, fracción exenta USD 12.208 | [Tabla SRI](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/fa75d2ba-c784-4b33-af3a-8390f2f7af13/Tablas%20c%C3%A1lculo%20IR.pdf) |
| Gastos personales, cero cargas | Hasta USD 5.752,60; rebaja del 18 % | [SRI, boletín 006/2026](https://www.sri.gob.ec/detalle-noticias?idnoticia=1261&marquesina=1) |

Consulta de fuentes: 11-09-2026. El divisor 240 no significa 240 horas efectivamente trabajadas. Las horas nocturnas registran solo el recargo adicional de horas ya incluidas en el sueldo; no deben duplicarse como horas extraordinarias.

Ejemplo mensual de USD 1.200 sin gastos proyectados: IESS personal 113,40; renta 3,46; neto 1.083,14; IESS patronal 133,80; IECE/SECAP 12; décimo tercero acumulado 100; cuarto 40,17; vacaciones 50; reserva acumulada 99,96. Costo mensual de los conceptos incluidos: 1.635,93. Los ejemplos asumen solicitud de acumulación de beneficios y reserva, empleo continuo desde enero de 2025 y remuneración estable en la proyección anual.

## Evidencia y límites

Las pruebas en copia cubren fabricación parcial, desperdicio y desmontaje, faltantes, dependencias, tiempos, lotes/series, planificación sin solapar un centro de capacidad uno, compra-fabricación-venta con valoración automática; importación parcial, AVCO/FIFO, divisas, mercancía vendida, clasificación, duplicados y ajuste inverso; nómina, aprobación, asiento repetido, reversión, corrección, permisos y parámetros 2026.

El contraste de seis casos con funciones puras de SKNOMINA no acredita equivalencia integral. Existe una diferencia intencional: el motor local aplica la rebaja de gastos personales al impuesto y no como reducción de la base imponible. No se modificó SKNOMINA ni se desconectó una empresa existente.

Pendientes para cerrar todos los prompts: aceptación visual completa por operario/supervisor y expediente con dos productos; nómina con acumulados y retenciones previas, otras relaciones IESS, cargas/exenciones, novedades de bases independientes, ausencias, liquidaciones y pagos conciliados; contrato externo y migración productiva. Las tasas reales no sustituyen estas pruebas ni constituyen homologación laboral. Render permanece aplazado; PAYPHONE ya fue probado por túnel.

## Respaldo y reproducción

Scripts: verify-operational-plan.py crea/usa copia aislada; verify-operational-runtime.py verifica semillas, vistas y concurrencia; install-operational-demo.py exige las pruebas y sus hashes, respalda y actualiza solo erpec_demo; restore-operational-demo.py recupera el respaldo en otra base con rol y filestore propios, conservando la demo. Los resultados privados se guardan en .cache/windows; la evidencia pública del repositorio excluye contraseñas.

## Incremento de aceptación — 11-09-2026

Diecinueve pruebas transaccionales pasan en copia aislada. El nuevo caso de fabricación usa usuarios operario y supervisor, dos operaciones dependientes, pausa/reanudación y producción parcial seguida de la orden pendiente; comprueba existencias y que el operario no lea asientos contables. El nuevo caso de importación concilia una factura de EUR 20 valorada inicialmente en USD 40 mediante pagos de ensayo de USD 20 y USD 30: saldo final cero, pérdida cambiaria USD 10 y costo capitalizado conservado en USD 40. Los tipos de cambio son datos controlados de prueba, no una cotización real ni parámetros de la demo. No hay conexión bancaria.

La política artificial de regresión usa un año reservado para coexistir con la versión real 2026; la demo conserva sus parámetros reales. La comprobación cambiaria incluye asientos de conciliaciones parciales, donde Odoo registra esta diferencia. Evidencia: evidencias/ERPEC26-OPERACIONES-ACEPTACION.json. Este incremento modifica pruebas y contexto, sin nueva instalación o restauración de la demo.
