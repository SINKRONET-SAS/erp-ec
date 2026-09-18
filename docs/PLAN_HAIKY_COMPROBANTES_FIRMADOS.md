# Plan Haiky OP13 — Comprobantes electrónicos firmados: nota de crédito, nota de débito y guía de remisión

Fecha: 18-09-2026. Instrucción del titular: "Debe cumplirse la legislación de Ecuador, los documentos comerciales debe ser firmados" (además: no se visualizaban todos los documentos comerciales de una venta ni dónde configurar consecutivos).

## Hallazgos de la investigación
- Los **consecutivos** ya existen de forma nativa (`account.journal.l10n_ec_entity`/`l10n_ec_emission` del módulo `l10n_ec` de Odoo, y `l10n_latam_document_number`); el problema era de descubribilidad, no de funcionalidad.
- Nota de crédito, nota de débito y guía de remisión NO se firmaban ni transmitían: el motor nativo (OP09) solo cubría factura (codDoc 01).
- `xades.sign()` tenía la etiqueta raíz `factura` fija (hallazgo real durante las pruebas; una lectura previa lo había dado por agnóstico). Ahora acepta el catálogo `COMPROBANTE_TAGS`.

## Alcance y estado por documento
| Documento | codDoc | XSD oficial | Estado |
|---|---|---|---|
| Factura | 01 | factura_V2.1.0.xsd | Hecho (OP09) |
| Nota de crédito | 04 | NotaCredito_V1.1.0.xsd | **Hecho en OP13-A** |
| Nota de débito | 05 | NotaDebito_V1.0.0.xsd | **Hecho en OP13-B** |
| Comprobante de retención | 07 | ComprobanteRetencion_V2.0.0.xsd | **Hecho en OP13-C** |
| Guía de remisión | 06 | GuiaRemision_V1.1.0.xsd | **Hecho en OP13-E** (modelo propio enlazable a `stock.picking`) |

## OP13-A (ejecutado)
- `erpec_fiscal_native/notacredito_engine.py`: XML validado contra el XSD oficial; `engine.access_key()` gana parámetro `doc_type` (por defecto '01').
- `erpec_fiscal_sri`: `action_native_emit()` acepta `out_refund` (solo si nace de "Añadir nota de crédito" sobre una factura tipo 01); `_poll()` elige RIDE por `codDoc` de la clave; `ride.build_ride_notacredito()` (no verificado pixel a pixel contra un RIDE oficial).
- Sin bloque de pagos (el esquema de notaCredito no lo tiene).
- Pruebas: 6 de motor + 4 de emisión firmada; además se corrigieron dos fixtures previos de `test_native.py` (sin país EC y numeración por campo derivado) que fallaban en base aislada. 65/65 pruebas en `erpec_fiscal_native` + `erpec_fiscal_sri`.
- Ensayo real: factura y nota de crédito firmadas con el certificado real de pruebas y AUTORIZADAS por celcer.sri.gob.ec (ambiente PRUEBAS).

## OP13-B (ejecutado)
- `erpec_fiscal_native/notadebito_engine.py`: motivos (razón + valor) e impuestos agrupados, pagos opcionales, validado contra el XSD oficial (codDoc 05).
- `erpec_fiscal_sri`: una nota de débito es `out_invoice` con `debit_origin_id` (mecanismo nativo `account_debit_note`) y tipo documental 05; el RIDE se generaliza en un constructor compartido con la nota de crédito (`build_ride_notadebito`).
- Pruebas: 72/72 en `erpec_fiscal_native` + `erpec_fiscal_sri` (7 nuevas de OP13-B). Ensayo real: factura y nota de débito AUTORIZADAS por celcer.sri.gob.ec (PRUEBAS) con el certificado real de pruebas.

