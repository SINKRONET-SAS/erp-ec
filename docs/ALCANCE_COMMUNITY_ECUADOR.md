# Aclaración de producto: ERP comercial sobre Community para Ecuador

Instrucción del titular, 10 de septiembre de 2026: explotar comercialmente un ERP basado en Odoo Community y localizado para Ecuador. El producto no es una etapa previa a contratar Enterprise ni un canal para vender esa edición.

Esta aclaración reafirma el objetivo del plan ERPEC26 y guía los siguientes incrementos. Los documentos y evidencias anteriores conservan su carácter histórico; no se modifica su AuditLock para atribuirles capacidades nuevas.

## Producto que se construye

- Núcleo Odoo Community y módulos propios del ERP EC. Enterprise puede servir como referencia de necesidades, pero no es dependencia del producto ni solución propuesta para desbloquear funciones.
- Procesos comerciales integrados: ventas, compras, inventario, cobros y contabilidad, con experiencia operativa del ERP.
- Localización de Ecuador: completar y validar los procesos fiscales y contables definidos en la matriz, incluidos emisión electrónica, retenciones, reportes y anexos según el alcance de cada fase. La existencia de `l10n_ec` no acredita por sí sola toda esa cobertura.
- Integraciones con Facturador y SKNOMINA conforme a los contratos del plan, con una autoridad por cálculo y autorización. La elección de integración no convierte al producto en distribuidor de Enterprise.
- Comercialización propia mediante planes, implementación, soporte, mantenimiento y alojamiento. Los componentes incorporados requieren licencias compatibles; no se copia código Enterprise.

PayPhone, la cola de altas, Docker y Render apoyan la operación comercial. Su validación no equivale a haber terminado el ERP ecuatoriano. Las carencias funcionales deben implementarse y verificarse sobre Community; no cubrirse con botones que pidan comprar Enterprise. No se considerará listo el producto por tener una instancia y un pago exitosos.

## Corrección del catálogo actual

La revisión del piloto encontró cero módulos instalados con licencia OEEL-1 u OPL-1 y veinte tarjetas promocionales de Enterprise en el catálogo estándar. Se configuró la acción de aplicaciones para excluir los registros marcados `to_buy`, conservando sus filtros previos. La acción se identifica como **Aplicaciones ERP EC · Community**.

Aplicado y verificado en operador 8169 y cliente local 8186: cero promociones visibles y 36 aplicaciones en el catálogo. No se instalaron, desinstalaron ni borraron módulos. Se conservan los mecanismos de actualización técnica de los módulos instalados y las atribuciones del software. Ocultar promociones no implementa las funciones que esas tarjetas anunciaban.

El cambio corresponde a esas dos bases locales. Los contenedores Linux y futuras instancias requieren incorporar esta política al aprovisionamiento y a la experiencia de producto; no se afirma que ya esté aplicada en ellos. La configuración es persistente en la base, pero una actualización del módulo base puede sustituir la acción y requerir reaplicarla.

## Operación y reversión

Desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe scripts/configure-community-catalog.py --operator --instance b0bdbfd97ff34409b0fe0ea9eff6793f
```

El script obtiene las credenciales de los archivos privados existentes, guarda el estado anterior en `.cache/windows/catalog-backups`, comprueba que no haya módulos propietarios instalados y conserva cambios posteriores ajenos. Ejecutarlo de nuevo es idempotente. Para restaurar la acción anterior, usar los mismos argumentos y añadir `--restore`. No requiere reiniciar Odoo. Recargar la pantalla de aplicaciones para cargar la acción modificada.

La evidencia está en `docs/evidencias/ERPEC26-community-catalog.json`. La fase 04 permanece abierta; este ajuste de catálogo no cierra fases de localización ni acredita una validación fiscal. La cobertura funcional y las brechas de Ecuador deben seguir siendo visibles en el avance del producto.
