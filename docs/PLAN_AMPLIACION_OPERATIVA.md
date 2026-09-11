# Ampliación aprobada: producción, órdenes de trabajo, nómina e importaciones

Complemento vigente del PLAN_HAIKY_ERPEC26.md, aprobado expresamente por el titular. Los cuatro frentes son entregables obligatorios del ERP comercial basado en Odoo Community. Importaciones significa compras al exterior, embarques y nacionalización de mercadería. No significa solamente carga de archivos.

Este documento complementa el plan histórico firmado sin alterar sus evidencias ni declarar fases terminadas. El estado siguiente distingue fuente inspeccionada, desarrollo y operación demostrada. La validación comercial de ERPEC26-08 deberá incluir los cuatro ciclos; ninguno puede retirarse del alcance sin decisión expresa del titular.

## Orden de ejecución y dependencias

1. OP01 Producción y OP02 Órdenes de trabajo: primer incremento integrado en una copia de la demo; después de validar, instalar y demostrar en la demo 8369.
2. OP03 Importaciones: expediente propio enlazado a compras, recepciones, gastos y valoración nativa. Requiere inventario y configuración contable probados.
3. OP04 Nómina: completar ERPEC26-06 con SKNOMINA como autoridad del cálculo y Odoo como autoridad del asiento. Preparar mapeos y casos sintéticos mientras se resuelve la disponibilidad del contrato externo.
4. Ensayo comercial transversal: importar insumos → recibir y nacionalizar → fabricar → registrar tiempos y costos → vender → registrar nómina y conciliar su costo por centro. La parte fiscal real conserva su gate de firma y ambiente de pruebas.

El orden anterior prioriza entregas locales demostrables. No elimina dependencias de cierre fiscal, permisos ni recuperación; una credencial que falte en un frente no impide trabajar en otro independiente. Render y producción pública conservan sus gates propios.

## OP01 — Control de producción

Base observada: mrp y mrp_account, LGPL-3 en el checkout oficial fijado. Reutilizar inventario, órdenes, listas de materiales y valoración; no crear un motor contable paralelo.

- Productos, unidades de medida, componentes, listas de materiales y operaciones versionadas o con trazabilidad de cambios.
- Planificación por fechas y disponibilidad; reservas, faltantes, abastecimiento y vínculos entre venta, compra y fabricación.
- Consumo previsto y real, producción parcial, orden pendiente por completar, lotes/series cuando corresponda, desperdicio y desmontaje controlado.
- Producto terminado, valoración y costo; distinguir costo previsto, real y desviaciones, documentando el método de valoración elegido.
- Pantallas: tablero de producción, órdenes, materiales, disponibilidad, trazabilidad de movimientos y costos.

Aceptación: producir una cantidad parcial y completar el resto; comprobar que materiales, existencias y producto terminado cuadren. Registrar desperdicio y verificar su impacto. Probar faltantes y restricciones de acceso entre empresas. No permitir cerrar el caso comercial con inventario negativo inadvertido ni con costos sin conciliar. Conservar evidencia de reversión/desmontaje y sus límites.

## OP02 — Órdenes de trabajo

Base observada: mrp.workorder, mrp.workcenter y registros de productividad existen en Community. La ausencia de una pantalla Enterprise no demuestra ausencia de esta capacidad.

- Centros, capacidad, calendario, operaciones, secuencia y dependencias.
- Responsables, tiempos previstos y reales; iniciar, pausar, reanudar y finalizar; motivos de detención y cantidades producidas.
- Avance por operación, carga de centros, retrasos, tiempos improductivos y desviación de costos.
- Relación visible con la orden de fabricación y el producto; permisos de operario y supervisor.

Aceptación: ejecutar una fabricación con al menos dos operaciones, registrar pausa y reanudación, terminar cada etapa y comprobar el cierre de fabricación. Probar dependencias, concurrencia sobre el mismo temporizador y ausencia de doble contabilización del tiempo. Medir el efecto del costo horario con datos sintéticos. No dar por disponible una vista de taller, calidad o mantenimiento sin revisar su implementación y licencia.

## OP03 — Importaciones comerciales

Base observada: stock_landed_costs, LGPL-3, depende de stock_account y purchase_stock. Cubre distribución de costos en valoración, no constituye por sí solo un expediente aduanero Ecuador.

