# SP02 — Configuración tributaria por casos
Autorizado: continuar SP02 y corregir la cadena de configuración indicada por el titular. Sustituye el enfoque funcional del incremento TX00–TX02, cuya evidencia histórica se conserva.

Catálogo SRI → detalle nativo account.tax ↔ cuentas contables de factura/devolución → plan → casos que agrupan detalles → asignación exacta por operación, tipo de tercero y tipo de producto.

| Fase | Dependencia | Resultado exigido |
|---|---|---|
| TX03 | Gobierno previo válido | Diagnóstico y este plan/prompt. Solo documentación. |
| TX04 | TX03 firmado | Catálogos referenciados, detalles/cuentas nativos, planes/casos, tipos y asignaciones por empresa; consulta de resolución visible; pruebas de integridad y permisos. |
| TX05 | TX04 probado | Instalación con respaldo, revisión de pantallas, evidencia, gobierno y publicación. |

Los tipos son configurables por el responsable contable: no inferir régimen por nombre, RUC o producto. El catálogo guarda código, fuente y versión como referencia; no importa tasas ni interpreta normativa. Las tasas y reparticiones permanecen en account.tax. No confundir catálogo ATS con catálogo de impuestos ni cuentas predeterminadas con cuentas de repartición.

El alcance de este incremento es configurar y comprobar la selección del caso y sus impuestos. La consulta compara el caso con la configuración operativa nativa; no cambia pedidos, facturas ni asientos. La aplicación automática a documentos y retenciones específicas requiere una fase posterior con pruebas de propagación y conservación de ajustes manuales. Mostrar esta frontera en pantalla; SP02 no se cierra por este incremento.

Compatibilidad: conservar erpec.tax.plan como consulta y sus métodos públicos. Crear erpec.tax.policy como plan real con casos y asignaciones. No reclasificar registros existentes. Reversión: recuperar respaldo previo mediante scripts/restore-operational-demo.py; conservar demo y copia aislada.

## Resultado del incremento
TX03 documental; TX04 pasó 38 pruebas finales; TX05 instalado con respaldo y revisión visual. Evidencia: evidencias/ERPEC26-TX05-CIERRE.json. El cierre corresponde a configuración y consulta; la aplicación automática y SP02 integral siguen pendientes. No se declara recuperación del respaldo nuevo.

## TX06 — Detalles de retenciones

Un plan consume varios casos; cada caso consume varios detalles de impuestos, retenciones de Renta y retenciones de IVA. Catálogo ATS desde 06/08/2026 para Renta y ficha 2.34 tabla 20 para IVA. Conservar tarifas condicionadas como texto, sin actualizar masivamente detalles operativos. Prompt: .github/prompts/ERPEC26-TX06-RETENCIONES.md. Fases: alcance firmado, implementación/pruebas, instalación/verificación.

## TX07 — Intersección automática por línea

Autorización ampliada: comparar los detalles de los planes del proveedor/cliente con los planes del artículo de cada línea. Los planes pueden ser diferentes. Se aplican únicamente detalles comunes, sin duplicarlos cuando aparecen en varios planes. Los tipos aportan planes adicionales; casos con asignaciones requieren coincidencia de tipos y casos sin asignaciones se consideran generales para su operación. Las facturas de proveedor también consumen casos de compra.

Compras, ventas y facturas en borrador usan impuestos y posiciones fiscales nativas. Sin planes a ambos lados se conserva el comportamiento previo; una configuración parcial o sin detalle común requiere corregirse antes de confirmar. La consolidación nativa suma el impuesto repetido. Las retenciones previstas consolidan bases por detalle, con desglose por línea; la preparación automática de compras USD requiere confirmar Renta sobre subtotal neto e IVA sobre IVA causado en ambos casos. Otros tratamientos requieren revisión y preparación específica. No se generan asientos ni comprobantes de retención por esta previsión.

Prompt: .github/prompts/ERPEC26-TX07-INTERSECCION.md. Secuencia: alcance → implementación/regresión → instalación con respaldo y revisión visual → cierre de evidencia y Git. Las pruebas TX06 no acreditan TX07.

### Cierre TX07

Implementación, regresión, instalación y revisión visual completadas. Evidencia: `docs/evidencias/ERPEC26-TX07-CIERRE.json`. El cierre cubre la intersección automática y sus límites; no cierra SP02 ni certifica tratamientos tributarios reales.
