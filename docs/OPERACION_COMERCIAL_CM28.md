# Operación comercial CM28

En administración, abre ERP EC → Planes y versiones. Configura el importe mensual, el anual opcional, usuarios incluidos, máximo contratable y precio de cada usuario adicional por periodo. En Módulos internos del ERP, elige capacidades incluidas y complementos con su tarifa. SKNOMINA y SINKRONET FACTURADOR identifican conexiones externas y no sustituyen los módulos de nómina y facturación del ERP.

El responsable debe revisar los impuestos y condiciones antes de publicar. Solo se muestran ofertas ERP con precio positivo, módulos definidos, tratamiento tributario revisado y publicación habilitada. Las versiones nuevas nacen sin publicar. Retirar una oferta conserva contratos e historial. SS-DEMO se retira expresamente durante la actualización; no se crean tarifas comerciales de ejemplo en las instancias reales.

La portada y `/autoservicio` muestran el catálogo vigente. Si no hay ofertas, informan disponibilidad pendiente y no permiten solicitar cobro. El cliente usa una cuenta personal para configurar el plan, periodo, módulos y usuarios. El servidor presenta el desglose y crea una única solicitud por clave del formulario.

En `/mi-servicio`, cada titular consulta exclusivamente sus propias empresas y altas. El pago se prepara en la cola existente y se confirma con PayPhone en servidor. El estado muestra espera, preparación del ERP, disponibilidad, próxima renovación o revisión del operador. Una referencia de alta ajena devuelve 404 incluso si la conoce otro usuario autenticado.

Cuando la instancia está lista, el titular puede abrirla o configurar su contraseña mediante el enlace personal. Si el enlace caduca, solicita uno nuevo desde el seguimiento. La emisión del enlace requiere ejecutar el trabajador; no se imprimen contraseñas en las pantallas ni evidencias.

Renovar o cambiar plan abre las ofertas actuales para elegir condiciones del periodo siguiente. Se conserva la identidad del cliente y su instancia. La renovación exige otro pago confirmado; no existe débito automático ni prorrateo. Una reducción de usuarios que exceda las cuentas activas requiere archivar cuentas y reintentar la incidencia; no se archivan automáticamente.

ERP EC → Clientes muestra titular, contratos e instancia; Renovaciones muestra los contratos sucesores; Pagos PayPhone conserva la autoridad del cobro; Instancias y trabajos e Incidencias permiten supervisar y reintentar. El trabajador local `scripts/provision-worker.py` sigue siendo el ejecutor de infraestructura. Su operación productiva en nube queda fuera del alcance local CM28.

Los ensayos del navegador usan la copia aislada descrita por `.cache/windows/cm28-lab.json`, con cron y correo desactivados. Sus ofertas sintéticas no son tarifas comerciales.

## Actualización y reversión local

CM28-F exige restaurar primero copias de fundador y demo y comparar sus filas, adjuntos y descifrado de certificados. Las evidencias públicas omiten claves y contraseñas. `scripts/cm28-update-local.py demo fundador a b` detiene el supervisor durante la ventana de mantenimiento, conserva base, filestore, configuración, código anterior y clave en directorio separado; actualiza todos los módulos propios instalados y verifica esquema y disponibilidad. Un error mantiene la instancia afectada en mantenimiento para revisión.

Cada actualización escribe `docs/evidencias/CM28/update-<instancia>.json`, que identifica el respaldo privado. Para comprobar su reversibilidad sin alterar datos: `python scripts/restore-cm28-instance.py --report docs/evidencias/CM28/update-fundador.json`. Solo ante una reversión necesaria se añade `--apply`: conserva una copia de rescate de la base actual y recupera la base, archivos, clave y código anteriores. Las operaciones posteriores al respaldo quedan en la copia de rescate, no se fusionan automáticamente. Verificar acceso, asientos y adjuntos tras recuperar. Nunca usar estos comandos sobre producción.

Los precios comerciales permanecen sin publicar. El fundador debe configurar tarifas base, usuarios incluidos, usuarios adicionales mensuales/anuales, complementos e impuestos revisados antes de publicar la oferta. Sin oferta publicada, la portada informa disponibilidad pendiente y no inicia cobros.

Fabricación requiere Inventario contratado (incluido en el plan o seleccionado como complemento). El servidor rechaza una combinación incompleta antes de crear el pago; el trabajador vuelve a comprobarla. Las dependencias técnicas instaladas no conceden derechos comerciales por sí solas.
