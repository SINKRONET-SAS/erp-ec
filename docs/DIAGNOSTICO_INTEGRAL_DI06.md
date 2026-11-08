# Diagnóstico integral ERP EC — DI06

Corte: 06-11-2026. Método: revisión de código propio, manifiestos, controles y pruebas existentes, contraste oficial y pruebas nuevas identificadas en evidencias/DI06. No es dictamen de cumplimiento ni auditoría de saldos de una empresa. No se inspeccionaron datos operativos: PostgreSQL bloqueó la conexión del ejecutor con Windows 10013. Gobierno inicial: 192 eslabones válidos; repositorio inicialmente limpio.

## Matriz de hallazgos y respuesta

| ID / prioridad | Área y evidencia concreta | Hallazgo / riesgo | Respuesta y aceptación |
|---|---|---|---|
| DI06-01 / Alta | Nómina, `addons/erpec_payroll/settlement.py`, `service_days//365` | Años bisiestos pueden aumentar indebidamente los años de indemnización; tres años calendario desde 2024 incluyen 1096 días | Contar aniversarios calendario conservando fechas inclusivas y API; probar tres años exactos, fracción, 25 años y febrero; actas históricas no se recalculan |
| DI06-02 / Media | Enfermedad/IESS, `engine.py`, `models.py`, `acceptance_matrix_data.xml` | Oficio PGE 10097 citado con fecha de publicación secundaria 17-02-2025; original fechado 16-01-2025 | Corregir referencia. El 100 % tiene sustento en el pronunciamiento; no clasificarlo como error aritmético ni extenderlo sin análisis a todos los regímenes |
| DI06-03 / Alta | Pagos masivos, `erpec_treasury/bank_export.py` y ACL | Lotes y líneas bloquean write/unlink, pero ACL permite create y los modelos no exigen token interno al crear; riesgo de evidencia bancaria fabricada por RPC autorizado | Exigir misma autoridad interna al crear lote/línea; pruebas de rechazo RPC y generación legítima. Verificar con Odoo antes de despliegue |
| DI06-04 / Alta | Finiquitos, `exit_settlement.py`, `settlement.py`, `exit_views.xml` | Implementación explícitamente DEMO: no contabiliza, no retiene IR, no consulta anticipos; vacaciones manuales; base de décimos usa último sueldo y no historial variable | Diseñar integración con mayor, anticipos y beneficios históricos; casos con cambios salariales, comisiones, reservas anteriores y pagos acumulados. Responsable laboral/contable. Abierto |
| DI06-05 / Alta | Estados financieros; búsqueda en addons propios y `erpec_base/__manifest__.py` | No se identificó generador propio del juego completo SCVS ni prueba de amarre. No inferir ausencia de todo reporte Community: debe verificarse instalación y menú reales | Construir/verificar situación, resultado integral, flujo, patrimonio y notas con mapeos y comparativos; igualdad balance/mayor y puente de efectivo. Abierto |
| DI06-06 / Alta | Conciliación tributaria, `erpec_workspace/tax_plan.py`, `tax_intersection.py` | Planes fiscales operativos no equivalen a conciliación anual de utilidad contable a base imponible; no se identificó expediente anual integral | Diseñar ajustes con origen, norma, reversión, diferencias permanentes/temporarias y aprobación; amarrar renta corriente/diferida y declaración. Abierto |
| DI06-07 / Alta | Activos y depreciación, `erpec_assets/models.py` | Existe calendario lineal, residual, estimaciones, asientos y reversión; módulo declara no determinar deducibilidad. Falta acreditar puente fiscal y deterioro/componentes según régimen aplicable | Auxiliar fiscal separado del contable sin duplicar asientos; pruebas residual, altas/bajas, vida útil, cierres y diferencias fiscales. No usar máximos fiscales como vida útil automática. Abierto |
| DI06-08 / Alta | Inventarios/costos, `erpec_imports/models.py`, `erpec_manufacturing/models.py` | FIFO/AVCO y costos adicionales dependen de Community; expediente distribuye gastos a recepciones terminadas. Revisión del reparto entre recepciones parciales y costos futuros necesaria; no se demuestra error por existir entrega parcial | Escenarios compra-recepción-factura-costo-venta-devolución, inventario negativo, cierre, merma y capacidad normal; amarre capas/mayor/producción. Abierto |
| DI06-09 / Alta | Importaciones e impuestos, `erpec_imports/models.py` | Se exige embarque, referencia y adjunto; eso no verifica DAI, subpartida, valoración aduanera ni deducibilidad. Los gastos se clasifican manualmente | Comparar expediente con liquidación SENAE, separar recuperables/capitalizables/gasto, divisas y retenciones; controlar compañía de propiedades de valoración en sesión multiempresa. Abierto |
| DI06-10 / Alta | Cuentas por pagar/tesorería, `erpec_treasury/payroll.py`, `banking.py`, `bank_export.py` | Hay cuenta por empleado y conciliación exacta; archivo bancario de nómina no acredita pago. Guayaquil queda sin confirmar; formatos de otros bancos tienen fuentes históricas | Aceptación por banco, respuesta/rechazo/reenvío sin duplicación; demostrar pagos masivos de proveedores, aprobación y conciliación parcial/divisas. Abierto |
| DI06-11 / Alta | Facturación, retenciones, ATS/RDEP: `erpec_fiscal_sri`, `erpec_fiscal_native`, `erpec_fiscal_ats`, `erpec_payroll/annex_rdep.py` | Existen firma, XML, estados, secuencias y validadores; no se ejecutó transmisión ni validación DIMM en esta sesión. Ficha publicada 2.34 no prueba cobertura del ERP | Casos factura/NC/ND/retención/guía/liquidación, rechazo/reintento/autorización, anulación y amarre contable/anexos; validar catálogos vigentes y retenciones por fecha. Abierto |
| DI06-12 / Alta | Infraestructura y regresión | Suite integrada no inicia por denegación TCP; sin evidencia nueva de persistencia, concurrencia, ACL ni navegación instalada | Habilitar ejecución en entorno con acceso autorizado y repetir suite aislada; no marcar PASS por compilación o evidencia histórica |

