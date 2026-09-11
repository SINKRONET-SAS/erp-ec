# Operación comercial Community en el cliente local

Incremento de preparación del cliente en ERPEC26-04. Instala módulos Community oficiales de ventas, compras e inventario y sus enlaces con facturación; añade el módulo propio `erpec_operations`. No implementa ni declara terminado el conector fiscal de fase 05. No se cierra fase 04 ni se crean recursos en Render.

## Acceso

En el cliente `http://127.0.0.1:8186`, entrar a **ERP EC → Operación Ecuador** y abrir la empresa. La pantalla reúne Ventas, Compras, Inventario y Facturas de clientes. Muestra datos básicos faltantes de la empresa y conserva visible la advertencia de emisión electrónica pendiente. Los menús propios de las aplicaciones Community también quedan disponibles según los permisos del usuario.

La pantalla de preparación está reservada al administrador del ERP, conforme a los permisos existentes de `erpec.workspace`. Los botones abren las acciones oficiales y mantienen las reglas de compañía de Odoo. No conceden roles nuevos a empleados ni cambian sus permisos.

## Alcance comprobado

Tres pruebas transaccionales en una copia aislada de la base del cliente:

1. Confirmar venta sintética de un servicio y generar factura borrador por USD 20, sin impuestos en el ensayo. Se comprueba importe, compañía y estado borrador. No es un ejemplo de tratamiento tributario para producción.
2. Confirmar venta de artículo almacenable y comprobar que genera entrega; confirmar compra y comprobar que genera recepción de la misma compañía. No acredita recepción física ni entrega validada.
3. Resolver los cuatro accesos de operación, validar la vista y comprobar que el diagnóstico y la limitación fiscal permanecen visibles.

Se instalaron `sale_management`, `sale_stock`, `purchase_stock` y sus dependencias de Community. No se incorporaron módulos OEEL-1 u OPL-1. Los módulos del controlador de pagos y aprovisionamiento permanecen separados del cliente.

## Instalación y resguardo

`scripts/verify-operations.py` utiliza PostgreSQL existente y crea una base aislada desde un respaldo del cliente. El reporte privado incluye resultado, registro y hashes del módulo. No envía documentos al SRI ni llama a PayPhone.

`scripts/install-operations.py` exige las pruebas aprobadas y coincidencia de hashes. Valida el PID, puerto y base del cliente, lo detiene, guarda base y filestore, copia únicamente el módulo propio al directorio de addons del cliente, instala y reinicia en un bloque de recuperación. Comprueba autenticación y módulos instalados. El operador 8169 no se reinicia.

Los scripts de este incremento apuntan expresamente al cliente de ensayo `b0bdbfd97ff34409b0fe0ea9eff6793f`, puerto 8186. No son todavía el empaquetado general de futuras instancias ni la imagen de Render.

## Reversión y pendientes

No desinstalar automáticamente Ventas, Compras o Inventario después de introducir datos. Para una reversión completa inmediata debe detenerse el cliente y restaurarse conjuntamente el respaldo de base y filestore previo al cambio, conservando primero cualquier trabajo posterior. La restauración implica descartar cambios posteriores y requiere revisar su alcance; no se ha ejecutado en este incremento. Los respaldos se mantienen en `.cache/windows/backups/operations-install-*`, fuera de Git.

Pendientes: incorporación del paquete al aprovisionamiento de futuras instancias, validación del flujo físico completo de inventario, configuración empresarial y permisos operativos finales; conector fiscal, XML/RIDE y confirmación de autorización según fase 05; nómina y contabilidad integrada según fase 06. Mostrar o crear una factura en Odoo no significa que el SRI la haya autorizado.
