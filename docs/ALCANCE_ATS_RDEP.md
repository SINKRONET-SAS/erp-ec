# Alcance — Anexo Transaccional Simplificado (ATS) y Anexo de Relación de Dependencia (RDEP)

Investigación del 13-09-2026, solicitada para documentar qué falta antes de programar la generación de ambos anexos SRI. No se ha escrito código de generación; este documento solo fija alcance y brechas, referenciando además lo ya construido en SKNOMINA y Facturador como antecedente, no como fuente normativa.

## Qué son y quién los presenta

**ATS**: anexo mensual que reporta compras, ventas, exportaciones, anulados, retenciones y comprobantes complementarios del período. Se ampara en la Resolución NAC-DGERCGC16-00000278 (citada en la ficha del trámite oficial). **RDEP**: anexo anual de las retenciones de impuesto a la renta practicadas a empleados bajo relación de dependencia; lo presenta todo empleador (persona natural o jurídica) que haya retenido renta a su personal, en enero del año siguiente al ejercicio fiscal, según el noveno dígito del RUC.

Estas dos reglas de periodicidad/plazo provienen de fuentes secundarias (despachos contables, no la ficha técnica oficial en sí) y deben confirmarse contra la ficha técnica y la resolución vigente antes de comprometer un calendario de generación. No se declaran homologadas.

## Fuentes oficiales verificadas hoy

| Documento | Fecha/versión observada | Fuente |
|---|---|---|
| Ficha Técnica ATS | 07-02-2025, 2.92 MB | sri.gob.ec, portal Alfresco (biblioteca de anexos) |
| Catálogo ATS (códigos de sustento, tipo de comprobante, etc.) | 03-03-2026, 3.58 MB | sri.gob.ec, biblioteca de anexos — **no descargado ni parseado en esta investigación** |
| Programa ATS de escritorio | v1.14.0, 31-10-2025 | sri.gob.ec |
| Esquema XML ATS (`ats.xsd`) | descargado y leído hoy | https://descargas.sri.gob.ec/download/anexos/ats/ats.xsd |
| Ficha Técnica RDEP | "RDEP 2024", vigente para ejercicio fiscal 2025, 701 KB | sri.gob.ec, biblioteca de anexos — **no descargada ni parseada en esta investigación** |
| Esquema XML RDEP (`Esquema RDEP 2023.xsd`) | actualizado 14-12-2023, descargado y leído hoy | https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/62837cc4-2de7-472c-9108-9b61bce8a38e/Esquema%20RDEP%202023.xsd |
| Trámite oficial ATS | última actualización listada 10-03-2022 | https://www.gob.ec/sri/tramites/anexo-transaccional-simplificado-ats |
| Trámite oficial RDEP | última actualización listada 10-03-2022 | https://www.gob.ec/sri/tramites/anexo-retenciones-fuente-relacion-dependencia-rdep |

Los dos esquemas XSD se leyeron directamente hoy (contenido crudo, no resumen de terceros); las fichas técnicas en PDF son imágenes escaneadas (93 páginas la del ATS) y no se pudieron extraer localmente: este entorno Windows no tiene `poppler`/OCR instalado, y la extracción remota devolvió solo metadatos del PDF, no texto. Antes de programar el mapeo campo a campo hay que conseguir una copia navegable de ambas fichas y del catálogo ATS, o instalar herramienta de OCR.

Los trámites oficiales en gob.ec no detallan periodicidad, canal de envío estructurado ni versión de esquema vigente con precisión — solo confirman que la presentación usa el software de escritorio **DIMM Formularios** más el plugin/anexo **APS** (ATS) o **RDEP**, con envío en línea vía sri.gob.ec o por FTP con convenio de responsabilidad. Es decir: **no hay indicio de una API REST de envío**; el canal de entrega real necesita confirmarse antes de diseñar cualquier integración, incluida la posibilidad de que el envío final deba hacerse fuera del ERP con estas herramientas oficiales.

## Estructura confirmada por el esquema (no exhaustiva de reglas de negocio, solo de forma)

