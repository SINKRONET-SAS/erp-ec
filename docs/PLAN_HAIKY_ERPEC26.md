# Plan HAIKY ERPEC26 — implementación integral de ERP Ecuador

Objetivo: comercializar Odoo Community en la nube mediante planes propios, integrado con SKNOMINA y SINKRONET FACTURADOR, aprovechando localización Community y revisando capacidades Enterprise sin incorporar código no autorizado.

Estado: fase 00 documental completada; fases 01–08 pendientes. No hay despliegue, conectores nuevos ni migraciones ejecutadas.

Referencias: MATRIZ_CAPACIDADES.md, ARQUITECTURA_Y_CONTRATOS.md y evidencias/fuentes.json. Ruta física SKNOMINA verificada: C:/proyectos web/nuevo_nomina; la variante C:/proyectos web/nuevo/_nomina no existe en esta máquina. Facturador contiene trabajo ajeno pendiente y debe preservarse.

| Fase | Entrega | Depende | Estado |
|---|---|---|---|
| ERPEC26-00 | Gobierno y diagnóstico | Ninguna | Completada: documentación |
| ERPEC26-01 | Procedencia y alcance Ecuador | 00 | Pendiente |
| ERPEC26-02 | Base Community y aislamiento | 01 | Pendiente |
| ERPEC26-03 | Organizaciones, identidad y planes | 02 | Pendiente |
| ERPEC26-04 | Aprovisionamiento SaaS | 03 | Pendiente |
| ERPEC26-05 | Facturación desde Odoo | 04 | Pendiente |
| ERPEC26-06 | Nómina y contabilidad | 05 | Pendiente |
| ERPEC26-07 | Cobertura Ecuador ampliada | 06 | Pendiente |
| ERPEC26-08 | Piloto, operación y publicación | 07 | Pendiente |

## Ejecución y control de alcance

Cada prompt define tareas y gates. La solicitud actual crea el plan; la ejecución de fases funcionales queda pendiente. Los cambios futuros en los tres repositorios se coordinarán mediante commits separados y referencias cruzadas, sin trasladar código privado a un remoto no autorizado.

No se estiman fechas o precios sin dimensionar clientes, usuarios simultáneos, volumen fiscal, almacenamiento y soporte. El primer incremento operativo cubre factura y nómina contable; documentos adicionales requieren sus propios contratos, pruebas y homologación.

## Decisiones pendientes

- Confirmar soporte y commit Community 18; cualquier cambio de versión actualiza matriz y pruebas.
- Elegir proveedor/región, dominios y objetivos de disponibilidad, recuperación y retención.
- Definir titularidad/licencia de módulos propios y revisar complementos seleccionados.
- Elegir autoridad de cobro de suite y vinculación de contratos vigentes sin doble cargo.
- Confirmar responsables de validación fiscal/contable y credenciales de pruebas.

Estas decisiones no bloquean la planificación completada. Sí condicionan las fases correspondientes.
