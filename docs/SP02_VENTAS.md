# SP02: ventas, cobros y coordinación operativa

## Recorrido disponible

En **Inicio → Cotizaciones y pedidos**, la lista muestra los documentos accesibles del usuario, su entrega y facturación. No activa automáticamente «Mis cotizaciones» ni presenta filas de ejemplo como documentos operativos. Las reglas nativas siguen limitando los pedidos de cada vendedor.

Al abrir un pedido, **Seguimiento de la venta** explica el siguiente paso según su estado: revisión, entrega parcial, cantidades facturables, anticipo expreso, abono por devolución o revisión de cobros. Los accesos a entregas y documentos respetan los permisos de cada área. Facturar, cobrar, conciliar y obtener autorización SRI son pasos diferentes.

## Correcciones de coordinación

- El responsable contable puede registrar y conciliar extractos con permisos específicos, conservando las reglas por empresa. No se le añade acceso a la nómina ni permiso adicional de eliminar extractos.
- La protección de los asientos de nómina comprueba internamente si existe un vínculo; ya no exige que un contable comercial pueda leer salarios para modificar una línea ajena a nómina. La protección de los asientos vinculados se conserva.
- Los dos documentos saneados de la semilla recuperan sus vínculos exactos con compra y venta. Se contrastan empresa, proveedor/cliente, producto, cantidad, precio, impuesto, documentos relacionados y estado. Si hay otra factura o vínculo ambiguo, se detiene la reparación. Se conserva el asiento publicado y se coordinan los impuestos de los pedidos demostrativos con sus sustitutos.
- Producción distingue **Iniciar producción** de la entrada al centro de trabajo e indica dónde registrar el motivo de pausa. La columna de motivo está disponible entre las columnas opcionales de operaciones.
- Importaciones muestra los costos preparados como consulta. Cuando existen costos, proveedor, moneda y compras vinculadas dejan de ofrecer edición; las validaciones del modelo siguen activas.

## Validación y límites

La prueba comercial usa cinco unidades a 20 y el IVA del 15 % configurado: primera entrega de dos unidades y factura de 46, cobros de 20 y 26; segunda factura de 69; devolución de una unidad y abono de 23; saldo restante de 46 cobrado y conciliado. Al final quedan cuatro unidades entregadas y cero deuda de esas facturas. Son operaciones de prueba en copia aislada, sin transferencias externas ni emisión SRI.

También se comprueban servicios, prohibición de facturar cantidades aún no entregadas según su política, cancelación sin borrar una factura publicada, permisos de bodega y protección de nómina. La evidencia ejecutada está en evidencias/ERPEC26-SP02-VENTAS.json; este documento no reemplaza las pruebas.

La revisión visual usa la sesión administradora de la demo. El ciclo completo automatizado usa vendedor, bodega y contabilidad; no equivale a aceptación visual integral con usuarios finales. En importaciones se revisó el expediente existente de un producto; el recorrido visual de dos productos y divisas sigue pendiente. En producción no se declara completado un nuevo ciclo visual por operario y supervisor.

Continúan abiertos la homologación de archivos bancarios, firma/emisión fiscal completa, equivalencia laboral integral y la puerta comercial. Mantenerlos visibles en el plan y no reemplazarlos por una afirmación de ERP terminado.