### ATS (`ats.xsd`)
Elemento raíz `ivaType` con cabecera (`TipoIDInformante`, `IdInformante`, `razonSocial`, `Anio`, `Mes`, `codigoOperativo`) y bloques opcionales independientes: `compras`, `ventas`, `ventasEstablecimiento`, `exportaciones`, `recap` (consumos con tarjeta), `fideicomisos`, `anulados`, `rendFinancieros`. Cada detalle de compra (`detalleComprasType`) lleva identificación del proveedor, tipo/secuencial/autorización del comprobante, bases imponibles (gravada/no gravada/exenta), ICE, IVA, retenciones de IVA y renta desglosadas por tarifa, referencias a comprobantes de retención propios (hasta dos), datos de documento modificado (notas de crédito/débito) y un bloque `reembolsos` repetible. El detalle de venta es más compacto: identificación del cliente, tipo de comprobante, bases, IVA, compensaciones, retención de IVA/renta recibida y forma de pago.

### RDEP (`Esquema RDEP 2023.xsd`)
Elemento raíz `rdep` con `numRuc`, `anio`, `tipoEmpleador` (PRIVADO_MIXTO/PUBLICO), `enteSegSocial` (IESS/ISSFA_ISSPOL) y una lista de `datRetRelDep`. Cada registro trae datos del empleado (`datEmpTyp`: tipo/número de identificación, nombre, establecimiento, residencia fiscal, discapacidad, beneficiario de gasto por discapacidad, cargas para rebaja de gastos personales) y el detalle económico anual (`datRetRelDepTyp`): sueldos/sobresueldos, participación de utilidades, décimo tercero, décimo cuarto, fondo de reserva, aportes IESS personal, deducciones desglosadas (vivienda, salud, educación, alimentación, vestimenta, arte/cultura, turismo — estas tres últimas con tope específico), exoneraciones por discapacidad/tercera edad, base imponible, impuesto causado, rebaja por gastos personales, e impuesto retenido.

## Correspondencia con lo ya nativo en el ERP

| Bloque del anexo | Dato ya disponible en el ERP | Módulo/campo | Brecha |
|---|---|---|---|
| RDEP: sueldo, décimo tercero, décimo cuarto, fondo de reserva, IESS personal, impuesto a la renta causado/retenido | Sí, calculado por período | `erpec_payroll` (`erpec.payroll.period` / motor en `engine.py`, conceptos `CONCEPTS` en `models.py`: `gross`, `personal_iess`, `tax`, `thirteenth`, `fourteenth`, `reserve_iess`) | Falta acumular por **año fiscal** (el motor cierra por período/mes, RDEP es anual); falta exponer el desglose exacto exigido por el esquema, no solo los agregados actuales |
| RDEP: deducciones desglosadas (vivienda/salud/educación/alimentación/vestimenta/arte/turismo) | No — solo existe `personal_expenses` como monto único | `erpec_payroll` línea 259 | Falta modelar la categoría de cada gasto personal; el esquema exige el desglose, no el total |
| RDEP: discapacidad, cargas familiares para rebaja, residencia fiscal del empleado | No | — | Campos nuevos requeridos en el modelo de empleado o de línea de nómina |
| RDEP: `tipoEmpleador` / `enteSegSocial` de la empresa | No | — | Campo nuevo a nivel de `res.company` |
| ATS: retenciones de compra/venta por comprobante, tarifa, cuentas tributarias | Sí, parcialmente | `erpec_withholding_accounting` (`erpec.withholding` / `erpec.withholding.line`: `kind` renta/IVA, `rate`, cuenta tributaria, vínculo a `account.move`) | El modelo ya distingue emitida/recibida y tasa verificada, pero no captura establecimiento/punto de emisión/secuencial/autorización del comprobante de retención en el formato de 3-3-9 dígitos que exige el XSD, ni el detalle de comprobante modificado |
| ATS: identificación de proveedor/cliente (tipo + número) | Sí | `l10n_latam_identification_type_id` nativo de `l10n_ec`/`l10n_latam_base` en `res.partner` | Falta mapear el catálogo propio de Odoo a los códigos `tpIdProv`/`tpIdCliente` del ATS (no confirmado si coinciden 1:1) |
| ATS: preparación XML de comprobantes de venta propios | Sí, parcial | `erpec_fiscal_native` (`Move.action_native_preview`, `engine.py`) — solo factura de venta, ambiente pruebas, sin firma ni envío SRI | Es la base más cercana para reutilizar generación XML local, pero cubre un solo tipo de comprobante y no produce el anexo agregado |
| ATS: compras al exterior / reembolsos de importación | Parcial | `erpec_imports` (expedientes de importación, cargos) | No hay mapeo hoy a los campos `pagoExterior`, `reembolsos` ni al catálogo de países/paraísos fiscales del XSD |
| ATS: catálogo de `codSustento`, `tipoComprobante`, `codRetAir` y similares | No | — | Requiere el Catálogo ATS oficial (03-03-2026), aún no descargado; no se deben inventar códigos |

