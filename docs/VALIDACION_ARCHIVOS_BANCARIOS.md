# Validación de archivos bancarios de nómina y proveedores — Ecuador
Consulta: 11-09-2026. Alcance: siete entidades solicitadas. Revisión de fuentes públicas y perfiles de referencia; no hubo carga en bancos ni transferencias.

## Resultado
Los perfiles estáticos de referencia de SKNOMINA no deben copiarse como formatos bancarios aprobados. El ERP tiene pagos contables y conciliación exacta; aún no tiene un generador bancario homologado. La existencia de un archivo exportable, un ensayo unitario o una orden cargada no acredita aceptación ni pago.

| Entidad y servicio | Evidencia oficial y resultado | Acción necesaria |
|---|---|---|
| Pichincha — carga de pagos Cash Management | [Formato publicado](https://www.pichincha.com/sites/default/files/images/Doc%2B10-footer-cash-pymes-instructivos-10-formato-carga-de-ordenes-de-pago-masiva_10.pdf): 12 columnas, tabuladores, sin encabezado, monto en centavos sin separador decimal. No coincide con el perfil de referencia de diez columnas, punto y coma, encabezado y totalizador. | Implementar un perfil específico de ese formato y contrastarlo con la plantilla del canal contratado. El [manual de 2025](https://www.pichincha.com/sites/default/files/images/instructivo-pagos-masivos-pichincha-empresas-02-25_11.pdf) muestra descarga de plantilla en Banca Empresas; no asumir equivalencia entre versiones. |
| Guayaquil — Banca Empresas / nómina | El [centro de ayuda oficial](https://www.bancoguayaquil.com/documents/files/centro-de-ayuda-nueva-banca-empresas.pdf) enlaza una guía específica de nómina; el enlace diseno_archivos_pago_nomina.pdf devuelve HTTP 404 al consultar. El [flujo actual](https://ayudaempresas.bancoguayaquil.com/hc/es/articles/42468275188372--C%C3%B3mo-hacer-transferencias-de-N%C3%B3mina) confirma carga y cuenta de débito, pero no define posiciones del archivo. | Obtener plantilla o ficha vigente del banco. No validar el CSV genérico de referencia por analogía con otros bancos ni con copias de terceros. |
| Produbanco — Pagos Full | [Ficha versión 1.1, 07-04-2022](https://www.produbanco.com.ec/media/712207/formato-entrada-pagos_full.pdf): veinte campos tabulados; cuenta de empresa de once dígitos, ceros a la izquierda para cuentas propias; importe numérico en centavos, trece posiciones; código local de institución de cuatro dígitos. | Sustituir el perfil genérico por el formato documentado; completar empresa/servicio y confirmar plantilla vigente con el canal contratado. |
| Pacífico — Cash Management | [Servicio oficial](https://www.bancodelpacifico.com/empresas/cash-management) y [manual de cobros y pagos](https://www.bancodelpacifico.com/BancoPacifico/media/pdf/CashManagement/MANUAL-DE-USUARIO-ORDEN-DE-COBROS-Y-PAGOS-2015.pdf). No se obtuvo de estas fuentes una especificación vigente de columnas que pruebe el perfil pacifico_interbank_immediate de SKNOMINA. | Obtener ficha exacta de roles o transferencias interbancarias del servicio contratado. No confundir formato de extracto/conciliación con archivo de instrucciones de pago. |
| General Rumiñahui — CM Full Pagos | [Ficha oficial de 19-03-2015](https://www.bgr.com.ec/resources/pdf/cash-management/cmfull-pagos-bgr-carga.pdf): veinte campos tabulados, cuenta de empresa de hasta veinte posiciones, importe de trece posiciones y referencia requerida. La ficha indica código 0042 para su campo bancario. | Perfil propio ausente en el archivo estático de referencia. Confirmar alcance de pagos interbancarios y formato vigente; no extrapolar códigos de otros servicios. |
| Internacional — Banca Online Empresas | [Cargas por archivo](https://www.bancointernacional.com.ec/wp-content/uploads/2020/11/BI-NBOE-TutorialPDF-9CargasporArchivo.pdf) documenta el recorrido. El manual de Pago Electrónico de Nómina incluye datos de enrolamiento; no basta para deducir el formato de abono salarial. | Obtener plantilla técnica de Pago Nómina del servicio contratado, separada del enrolamiento. Perfil estático ausente en la referencia revisada. |
| Bolivariano — SAT Pagos / Banca Empresas | [SAT Pagos](https://www.bolivariano.com/empresas/sat/sat-pagos) y [tutoriales](https://www.bolivariano.com/empresas/sat/tutoriales-bde) acreditan el servicio, no se obtuvo allí la ficha de posiciones de nómina. | Obtener ficha o macro oficial de carga. Perfil estático ausente en la referencia revisada. |

## Controles que debe pasar cada perfil antes de habilitarlo
1. Identificar banco, servicio, canal, versión, fuente y fecha de vigencia. Conservar una plantilla de referencia y su hash; una edición del perfil debe producir otra versión.
2. Verificar cantidad y orden de campos, posiciones o separadores, espacios vacíos, ceros iniciales, encabezado/totalizador, codificación, saltos de línea y nombre del archivo. No truncar nombres ni cuentas silenciosamente.
3. Tratar cuentas, identificaciones y códigos como texto. Validar tipo de cuenta, longitud por entidad receptora, identificación y código bancario del formato concreto. No reutilizar códigos de otro catálogo.
4. Obtener importes del saldo elegible por empleado o proveedor; excluir cuentas liquidadas, versiones revertidas y registros sin datos. Rechazar duplicados, importes negativos/cero, caracteres de control y separadores dentro de campos.
5. Calcular cantidades e importes con decimales exactos. Contrastar total de obligaciones seleccionadas, suma de registros y totalizador cuando el banco lo exija. Probar pagos parciales sin volver a exportar el neto original completo.
6. Congelar el lote y su archivo, registrar usuario, empresa, fecha, versión y SHA256. Repetir descarga devuelve el mismo archivo; una corrección crea un lote trazable y no modifica el previamente entregado.
7. Separar preparación, autorización interna, exportación, resultado del banco, asiento y conciliación. Generar o descargar un archivo no liquida obligaciones de empleados ni proveedores.
8. Probar archivo aceptado y rechazos reales del validador de cada banco sin ejecutar transferencias; registrar respuesta íntegra. La aceptación del formato no acredita saldo, titularidad o ejecución.

## Hallazgos de la referencia local
Se revisó backend/src/config/bank-file-profiles.json y el generador de SKNOMINA en modo lectura. Contiene Pichincha, Guayaquil, Produbanco y Pacífico; faltan los otros tres bancos solicitados. Pichincha y Produbanco muestran incompatibilidades con las fichas anteriores. Pacífico declara un formato distinto pero no aporta en ese JSON su fuente técnica y versión.

El generador consultado incluye nóminas cerradas o pagadas y toma el neto completo; el traslado al ERP debe basarse en saldos y lotes para evitar reexportar pagos parciales o liquidados. Esta observación corresponde al código inspeccionado, no a una prueba de una operación real de SKNOMINA. No se modificó ese repositorio.

## Pendientes externos precisos
Plantillas vigentes de los siete servicios contratados y aceptación en sus validadores. Para Guayaquil, Pacífico, Internacional y Bolivariano falta además una estructura técnica completa recuperable de fuente oficial. No hay evidencia para declarar esos formatos aprobados.

## Extensión autorizada: pagos a proveedores

El usuario confirmó el 11-09-2026 que estos requisitos también deben cubrir proveedores. La arquitectura debe compartir perfiles, validación, lotes y trazabilidad en Tesorería; cada banco/servicio conserva su formato específico de nómina o proveedores. No duplicar un generador por módulo ni asumir que una plantilla de nómina sirve para proveedores.

El origen contable para proveedores es la cuenta por pagar nativa y su saldo pendiente. Incluir facturas parciales, agrupación por beneficiario/cuenta/moneda cuando el servicio lo admita, anticipos y aplicación de notas de crédito. Nunca mezclar empresas, sumar dos veces una factura o exportar nuevamente el importe original de una obligación parcialmente pagada. La asignación de una cuenta bancaria receptora requiere titular y tipo explícitos.

La exportación no crea ni concilia un pago. El resultado bancario debe permitir distinguir aceptados, rechazados, pendientes y pagos parciales; el registro contable y el cotejo del extracto conservan las referencias originales. Los fondos no se transmiten desde el ERP durante las pruebas de formato. El ensayo actual de tesorería cubre cotejo exacto de entradas/salidas, pagos de nómina y proveedor con crédito, anticipo y pagos parciales; todavía no acredita lotes bancarios de proveedores.


## Matriz de aceptación común y diferencias por origen

| Caso | Nómina | Proveedores | Resultado exigido |
|---|---|---|---|
| Importe elegible | Saldo de la preparación por empleado vigente | Saldo de facturas publicadas después de aplicar créditos y anticipos | No usar nuevamente el total original |
| Beneficiario | Empleado y tercero contable enlazado | Proveedor y tercero contable de la obligación | Cuenta receptora explícita; rechazar discrepancias |
| Servicio bancario | Dispersión de nómina contratada | Pago a proveedores contratado | Perfil y catálogo propios por servicio, aun dentro del mismo banco |
| Duplicados | Misma obligación en otro lote activo | Misma factura o vencimiento en otro lote activo | Bloquear reservas simultáneas y sobreasignaciones |
| Agrupación | Solo si la referencia por empleado se conserva | Solo por empresa, beneficiario, cuenta, moneda y servicio compatibles | Conservar distribución exacta por documento |
| Anticipo | No inferirlo del neto salarial | Orden de anticipo autorizada, separada de la factura | No presentar un anticipo como deuda facturada |
| Rechazo parcial | Mantener pendiente el abono rechazado | Mantener pendientes las asignaciones rechazadas | No liquidar todo el lote por una aceptación parcial |
| Corrección | Nueva versión de obligación/lote | Nueva versión de lote y distribución | Conservar archivo y resultado anteriores |
| Conciliación | Pago individual y movimiento de extracto | Pago individual y movimiento de extracto | No confundir archivo generado, aceptado y fondos debitados |

Los siete bancos quedan incluidos para ambos orígenes. La evidencia técnica de nómina del cuadro anterior no homologa automáticamente proveedores. La ficha de cada servicio debe confirmar su estructura, catálogo, límites y reglas de resultado; un servicio sin evidencia suficiente permanece inhabilitado.