- Expediente de importación con proveedor extranjero, moneda, tipo de cambio, términos comerciales, transporte, embarque, fechas y documentos.
- Compras y recepciones parciales; documentos aduaneros y referencias a declaración/liquidación, sin inventar autorizaciones de SENAE.
- Flete, seguro, agente y otros gastos identificados; separación de costos capitalizables, gastos y tributos recuperables según revisión contable vigente.
- Distribución verificable mediante el motor nativo: valor, cantidad, peso, volumen u otro criterio soportado. Evitar doble imputación de una factura de gasto.
- Trazabilidad expediente → compra → recepción → valoración → factura → asiento y cuenta por pagar. Diferencias de cambio y pagos parciales.
- Pantallas: expedientes, etapas y documentos, recepciones, hoja de costos y acceso al asiento de valoración.

Aceptación: compra extranjera con dos productos y recepción parcial; cargar gastos, revisar distribución, validar costo unitario y asiento. Probar gasto duplicado, recepción ajena, moneda distinta, documento faltante, corrección y mercancía parcialmente vendida antes del costo adicional. Determinar y verificar soporte FIFO/AVCO antes de habilitar el flujo. Clasificación tributaria y tratamiento aduanero deben contrastarse con fuentes oficiales vigentes antes de una operación real; no fijar tasas en este plan.

## OP04 — Nómina Ecuador

Base observada: SKNOMINA ofrece rutas externas de empleados, marcas, novedades y consulta de nómina; también tiene servicios y controlador de mapeo contable. No se ha acreditado que ese controlador esté disponible con el contrato externo requerido para Odoo.

- Vinculación explícita de organización, tenant SKNOMINA, instancia y empresa Odoo, con credencial propia y permisos mínimos.
- Empleados y centros de costo; novedades, ingresos, descuentos, aportes, beneficios, provisiones y liquidaciones calculados por SKNOMINA.
- Catálogo de conceptos y mapeo versionado a cuentas, terceros y distribución analítica, con vigencia por período.
- Cierre aprobado, asiento borrador balanceado, revisión y contabilización. Nómina por pagar, pagos y conciliación. Separar obligación laboral, provisión y desembolso.
- Referencia única por tenant, período, cierre y versión; reintentos sin duplicados, rechazos explicados, reapertura y reversión controlada.
- Pantallas: conexión, mapeos, períodos/cierres, novedades o enlaces a su fuente, bandeja de importación contable, errores y asientos.

Aceptación: período sintético con al menos dos empleados y centros, ingresos variables y descuentos; reconciliar total de nómina, provisiones, pasivos y asiento. Rechazar período sin cerrar, cuenta faltante, credencial ajena y asiento desequilibrado. Probar timeout, repetición, corrección de cierre y reversión sin sobrescribir un asiento publicado. Las tasas y cálculos laborales se validan en el motor y contra normativa vigente; no se replica hr_payroll Enterprise.

## Estado, entregas y exposición comercial

| Frente | Estado comprobado al aprobar la ampliación | Entrega siguiente | Cierre obligatorio |
|---|---|---|---|
| OP01 | Fuente Community y manifiestos inspeccionados | Configuración y ensayo de fabricación | Materiales, cantidades, costos y aislamiento demostrados |
| OP02 | Modelos de órdenes, centros y productividad inspeccionados | Operaciones secuenciadas y tiempos en demo | Ciclo por operario y supervisor probado |
| OP03 | Motor nativo de costos adicionales inspeccionado | Expediente y mapeo de costos de importación | Recepción, nacionalización documentada, valoración y contabilidad conciliadas |
| OP04 | Rutas externas y controlador contable de SKNOMINA inspeccionados | Contrato de cierre y mapeos | Asiento y pagos trazables, sin duplicados y con reversión |

La empresa Comercial Andina DEMO conserva datos ficticios y RUC vacío. La ampliación no conecta la demo al emisor SINKRONET. Los ejemplos laborales serán sintéticos; no se copian nóminas reales para ventas. La matriz de demostración comercial identificará qué ciclo está aprobado y cuál todavía no; instalar módulos no modifica ese estado automáticamente.

Cada frente requiere respaldo previo, pruebas en copia, instalación verificada, navegación visible, evidencia y guía corta de demostración. No basta una prueba de importación de módulos. La exposición en frontend corresponde a cada entrega funcional; este incremento de planificación no declara pantallas instaladas.

## Prompts ejecutables complementarios

- .github/prompts/ERPEC26-OP01-PRODUCCION.md
- .github/prompts/ERPEC26-OP02-ORDENES-TRABAJO.md
- .github/prompts/ERPEC26-OP03-IMPORTACIONES.md
- .github/prompts/ERPEC26-OP04-NOMINA.md

Estos prompts se ejecutan con la autorización vigente y complementan ERPEC26-06, ERPEC26-07 y la aceptación de ERPEC26-08. Las firmas históricas no se reescriben para simular implementación.