## Integralidad de procesos

| Recorrido | Componentes identificados | Evidencia de cierre requerida |
|---|---|---|
| Venta a cobro | Ventas Community, factura, emisión SRI, cuenta por cobrar, pago | Autorización fiscal y conciliación bancaria enlazadas al mismo documento; reversión/NC coherente |
| Compra a pago | Compras, inventario, factura proveedor, retención, pago | Recepción/factura/retención/saldo/proveedor sin doble aplicación; antigüedad y pagos parciales |
| Importación a costo vendido | Expediente, gastos, landed costs, capas y mayor | Reparto a recepciones parciales, saldo de tránsito, inventario vendido y remanente conciliados |
| Nómina a banco/IESS/RDEP | Motor decimal, asientos, preparación de pagos, lotes, RDEP | Rol aprobado = obligación contable = pagos + saldo; aportes/planillas y acumulados RDEP conciliados |
| Salida a finiquito | Cálculo DEMO y acta PDF | Falta integrar deuda/pago, IR y beneficios anteriores; no se declara recorrido terminado |
| Cierre a estados/declaración | Mayor Community y configuraciones fiscales | Falta acreditar juego completo de estados, conciliación tributaria, impuesto diferido y aprobación |

## Fuentes oficiales consultadas y alcance

- SRI: [facturación electrónica](https://www.sri.gob.ec/facturacion-electronica), ficha off-line 2.34, julio 2026. Referencia técnica para contraste; sin homologación del software.
- IESS: [Ley de Seguridad Social](https://www.iess.gob.ec/documents/10162/33701/Ley_seguridad_social.pdf?version=1.3), arts. 106/107. La copia consultada es anterior al corte; contrastar reformas y régimen antes de producción.
- PGE: [extractos enero 2025](https://blogcasos.pge.gob.ec/images/2025/ROTATIVOS/pronunciamientos/Extracto_Pronunciamientos_Enero_2025.pdf), oficio 10097 del 16-01-2025, consulta de Secretaría Nacional de Planificación. Reconoce 100 % inicial para trabajador con derecho; no es una regla creada por el ERP. Aplicabilidad concreta y aportación se revisan separadamente.
- Ministerio del Trabajo: [SBU 2026](https://www.trabajo.gob.ec/wp-content/plugins/download-monitor/download.php?force=0&id=4933): USD 482 desde enero de 2026; coincide con `parameters_ec2026.py`. No valida por sí solo salario sectorial o jornada especial.
- Ministerio del Trabajo: [liquidación por despido](https://www.trabajo.gob.ec/8-en-caso-de-despido-intempestivo-que-rubros-se-deben-tomar-en-cuenta-al-momento-de-realizar-la-liquidacion-del-trabajador/), art. 188 y otros derechos. El conteo por aniversarios corrige la distorsión de dividir por 365; no resuelve bases variables o indemnizaciones especiales.
- SRI: [RLRTI publicado, reforma 22-05-2026](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/7169103f-f014-4bf2-bf24-fb29b34e8d07/REGLAMENTO_PARA_APLICACION_LEY_DE_REGIMEN_TRIBUTARIO_INTERNO.pdf). Depreciación/deducibilidad y conciliación requieren contraste artículo por artículo y reformas posteriores; no se certifica vigencia exhaustiva por una búsqueda.
- SENAE: [para importar](https://www.aduana.gob.ec/servicio-al-ciudadano/para-importar/). Tributos dependen de subpartida y base; preservar excepciones y no introducir una tasa global indiscriminada.
- SCVS: [guías y formatos financieros](https://appscvsmovil.supercias.gob.ec/guiasUsuarios/info_fin.zul). Incluye situación, resultados, flujo y patrimonio; parametrización y notas necesitan revisión profesional.

## Dictamen técnico limitado

Hay implementación sustancial, pero no evidencia suficiente para declarar cumplimiento integral o disponibilidad productiva de todos los procesos solicitados. La presencia de menús, pruebas históricas o gobierno firmado no demuestra autorización fiscal, pago bancario, liquidación legal correcta o estados financieros completos. Los hallazgos abiertos conservan responsable, acción y criterio de aceptación en el plan; las correcciones de esta pasada se informan por separado de esas ampliaciones.

## Resultado de ejecucion de esta pasada

DI06-01 corregido y probado en motor puro (nueve casos); DI06-02 corregido; DI06-03 implementado con pruebas ORM pendientes. Se actualizo la matriz derivada DI25 al detectar divergencia. 36 pruebas locales aprobadas; 276 Python y 74 XML analizados. No hay candidatos de mojibake en los archivos examinados. Fallo Bash y bloqueo PostgreSQL conservados en evidencia; no se acredita regresion integral ni UI instalada. Las ampliaciones DI06-04 a DI06-11 permanecen abiertas; DI06-12 impide su aceptacion funcional.

El titular autorizo iniciar PostgreSQL: consulta SCM denegada, conexion TCP 10013 e inicio pg_ctl rechazado por permiso de escritura del log. El log existente mostraba servidor listo y checkpoints recientes, por lo que no se declara detenido ni reiniciado con exito.

## DI06-13 — segunda pasada: aprobacion de calculos anteriores

Prioridad alta. En exit_settlement.py, la aprobacion anterior comparaba exclusivamente la huella de entradas y parametros. Un cambio del motor sin cambio de entradas no obligaba a recalcular un finiquito pendiente. Ademas, el limite DEMO se verificaba al calcular pero no otra vez al aprobar. Correccion 18.0.1.15.2: huella compartida de entradas/parametros/resultado, comparacion del resultado almacenado y revalidacion de politica/empresa antes de aprobar. No recalcula ni modifica actas emitidas. Se agregan tres pruebas ORM y dos puras; estas ultimas ejecutadas, ORM bloqueado por PostgreSQL.

## Segunda pasada renovada - 07-11-2026

CI 42299693024 del commit 7ea9a11145860cb8d9f227e5937712b651cace5f termino con cinco trabajos aprobados: gobierno, auditoria de dependencias, suite Linux y arranque customer/controller. Sustituye los bloqueos historicos de CI; no acredita aceptacion fiscal/bancaria ni implementacion de DI06-04 a DI06-11.

DI06-15 (alta, concreta DI06-09): las dos validaciones propias de importaciones leian cost_method y valuation del producto con la empresa activa, no la del expediente/costo. En una sesion con varias empresas podia rechazarse AVCO valido o admitirse configuracion no soportada. Correccion: with_company de la empresa del documento en ambos controles, manteniendo ACL y motor Community; version 18.0.1.0.2. Dos pruebas ORM verifican ambos sentidos al preparar y validar. La interfaz afectada ya existe: Preparar distribucion de costos y validacion del costo. No cambia formularios, datos historicos ni reglas fiscales.
