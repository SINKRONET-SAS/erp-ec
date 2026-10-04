# UX04 — continuidad de navegación y ambiente SRI

La revisión en navegador reprodujo dos recorridos diferentes de Ventas: Inicio abría el listado propio manteniendo el área Inicio, mientras Aplicaciones abría otro listado con promoción del proveedor y filas de ejemplo. Ambos accesos usan ahora la misma acción y conservan Ventas en la barra. Los accesos a facturas y facturas de proveedores también resuelven la acción de su menú autorizado y limpian la navegación previa.

La paleta común se define antes de los estilos del núcleo. Administración identifica las funciones administrativas; Tesorería pertenece a Contabilidad y Producción y trabajo a Manufactura. Facturación electrónica tiene entrada propia. Los créditos y licencias se conservan. El pie público, el título inicial y el aviso de sesión usan la identidad ERP EC.

## Ambiente SRI

La configuración ya existía por punto de emisión, pero su menú largo quedaba dentro de Más y no nombraba el ambiente. Ahora Facturación electrónica abre primero **Ambiente SRI**. El formulario expone **Ambiente actual**, Pruebas/Producción, y las acciones **Habilitar producción** y **Volver a pruebas** para responsables contables. Se mantiene el control de certificado reconocido y la numeración independiente por ambiente; no se cambia el ambiente de ningún punto operativo durante esta revisión.

La [página oficial SRI](https://www.sri.gob.ec/facturacion-electronica) publica la ficha 2.34, julio de 2026. Se descargó y contrastó la tabla 4 (1 pruebas, 2 producción) y 7.2.1/7.2.2 (celcer/cel para recepción y autorización). El código existente propaga el ambiente a XML, clave de acceso y servicios SRI. Evidencia de fuente y hash: evidencias/UX04/sri-2026.json. Esta revisión no acredita cumplimiento integral de toda la ficha ni autorización real del SRI.

## Recorrido y conservación

Fundador y demo reciben los mismos cambios. Sus datos se mantienen separados; no se copia información ficticia a Fundador. El actualizador respalda y compara íntegramente las tablas de asientos, líneas, planes y clases antes y después. Los informes de actualización registran los hashes y el estado del esquema. La validación de estructura del respaldo no equivale a ejecutar una restauración.

Las capturas anteriores documentan Inicio, sus ventas y el acceso alternativo. Las posteriores documentan el menú y la configuración visibles. No se guardan nuevos documentos comerciales ni se habilita producción ni se transmite al SRI.

La prueba inicial de workspace y sitio público pasó 58 casos. Dos ensayos intermedios detectaron un idioma es_EC no instalado en una base nueva y el orden de actualización del enlace único /odoo/sales; se corrigieron usando solo idiomas activos y vaciando la escritura del enlace anterior antes de reasignarlo. El resultado de la validación final y los hashes de capturas se registran en evidencias/UX04/validacion.json.

Resultado final Odoo: 163 pruebas, cero fallos y errores, cierre normal registrado. El ejecutor externo devolvió TimeoutExpired al esperar el proceso tras una interrupción larga del reloj del equipo; su salida 1 se conserva como limitación de ejecución, no se atribuye salida 0. Seis pruebas de gobierno aprobadas. Evidencia: evidencias/UX04/pruebas.json.
