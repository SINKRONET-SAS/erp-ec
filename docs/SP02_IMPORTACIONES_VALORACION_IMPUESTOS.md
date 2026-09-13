# SP02 — Importaciones, valoración nueva y plan de impuestos
Ejecución del 13/09/2026 en la copia ec_operational_7a74b3c051. Evidencia consolidada: evidencias/ERPEC26-SP02-IMPORTACIONES-VALORACION.json. SP02 permanece abierto.

## Importación observada
Comprador confirma P00011 por 300 EUR. Bodega recibe 5 unidades de cada artículo y después las 5 restantes: WH/IN/00079 y WH/IN/00099, diez unidades A y diez B. Contabilidad registra la factura exterior sintética ENSAYO-SP02-FLETE por 30 EUR, clasifica el flete capitalizable y prepara LC/2026/0059.

La distribución por valor agrega 34,78 USD: 5,80 por cada recepción de A y 11,59 por cada recepción de B. Inventario de 347,76 a 382,54 USD. El ajuste inverso LC/2026/0060 devuelve exactamente 347,76 USD: A 115,92 y B 231,84; costos unitarios 11,592 y 23,184. Asientos MISC/2026/09/0006 y 0007 publicados y balanceados. No se acredita liquidación aduanera ni tratamiento tributario real.

Se corrigieron accesos que bloqueaban al perfil de bodega al cargar relaciones contables ocultas, y al responsable contable al leer solicitudes fiscales que no le correspondían. La consulta interna de existencia conserva los bloqueos de documentos con envío fiscal preparado. No otorga lectura de esa bandeja. El adjunto del ensayo quedó vinculado al expediente y los usuarios ficticios recibieron direcciones example.invalid para las notas internas; no hay servidor de correo activo.

## Fabricación sin contador heredado
La semilla prepara por ORM cuatro componentes a 5 USD y una orden nueva, sin temporizadores. El supervisor confirma WH/MO/00059, ejecuta dos operaciones dependientes, cierra los intervalos y produce dos unidades en pantalla. El historial antiguo se conserva.

Materiales 20,00 USD; intervalos de 12 y 26 segundos, duraciones nativas redondeadas 0,20 y 0,43 minutos; centro sintético de 60 USD/h. Costo nativo 20,63 USD; visualización unitaria 10,32 USD. Sin intervalos abiertos y con asientos balanceados. Es un ensayo representativo del mecanismo de valoración, no un estudio de tiempos industriales.

Una transacción automatizada entrega una unidad por 10,32 USD y la devuelve por el mismo valor; verifica existencias 2 → 1 → 2 y asientos balanceados, después revierte toda esa transacción. La entrega/devolución no fue un recorrido visual ni produjo una factura.

## Plan de impuestos
Acceso en Inicio → Consultar plan de impuestos y menú Áreas. Disponible al responsable contable. Cree una consulta con empresa, operación, artículo y proveedor/cliente. Odoo resuelve la posición fiscal y los impuestos; el plan muestra los de origen y resultado, componentes de grupos, reparticiones de factura/devolución y cuentas vinculadas.

Desde las cuentas vinculadas, abra y expanda la ficha: el botón nativo Impuestos devuelve el catálogo filtrado. Catálogo de impuestos, Plan de cuentas y Posiciones fiscales también son accesibles desde el encabezado del escenario. Los impuestos predeterminados de una cuenta no representan su vínculo de contabilización.

La consulta visual «Cruce de compra · Aceptación SP02» expuso que el artículo conserva IVA 15% y la cuenta 11050101 aun al elegir el proveedor exterior sin posición fiscal. Es configuración existente que requiere revisión contable, no tratamiento validado ni asignado automáticamente por este incremento. Los artículos importados del ensayo permanecen sin impuestos de compra; no se declara esa ausencia como exención.

Las consultas reflejan configuración vigente al abrirlas. No son versiones históricas de reglas ni sustituyen los cambios manuales o dirección de entrega de un documento. Retenciones específicas, sustento ATS, nómina y validación tributaria real conservan sus controles y pendientes. Plan y fases: PLAN_HAIKY_IMPUESTOS.md y .github/prompts/ERPEC26-TX01-PLAN-IMPUESTOS.md.

## Verificación, instalación y recuperación
32/32 pruebas de importaciones, centro de trabajo y conector aprobadas en la copia, con salida 0. Incluyen correspondencia con compra nativa, impuestos agrupados, ausencia de configuración, accesos negativos, aislamiento y herencia en sucursales. Vistas y once accesos comprobados en demo; 40 archivos instalados coinciden con los probados.

Instalación con respaldo imports-ui-install-20260913-165519. Recuperado en ec_recovery_746b09dd18: filestore y módulos coincidentes, centro, asientos y Tesorería conservados. El respaldo corresponde al estado anterior al incremento; no acredita recuperación de escenarios tributarios creados después.

Para recuperar: scripts/restore-operational-demo.py --backup RUTA_ABSOLUTA --imports-ui-backup --expect-workspace --expect-treasury. Crea otra base y carpeta; verificar esa copia antes de cualquier cambio de servicio. No reemplaza la demo automáticamente.

Scripts de contraste: verify-sp02-imports.py, verify-sp02-valuation.py y verify-tax-plan-runtime.py, ejecutados en Odoo shell con la configuración de la copia autorizada. La valoración y la consulta tributaria revierten sus transacciones de ensayo.

## Pendientes conservados
SP02 mantiene abiertos los recorridos integrales restantes, la aceptación visual de venta/devolución de la nueva producción, los gates fiscales, equivalencia laboral, homologación bancaria y calidad comercial. No se cierra una fase histórica ni se acredita WCAG por estas pruebas. Las capturas se limitan al escritorio; el título largo del escenario puede recortarse mientras se edita y permanece completo en la navegación.
