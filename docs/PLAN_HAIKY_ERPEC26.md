# Plan HAIKY ERPEC26 — implementación integral de ERP Ecuador

Objetivo: comercializar Odoo Community en la nube mediante planes propios, integrado con SKNOMINA y SINKRONET FACTURADOR, aprovechando localización Community y revisando capacidades Enterprise sin incorporar código no autorizado.

Estado: fases 00–03 completadas; fase 04 parcialmente implementada y validada localmente; pendiente de adaptación a Render; PAYPHONE probado localmente por túnel. Windows es el entorno local; Render alojará producción y PostgreSQL, con Cloudflare para el dominio futuro. No hay despliegue productivo.

Referencias: MATRIZ_CAPACIDADES.md, ARQUITECTURA_Y_CONTRATOS.md y evidencias/fuentes.json. Ruta física SKNOMINA verificada: C:/proyectos web/nuevo_nomina; la variante C:/proyectos web/nuevo/_nomina no existe en esta máquina. Facturador contiene trabajo ajeno pendiente y debe preservarse.

| Fase | Entrega | Depende | Estado |
|---|---|---|---|
| ERPEC26-00 | Gobierno y diagnóstico | Ninguna | Completada: documentación |
| ERPEC26-01 | Procedencia y alcance Ecuador | 00 | Completada |
| ERPEC26-02 | Base Community y aislamiento | 01 | Completada: piloto Windows verificado |
| ERPEC26-03 | Organizaciones, identidad y planes | 02 | Completada: contratos locales sin cargo automático |
| ERPEC26-04 | Aprovisionamiento SaaS | 03 | Parcial: piloto local probado; adaptación Render pendiente; PAYPHONE local probado |
| ERPEC26-05 | Facturación desde Odoo | 04 | Pendiente |
| ERPEC26-06 | Nómina y contabilidad | 05 | Pendiente |
| ERPEC26-07 | Cobertura Ecuador ampliada | 06 | Pendiente |
| ERPEC26-08 | Piloto, operación y publicación | 07 | Pendiente |

## Ejecución y control de alcance

Cada prompt define tareas y gates. El usuario autorizó ejecutar todas las fases y publicar los cambios. Los cambios futuros en los tres repositorios se coordinarán mediante commits separados y referencias cruzadas, sin trasladar código privado a un remoto no autorizado.

No se estiman fechas o precios sin dimensionar clientes, usuarios simultáneos, volumen fiscal, almacenamiento y soporte. El primer incremento operativo cubre factura y nómina contable; documentos adicionales requieren sus propios contratos, pruebas y homologación.

## Decisiones pendientes

- Community 18 fijado en upstream.json y verificado en fase 01; cualquier cambio de versión actualiza matriz y pruebas.
- Proveedores elegidos: Render para producción, Cloudflare para DNS/proxy y PAYPHONE para pagos. Faltan región, recursos y objetivos de disponibilidad/recuperación/retención. El dominio se contratará después; se permite probar con la URL HTTPS de Render.
- Definir titularidad/licencia de módulos propios y revisar complementos seleccionados.
- Elegir autoridad de cobro de suite y vinculación de contratos vigentes sin doble cargo.
- Confirmar responsables de validación fiscal/contable y credenciales de pruebas.

Estas decisiones no bloquean la planificación completada. Sí condicionan las fases correspondientes.

## Ampliación fiscal local autorizada — 11-09-2026

El titular solicita trasladar también lógica de facturación al ERP. Se permite avanzar el incremento local independiente de Render, preservando las dependencias del cierre histórico. Primer incremento: XML previo sin firma; evidencia ERPEC26-FISCAL-NATIVO.json y guía FACTURACION_LOCAL.md. La emisión fiscal completa y el cierre de ERPEC26-05 siguen pendientes. No se modifica el repositorio fuente del Facturador.

## Segunda pasada autorizada — septiembre de 2026

La revisión de estabilización, navegación y experiencia de producto tiene prioridad sobre nuevas ampliaciones aisladas. Su orden y puertas de aceptación están en SEGUNDA_PASADA_PRODUCTO.md. El centro de trabajo constituye un incremento local; no sustituye ni cierra las validaciones pendientes de este plan.

## Anexos fiscales ATS y RDEP autorizados — 13-09-2026

El titular pidió investigar y documentar el alcance de los anexos ATS y RDEP del SRI, con referencia adicional a lo ya construido en SINKRONET FACTURADOR y SKNOMINA, y ejecutar el resultado. Se amplía PLAN_AMPLIACION_OPERATIVA.md con el complemento OP05: ver docs/ALCANCE_ATS_RDEP.md para el alcance normativo y docs/evidencias/ERPEC26-OP05-ANEXOS-ATS-RDEP.json para el primer incremento (agregador RDEP de solo lectura; ATS pendiente del catálogo oficial). No se declara homologación ni presentación ante el SRI.

## Cumplimiento legal Ecuador autorizado — 13-09-2026

El titular pidió, en respuesta a la necesidad de garantizar cumplimiento legal (Tributario, Facturación Electrónica, ATS, RDEP, Laboral, Protección de Datos, envíos por email), generar un plan Haiky dedicado con su gobierno y ejecutarlo. Ver docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md, complemento OP06 con prompt en .github/prompts/ERPEC26-OP06-CUMPLIMIENTO-LEGAL-EC.md. Los dominios con documentación propia (Facturación Electrónica, ATS, RDEP, Laboral) se remiten a ella sin duplicarla. Protección de Datos y envíos por email, sin trabajo previo, se investigaron contra fuente oficial (LOPDP, Registro Oficial Suplemento 459 del 26-05-2021; Ley 67 de Comercio Electrónico) y tienen un primer incremento de código: módulo `erpec_data_protection` (Registro de Actividades de Tratamiento y exclusión de correo comercial). No se declara cumplimiento legal alcanzado en ningún dominio.


## Plan tributario transversal autorizado — 13-09-2026
Complemento local TX00–TX02: PLAN_HAIKY_IMPUESTOS.md. Relaciona catálogo, cuentas, artículos, proveedores y operaciones con las posiciones fiscales nativas. No sustituye los gates de emisión, retenciones, ATS ni validación legal.

## Revisión transversal autorizada — 14-09-2026

El titular pidió una pasada al funcionamiento, cálculos y reportes de nómina, facturación electrónica en pruebas y producción, y monetización. Se ejecuta como complemento CF01 de SP02 conforme a `docs/PLAN_HAIKY_REVISION_NOMINA_FISCAL_MONETIZACION.md`. La revisión puede corregir defectos locales reproducibles, pero no convierte simulaciones en homologación externa ni cierra las fases 04–08.
