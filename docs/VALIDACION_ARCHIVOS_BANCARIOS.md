# Validación de archivos bancarios de nómina y proveedores — Ecuador
Consulta: 11-09-2026; ampliada el 24-09-2026 tras instrucción expresa del titular ("homologación bancaria" señalada como pendiente con falsos positivos: dos de los siete bancos sí tenían ficha técnica pública completa y no estaba implementada). Alcance: siete entidades solicitadas. Revisión de fuentes públicas oficiales; no hubo carga en bancos ni transferencias reales.

## Resultado (actualizado 24-09-2026)
Los perfiles estáticos de referencia de SKNOMINA (`nuevo_nomina/backend/src/config/bank-file-profiles.json`) se confirmaron como una plantilla genérica de 10 campos idéntica para Pichincha/Guayaquil/Produbanco (solo cambia `bankCode`), tomada como referencia arquitectónica del generador (`bancoAebGenerator.js`: perfil + lote + validación + hash) pero **no** como fuente de los campos reales de ningún banco — se descartó explícitamente.

**Implementado y probado** (`addons/erpec_treasury/bank_export.py`, DI25-07): generador de archivo de pago de **nómina**, homologado con ficha técnica oficial verificada de fuente primaria (PDF/HTML oficial descargado, SHA-256 en `docs/evidencias/DI25/bancario/manifiesto-fichas-bancarias.json`), solo para beneficiarios del mismo banco del perfil:

| Banco | Estado | Ficha técnica oficial |
|---|---|---|
| Banco Pichincha | **Implementado** (12 campos, tabulador, sin encabezado) | [Formato de carga para pagos](https://www.pichincha.com/sites/default/files/images/Doc%2B10-footer-cash-pymes-instructivos-10-formato-carga-de-ordenes-de-pago-masiva_10.pdf) |
| Produbanco | **Implementado** (20 campos, tabulador; verificado campo a campo contra el ejemplo numérico oficial) | [Formato de Entrada Pagos_Full v1.1, 07-04-2022](https://www.produbanco.com.ec/media/712207/formato-entrada-pagos_full.pdf) |
| Banco General Rumiñahui | **Implementado** (20 campos, tabulador, sin relleno de ceros; solo admite cuentas del propio BGR según su ficha) | [Formato CM Full Pagos, 19-03-2015](https://www.bgr.com.ec/resources/pdf/cash-management/cmfull-pagos-bgr-carga.pdf) |
| Banco Guayaquil | **Perfil identificado, bloqueado**: 20 campos localizados en el [centro de ayuda oficial](https://ayudaempresas.bancoguayaquil.com/hc/es/articles/11032985670804--Cu%C3%A1l-es-el-formato-para-cargar-una-orden-de-Cash-Management-para-pago-a-terceros-en-mi-Banca-Empresas), casi idénticos a Produbanco/Rumiñahui, pero esa fuente no declara el delimitador del archivo | Confirmar el delimitador directamente con el banco antes de habilitar el perfil |
| Pacífico | Sin ficha técnica pública de columnas | [Servicio oficial](https://www.bancodelpacifico.com/empresas/cash-management) y [manual de cobros y pagos](https://www.bancodelpacifico.com/BancoPacifico/media/pdf/CashManagement/MANUAL-DE-USUARIO-ORDEN-DE-COBROS-Y-PAGOS-2015.pdf): no aportan especificación de columnas |
| Internacional | Sin ficha técnica pública de columnas | El [tutorial de cargas por archivo](https://www.bancointernacional.com.ec/storage/2020/11/BI-NBOE-TutorialPDF-11PagoTercerosNominaProvBananeros.pdf) muestra las pantallas de "Carga de Órdenes" (Manual/Archivo) pero no el layout del archivo subido |
| Bolivariano | Sin archivo plano: SAT Pagos es una plataforma de captura manual/beneficiarios matriculados, sin carga masiva por archivo documentada en su manual técnico | [Manual SAT Pagos](https://portalbb-multimedia.bolivariano.com/docs/default-source/sat/manual-sat-pagos_01082022_hsat-man-008.pdf) |

Generar el archivo **no** ejecuta ningún pago ni lo marca como pagado: la preparación (`erpec.payroll.disbursement`), el pago contable, el resultado del banco y la conciliación del extracto siguen siendo pasos separados. El alcance de este incremento es solo **nómina**; proveedores queda como siguiente paso (ver "Extensión autorizada" más abajo, sin implementar todavía).

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
Aceptación real en el validador de cada banco (Pichincha, Produbanco, Rumiñahui) con una carga real del canal contratado; hoy solo está verificado que el generador reproduce exactamente el formato documentado, incluido el ejemplo numérico oficial de Produbanco. Confirmar el delimitador de Guayaquil directamente con el banco. Para Pacífico, Internacional y Bolivariano sigue faltando una estructura técnica completa recuperable de fuente oficial; no hay evidencia para declarar esos formatos aprobados ni para implementar un generador sin fabricar campos.

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
