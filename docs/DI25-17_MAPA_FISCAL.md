# Mapa de dueños y consumidores fiscales — DI25-17

Fecha: 24-09-2026. Responde al hallazgo DI25-17 (solapamiento de adaptadores, menús y sustentos): no todo lo que parece duplicado lo es. Cada entidad tiene una autoridad y un propósito; se conservan las de semántica distinta y se documenta que no se identificó ninguna ruta obsoleta que retirar.

## Entidades con propósito distinto (se conservan)

| Tema | Entidad | Módulo dueño | Propósito | Consumidores |
|---|---|---|---|---|
| Retenciones de compra | `erpec.purchase.withholding` | `erpec_fiscal_documents` | Preparación y estimación por concepto (la puebla `erpec_workspace` desde el plan de impuestos) | `erpec_workspace` |
| | `erpec.withholding` y `.line` | `erpec_withholding_accounting` | Asiento contable y conciliación de la retención (emitida o recibida); inmutable al contabilizar | `erpec_fiscal_withholding_sri`, `erpec_fiscal_ats` (retención en compras y ventas) |
| | ampliación de `erpec.withholding` | `erpec_fiscal_withholding_sri` | Datos SRI (número, sustento, código por concepto) y emisión electrónica de la retención a proveedores | `retencion_engine`, `erpec_fiscal_ats` (referencia al comprobante) |
| Reembolsos | `erpec.reimbursement.support` | `erpec_fiscal_documents` / `erpec_withholding_accounting` | Sustentos del reembolso en compras, conciliados con la línea contable | validación previa a contabilizar |
| | `erpec.fiscal.reimbursement` | `erpec_fiscal_sri` | Sustentos del reembolso que van en el XML de la factura de venta | `engine` (bloque de reembolso) |
| Emisión | `erpec.fiscal.emission` | `erpec_fiscal_sri` | Única autoridad nativa: firma, cola, SRI, autorización, RIDE; compartida por facturas, notas, liquidaciones, retenciones y guías | `erpec_fiscal_ats` (ventas y anulados), vistas de bandeja |
| | `erpec.fiscal.job` | `erpec_fiscal_connector` | Autoridad alternativa: Facturador externo; excluyente con la emisión nativa por comprobante (se comprueba en ambos sentidos, DI25-02) | `erpec_fiscal_ats` |
| Previsualización | `erpec.fiscal.preview` | `erpec_fiscal_native` | XML sin firma para revisar; no es autoridad ni reserva secuencial | facturas |
| Anexos | `erpec.ats.report` | `erpec_fiscal_ats` | Ensayo local del ATS con faltantes y documento origen; no es presentación | matriz fiscal, DIMM (validación local) |

## Reglas comunes

`_gather_native_common` (`erpec_fiscal_native/models.py`) concentra la validación de líneas e identificación que comparten la vista previa y la emisión nativa (adaptador común, DI25-02). Los tipos de comprobante ATS se derivan del código del tipo documental de Odoo (`l10n_latam.document.type.code`), sin tabla paralela.

## Menús

Todo lo fiscal cuelga de una raíz (`Fiscal · Pruebas`, con "Configuración de impuestos" y "Retenciones contables" aparte por rol). Las entradas (Facturas — preparación local, Emisiones nativas, Establecimientos, Certificado, Matriz fiscal, Anexo ATS, Conexión externa de pruebas) se muestran solo a los grupos que pueden usarlas; en la comprobación por rol un usuario básico solo ve Inicio y un vendedor solo Ventas.

## Rutas obsoletas

No se identificó ninguna ruta o entidad obsoleta que retirar: la vista previa y la emisión coexisten a propósito, y las dos formas de retención y de reembolso tienen semántica distinta. Ningún método público se retiró en DI25-06 ni en DI25-07. Si en el futuro se retira una, requerirá inventario de consumidores y migración.
