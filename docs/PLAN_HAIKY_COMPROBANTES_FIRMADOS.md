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
| Guía de remisión | 06 | GuiaRemision_V1.1.0.xsd (descargado) | Pendiente OP13-C (modelo nuevo sobre `stock.picking`, no `account.move`) |

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

## Pendiente explícito
- OP13-C guía de remisión.
- Producción SRI sigue bloqueada (ver OP11-B3); RIDE de nota de crédito sin validación visual oficial.
- Vista de "documentos de la venta" unificada en la UI (descubribilidad) aún no construida.
