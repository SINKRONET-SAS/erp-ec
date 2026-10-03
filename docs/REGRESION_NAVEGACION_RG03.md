# RG03 — navegación tributaria e identidad del producto

Solicitud del 03-10-2026: recuperar planes, detalles y clases de proveedores e ítems en Fundador, eliminar promoción ajena visible y comprobar paridad funcional con demo.

## Causa comprobada

El servidor del Fundador entregaba los menús tributarios y tenía erpec_workspace 18.0.1.3.1 instalado. ProductShell ocultaba todas las secciones cuando la aplicación activa era erpec_base.suite_root. Los menús de impuestos seguían bajo esa raíz. Las comprobaciones anteriores abrían acciones por URL, por lo que no acreditaban que el usuario pudiera encontrarlas navegando.

Ajustes conservaba mobile_apps_funnel y res_config_edition, incluidos QR y promoción móvil del proveedor del núcleo. La pestaña usaba su icono predeterminado.

## Corrección

- Aplicación Impuestos para responsables contables; planes, detalles, clasificaciones, asignaciones y consulta conservan sus modelos y datos.
- Accesos específicos a clases de proveedores/clientes y clases de ítems, con filtro y valor inicial por tipo. Los cuatro accesos principales se priorizan en la barra; se retira el acceso combinado duplicado.
- Restauración de las secciones del menú ERP EC para evitar ocultar otras funciones.
- Ajustes con identidad ERP EC · SINKRONET. Créditos y licencias conservados en una sección desplegable; sin QR de tiendas.
- Pie del acceso web con identidad ERP EC, sin promoción del proveedor del núcleo.
- Icono propio y retirada de enlaces de documentación, soporte y cuenta externos del menú de usuario. Preferencias, atajos y salida se conservan.
- Versión erpec_workspace 18.0.1.3.2, registrada en el control de versiones.

## Verificación y despliegue

44 pruebas del módulo aprobadas, sin fallos, errores u omisiones. Registro local: ec_integrated_test_3567a6cdc267.log. Incluye acceso del responsable contable sin privilegio de administrador del sistema, exclusión del perfil básico, acciones de clasificación y composición de Ajustes.

La actualización y el recorrido real quedan registrados en docs/evidencias/RG03. El recorrido usa menús visibles y abre formularios nuevos sin guardar registros, además de revisar Ajustes e icono.

Fundador (8199, erpec_fundador) y demo (8369, erpec_demo) conservan bases independientes. La paridad de esta corrección se verifica por versión y recorridos; no se copian datos de demostración al Fundador ni se afirma igualdad integral entre las bases.

## Operación y reversión

Ejecutar scripts/update-navigation-rg03.py para actualizar ambas instancias con mantenimiento, respaldo completo y comprobación exacta de asientos, líneas, planes y clasificaciones antes/después. Un fallo conserva el mantenimiento y el respaldo para diagnóstico. Cada informe update-*.json identifica la copia recuperable y se valida con scripts/restore-cm28-instance.py --report <informe>. La restauración efectiva requiere --apply y no se ejecuta durante una validación.

Ejecutar scripts/verify-navigation-rg03.py tras actualizar para acreditar navegación, formularios y marca en ambas instancias. No guarda operaciones comerciales ni envía comprobantes, correos o pagos. No acredita homologación fiscal.
