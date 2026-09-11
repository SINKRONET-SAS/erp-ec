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
