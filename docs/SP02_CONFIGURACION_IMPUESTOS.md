# SP02 — Planes, intersección de detalles y aplicación automática

## Configuración

1. En Áreas → Configuración de impuestos → Catálogos SRI, revise código, clase, versión, fuente y tarifa condicionada.
2. En Detalles y cuentas, o en los accesos de retenciones de Renta/IVA, vincule el detalle nativo a la referencia y configure sus cuentas de factura y devolución.
3. Cree planes con varios casos. Cada caso agrupa varios detalles de impuestos facturados, Renta e IVA por separado y tiene una operación.
4. Asigne planes al proveedor/cliente comercial y al producto. Se agregan los planes de sus tipos tributarios, conservados por empresa.
5. Si un caso tiene asignaciones, se usa solo cuando coinciden los tipos de tercero y producto y su operación. Un caso sin asignaciones es general para su operación. La factura de proveedor admite también los casos de compra.
6. Consulte el resultado o seleccione tercero y productos en un documento en borrador.

La comparación es por cada línea y por el mismo detalle nativo, no por nombre, código similar ni igualdad de planes. Se intersectan los detalles aportados por ambos lados, dentro de la misma empresa y operación. Si el mismo detalle aparece en varios planes, se aplica una vez a la línea.

Ejemplo: plan del proveedor con IVA 15 % e IVA 5 %; plan del producto A solo con el mismo detalle IVA 15 %; plan del producto B solo con el mismo detalle IVA 5 %. Dos líneas de A por 100 y 50 generan IVA 22,50; una línea de B por 100 genera IVA 5,00. El total nativo consolida 27,50 de impuestos sobre 250,00. El mismo mecanismo se aplica al cliente y sus productos de venta.

## Aplicación y consolidación

Se cargan impuestos automáticamente en borradores de compra, cotización y factura al seleccionar tercero/producto, conservando el cálculo y la posición fiscal nativos. No se mantienen tasas ni cuentas duplicadas en el plan.

Sin planes en ambos lados se conserva la configuración previa del artículo. Si solo un lado tiene planes o no hay detalles comunes, aparece el motivo y se impide confirmar hasta corregir la configuración. Una exención requiere su detalle explícito. Si los planes cambian después de cargar una línea, la confirmación exige volver a seleccionar el producto; no se reescriben masivamente documentos confirmados.

Las retenciones previstas aparecen separadas del IVA facturado. Para preparar automáticamente compras USD, el responsable confirma en los casos de ambos planes que corresponde Renta sobre subtotal neto e IVA sobre IVA causado, con tarifas revisadas. El importe preliminar usa el cálculo existente de preparación. Casos con otras bases, condiciones o monedas requieren revisión específica.

Las bases de líneas repetidas se suman por detalle; editar o eliminar una línea actualiza la preparación automática. Se conserva el desglose de bases por línea. Una preparación manual para el mismo detalle produce un aviso de conflicto y no se sobrescribe. El cero no crea una retención positiva.

En ventas se muestra la previsión consolidada; el comprobante de retención recibido del cliente se registra en el flujo contable existente. La previsión no genera por sí sola asientos, cobros, firma, XML ni autorización SRI.

## Catálogos y alcance

Se incluyen nueve referencias IVA de la tabla 17, ocho códigos de retención IVA de la tabla 20 de la ficha SRI 2.34 y 123 referencias de Renta del catálogo ATS desde 06/08/2026. Las tarifas condicionadas se preservan como texto. No se sustituyen masivamente porcentajes históricos de detalles operativos.

## Conciliación de tarifas de retención

En **Retenciones de Renta y cuentas** y **Retenciones de IVA y cuentas**, el listado compacto muestra el código SRI, la tarifa operativa y uno de estos estados: Falta referencia, Coincide, No coincide, Revisión pendiente o Revisada. La tarifa publicada y el mensaje completo pueden activarse como columnas opcionales y siempre aparecen en el formulario.

Una tarifa numérica única coincide cuando su valor absoluto es igual al porcentaje operativo del detalle. Una divergencia bloquea el caso y no puede aprobarse manualmente. Las tarifas condicionadas, múltiples o narrativas exigen que el responsable contable escriba la justificación y use **Confirmar revisión de tarifa**. La huella conserva referencia, versión, texto de fuente, tipo de cálculo y porcentaje; si cualquiera cambia, la revisión queda pendiente otra vez.

La instalación no enlaza los detalles históricos por su nombre. En la demo existen 74 detalles nativos de retención y ninguno estaba vinculado al catálogo al cerrar TX08; aparecen como **Falta referencia** para que el responsable seleccione el código correcto. Inferir o actualizar masivamente esos vínculos habría ocultado diferencias reales, como el detalle histórico 304E al 8 % frente a la referencia ATS actual al 10 %.

Fuente y huella del catálogo: evidencias/ERPEC26-TX06-FUENTES.json. Un código publicado no acredita por sí solo el tratamiento de una transacción. ICE, IRBPNR, bases especiales y aceptación fiscal integral siguen pendientes.

## Venta y valoración visual anterior

En ec_operational_7a74b3c051 se confirmó S00049, se entregó una unidad por WH/OUT/00029 y se devolvió por WH/IN/00196. WH/OUT/00030 conserva una unidad pendiente. Entregado neto cero; sin factura. Salida y retorno por 10,32 USD, asientos balanceados, inventario final de dos unidades y valoración de 20,63 USD. Evidencia: evidencias/ERPEC26-SP02-VENTA-VISUAL.json. No se alteró el contador histórico.

## Recuperación y continuidad

Conservar el respaldo indicado en el cierre de la instalación. Para ensayar su recuperación en otra base:
`scripts/restore-operational-demo.py --backup <ruta-del-respaldo> --imports-ui-backup --expect-workspace --expect-treasury`.

La herramienta conserva la demo. El respaldo previo contiene el estado anterior; no representa una migración inversa de datos nuevos. No se declara restauración del nuevo respaldo sin evidencia.

SP02 permanece abierto por cobertura tributaria y aceptación integral pendientes.
