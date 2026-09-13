# ERPEC26-OP05 — Anexos fiscales ATS y RDEP

Leer AGENTS.md, RULES.md, el contexto histórico, docs/PLAN_AMPLIACION_OPERATIVA.md y docs/ALCANCE_ATS_RDEP.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Investigar y documentar el alcance del Anexo Transaccional Simplificado (ATS) y del Anexo de Relación de Dependencia (RDEP) contra los esquemas oficiales vigentes del SRI, tomando como referencia adicional lo ya desarrollado en SINKRONET FACTURADOR (ATS) y SKNOMINA (nómina), sin copiar sus fuentes. El ATS existe dentro de Facturador pero no está expuesto en su API externa (docs/evidencias/ERPEC26-01.md); no se puede depender de esa integración sin ampliar ese contrato primero.

No inventar catálogos, códigos ni campos cuyo significado no esté confirmado en el propio esquema descargado o en su documentación oficial. Un campo requerido por el esquema cuya fuente de cálculo no exista todavía en el ERP se documenta como pendiente; no se completa con ceros, supuestos ni datos sintéticos presentados como reales. No se declara homologación, presentación ni equivalencia integral en ningún incremento de este complemento.

Empezar por inspeccionar el estado actual, las licencias y lo ya nativo en erpec_payroll, erpec_withholding_accounting, erpec_fiscal_native e erpec_imports antes de modelar campos nuevos. Aprovechar el código Community y los motores propios ya disponibles. No modificar productos fuente (Facturador, SKNOMINA) como efecto secundario.

## Entrega verificable

Preparar respaldo y trabajar primero en copia aislada. Implementar solo los modelos, permisos y navegación que los datos disponibles permitan cubrir honestamente; probar el ciclo con datos sintéticos, sin generar ni presentar anexos ante el SRI mientras falten catálogos o campos requeridos. Instalar en la demo solamente después de aprobar los controles. Mantener su RUC vacío.

Registrar evidencia real, resultado de pruebas, límites y guía corta de demostración en docs/evidencias/. Las carencias de catálogo, ficha técnica o cálculo deben indicar acción concreta (qué documento falta, qué campo del motor falta); no retirar requisitos ni declararlos aprobados. Verificar UTF-8, gobierno y diferencias de Git. Commit: phase: ERPEC26-OP05 task: ERPEC26-OP05.N. No cerrar la fase por añadir un documento o instalar un módulo.

## Primer incremento autorizado — 13-09-2026

El titular pidió investigar y documentar el alcance, y ejecutar el resultado. Se entrega docs/ALCANCE_ATS_RDEP.md con el alcance normativo confirmado contra `ats.xsd` y `Esquema RDEP 2023.xsd` leídos directamente, y un primer incremento de código: agregador RDEP de solo lectura sobre `erpec_payroll` (períodos ya contabilizados) más los campos de empresa/empleado cuyo significado está documentado en el propio esquema oficial. El ATS queda íntegramente pendiente del Catálogo ATS oficial (códigos de sustento y tipo de comprobante), que no se ha obtenido. La generación de XML del RDEP también queda pendiente: el esquema exige participación de utilidades, intereses ganados, salario digno, otros ingresos gravados y deducciones desglosadas por categoría, que el motor de nómina nativo no calcula todavía.

No se declara el anexo presentable, homologado ni equivalente a Facturador/SKNOMINA. Evidencia: docs/evidencias/ERPEC26-OP05-ANEXOS-ATS-RDEP.json.