## Brechas que bloquean empezar a programar

1. **Catálogos oficiales sin parsear**: el Catálogo ATS (códigos de sustento tributario, tipo de comprobante, tipo de retención AIR) y ambas fichas técnicas en PDF no se han leído; sin ellos no hay forma de mapear datos del ERP a los códigos exigidos sin inventar valores, algo que este proyecto excluye explícitamente (ver `docs/MATRIZ_CAPACIDADES.md` y `docs/evidencias/ERPEC26-01.md`).
2. **Canal de envío no confirmado**: los trámites oficiales apuntan a software de escritorio (DIMM Formularios + plugin APS/RDEP) y envío por FTP o portal, no a una API. Decidir si el ERP solo genera el XML válido contra el XSD (dejando el envío fuera del sistema) o si además debe automatizar la entrega requiere confirmar esa brecha primero.
3. **RDEP requiere datos que hoy no existen**: discapacidad/cargas familiares del empleado, desglose de gastos personales por categoría, y clasificación patronal/seguridad social de la empresa. `erpec_payroll` calcula los montos agregados pero no en la forma exigida por el esquema.
4. **RDEP es anual, el motor de nómina cierra por período**: falta decidir cómo se consolidan los períodos de un año fiscal en un solo anexo (¿nuevo modelo `erpec.payroll.annual.report` o cálculo derivado de los períodos existentes?).
5. **ATS agrega comprobantes de todos los flujos** (ventas, compras, importaciones, retenciones, anulados) que hoy viven en módulos separados (`erpec_fiscal_native`, `erpec_withholding_accounting`, `erpec_imports`, `purchase`, `sale` nativos): falta un modelo agregador por período/empresa, y falta decidir el mismo punto que en Facturador — "guías, retenciones, notas, liquidaciones y ATS existen en el producto fiscal [Facturador], pero no se acreditan en su router de API externa" (`docs/evidencias/ERPEC26-01.md`), por lo que **no se puede depender de la API de Facturador para el ATS**; la generación tendría que ser nativa del ERP o requerir ampliar ese contrato primero.
6. **Vigencia normativa**: igual que se señaló en fase 01 para el ATS ("catálogo y esquema vigente aún requieren validación... no se declara homologación"), este documento tampoco homologa nada: confirma que existe una versión de esquema fechada y descargable hoy, no que sea la única aplicable al período fiscal que se vaya a declarar.

## Próximos pasos sugeridos (sin ejecutar)

1. Descargar y hacer legible (OCR o copia de texto) la Ficha Técnica ATS 07-02-2025, la Ficha Técnica RDEP 2024 y el Catálogo ATS 03-03-2026 completos.
2. Confirmar contra esas fichas la periodicidad, plazos por noveno dígito de RUC y el canal de envío real (¿hay API además del software de escritorio?).
3. Diseñar el modelo de datos que falta en `erpec_payroll` (discapacidad, cargas, desglose de gastos personales, tipo de empleador) y en `res.company` (tipo de empleador, ente de seguridad social).
4. Decidir el agregador ATS por período/empresa y su relación con `erpec_fiscal_native`, `erpec_withholding_accounting` e `erpec_imports`.
5. Validar el XML generado contra `ats.xsd` y `Esquema RDEP 2023.xsd` como parte de las pruebas automatizadas, igual que ya se hace con `factura_V2.1.0.xsd` en `erpec_fiscal_native`.

Este documento no autoriza a iniciar la implementación; queda pendiente decisión del usuario sobre orden y alcance de la fase que cubra ATS/RDEP.