## OP13-C (ejecutado): retenciones a proveedores y ambiente por diario
- Verificación del lado de compras pedida por el titular: `erpec.withholding` era solo contable (sin XML, firma ni SRI; el concepto SRI era texto libre). Liquidación de compra (03) sigue sin emitirse.
- `retencion_engine.py` (v2.0.0) y nuevo módulo `erpec_fiscal_withholding_sri`: código SRI estructurado por concepto, sustento ATS, parte relacionada, forma de pago, número SRI, resolución de agente de retención, emisión firmada y RIDE. `erpec.fiscal.emission` deja de exigir factura (fuente genérica).
- Hallazgos reales del SRI (no detectables por XSD): `tipoSujetoRetenido` solo con identificación del exterior; cada código de concepto tiene tarifa oficial (312 = 2.00%). El catálogo completo de tarifas de renta NO está embebido (pendiente).
- Consecutivos separados por ambiente: el SRI numera pruebas y producción de forma independiente. `account.journal.ec_sri_ambiente` alimenta clave de acceso y XML; las retenciones usan una secuencia por empresa y ambiente. Producción sigue bloqueada.
- Pruebas: 83/83. Ensayo real: retención AUTORIZADA por celcer.sri.gob.ec (PRUEBAS).

## OP13-D (ejecutado): establecimientos, puntos de emisión y ambiente configurables por el cliente
- Pedido del titular: el cliente debe poder configurar pruebas/producción; el establecimiento (local o sucursal) y el punto de emisión (caja) no eran visibles. Existían solo como campos técnicos del diario (`l10n_ec_entity`/`l10n_ec_emission`).
- Nuevo modelo `erpec.fiscal.point` (menú Fiscal > Establecimientos y puntos de emisión): códigos de 3 dígitos, nombre, dirección del establecimiento (sale como `dirEstablecimiento`), ambiente vigente.
- Consecutivos independientes por ambiente: cada punto mantiene un diario de ventas por ambiente (FP### pruebas, FR### producción). Cambiar de ambiente activa/crea el diario del otro ambiente; nunca se reutiliza numeración. Se valida que el número del comprobante corresponda al establecimiento y punto del diario.
- Habilitar producción exige rol de responsable contable, certificado verificado y de entidad reconocida, y confirmación explícita; queda registrado quién y cuándo. El ambiente no se escribe directamente. El diario del ambiente equivocado no emite.
- `sri_client`: el endpoint de producción (cel.sri.gob.ec, WSDL alcanzable) queda disponible, pero SOLO se usa desde un punto habilitado. La transmisión real a producción NO se ha probado (solo pruebas); un primer envío real a producción debe hacerse con una factura de bajo riesgo y supervisión del responsable.
- Retenciones: usan el punto del diario de retenciones (establecimiento/punto/dirección) y una secuencia por empresa, punto y ambiente.
- Pruebas: 90/90. Ensayo real en la demo por RPC: punto creado con su diario de pruebas; producción rechazada sin certificado; escritura directa del ambiente rechazada.

## OP13-E (ejecutado): guía de remisión
- Nuevo módulo `erpec_fiscal_guide_sri`: `erpec.fiscal.guide` (destinatario, transportista, placa, fechas de traslado, bienes, sustento con la factura), botón "Guía de remisión SRI" en el traslado de inventario que precarga los bienes, `guiaremision_engine.py` (XSD 1.1.0), RIDE y emisión firmada reutilizando `erpec.fiscal.emission`.
- Numeración por punto de emisión y ambiente (secuencia propia). La guía debe emitirse antes de iniciar el traslado (validado). Una guía inmutable una vez firmada.
- Con esto los cinco comprobantes de venta/compra (factura, nota de crédito, nota de débito, retención, guía de remisión) se firman y transmiten. Faltan liquidación de compra (03) y comprobantes de reembolso.
- Pruebas: 100/100. Ensayo real: guía AUTORIZADA por celcer.sri.gob.ec (PRUEBAS) con el certificado real de pruebas.

## Pendiente explícito
- Asignar el punto de emisión a los diarios ya existentes (migración de diarios previos) y selección de punto por usuario/caja.
- Catálogo completo de conceptos y tarifas de retención de renta; liquidación de compra (03).
- OP13-C guía de remisión.
- Producción SRI sigue bloqueada (ver OP11-B3); RIDE de nota de crédito sin validación visual oficial.
- Vista de "documentos de la venta" unificada en la UI (descubribilidad) aún no construida.
