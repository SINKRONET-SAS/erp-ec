# ERPEC26-OP13 — Comprobantes electrónicos firmados (nota de crédito, nota de débito, guía de remisión)

Objetivo: cumplir la legislación ecuatoriana firmando (XAdES-BES) y transmitiendo al SRI todos los comprobantes de una venta, no solo la factura.
Fuente de verdad: XSD oficiales del SRI en addons/erpec_fiscal_native/xsd/. Sin pruebas reales no se declara cumplimiento.
Plan: docs/PLAN_HAIKY_COMPROBANTES_FIRMADOS.md. Incrementos: A nota de crédito (hecho), B nota de débito, C guía de remisión.
Reglas: aislar pruebas en base nueva, respaldo antes de instalar en demo, ensayo real contra celcer.sri.gob.ec solo con certificado de pruebas del titular, stage solo archivos propios.
