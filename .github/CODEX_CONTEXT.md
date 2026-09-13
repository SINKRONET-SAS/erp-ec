# Contexto vigente ERPEC26

Actualizado: 13-09-2026. Leer junto con RULES.md, docs/PLAN_HAIKY_ERPEC26.md y docs/PLAN_AMPLIACION_OPERATIVA.md. Este contexto orienta la continuidad; no acredita por sí mismo avances funcionales.

## Autorización y decisiones

- Continuar los prompts del plan y su ampliación OP01–OP04; commit y push autorizados. Repositorio privado SINKRONET-SAS/erp-ec, rama codex/erpec26-implementacion, base main.
- Prioridad actual: desarrollo local en Windows con Odoo Community. Render continúa aplazado; Cloudflare se reserva para el dominio futuro. No pedir Render como requisito para tareas locales independientes.
- PAYPHONE ya tuvo una transacción externa verificada mediante túnel: docs/evidencias/ERPEC26-04-payphone-local.json. No repetir la solicitud como si nunca se hubiera probado.
- SKNOMINA sí tiene API. El titular autorizó trasladar lógica propia al ERP para calcular localmente. La API sigue como alternativa y referencia de contraste; no se exige otro servicio para la demo.
- Facturación: el titular autorizó también trasladar lógica propia al ERP. Primer incremento instalado: preparación XML sin firma, con verificación XSD y módulo 11. Ver docs/FACTURACION_LOCAL.md y evidencia ERPEC26-FISCAL-NATIVO.json. No hay firma ni emisión SRI nativas todavía; conservar Facturador/API y una autoridad por comprobante.
- La demo usa parámetros laborales reales Ecuador 2026; empleados y operaciones son ficticios. Los parámetros artificiales de regresión no deben alimentar la semilla de demostración.
- Mantener una autoridad por empresa/año. No migrar empresas reales ni retirar SKNOMINA sin equivalencia integral y corte controlado. No modificar repositorios fuente ni incorporar código Enterprise sin permiso.

## Estado comprobado

- Fases históricas 00–03 completadas. Fase 04 parcial, con aprovisionamiento local probado y validación Render pendiente. Las fases 05–08 no se declaran cerradas por los incrementos locales autorizados.
- Demo: http://127.0.0.1:8369, base erpec_demo, usuario demo. RUC vacío. Mantener separadas demo, emisor y copias de pruebas; credenciales únicamente en almacenamiento privado local.
- Fabricación: parciales, órdenes pendientes, desperdicio/desmontaje, faltantes, lotes/series, planificación, dos operaciones dependientes, pausa con motivo, concurrencia y valoración. El costo nativo incluye ocupación del centro, incluidas pausas.
- Importaciones: expediente enlazado a compras, recepciones, documentos y costos nativos; FIFO/AVCO, duplicados, clasificación, divisas, mercancía vendida y ajuste inverso.
- Nómina nativa: parámetros reales 2026, novedades, aprobación, cierre, asiento idempotente, reversión y corrección; versión activa inmutable. Equivalencia con SKNOMINA solo parcial, no integral.
- Instalación y recuperación verificadas del incremento anterior: docs/evidencias/ERPEC26-OPERACIONES-LOCAL.json. Guía: docs/OPERACIONES_LOCALES_DEMO.md. Conservar evidencias históricas sin reescribirlas.
- Validaciones adicionales de este incremento: docs/evidencias/ERPEC26-OPERACIONES-ACEPTACION.json. Distinguir ensayos automatizados en copia de recorridos visuales en la demo. Acceso web corregido: la demo se ejecutaba con un usuario Windows sin escritura en data/sessions. Se verificó login completo y navegación a Facturación electrónica con el propietario de la carpeta. Sigue pendiente la aceptación visual integral de los ciclos operativos.

## Cola de ejecución

Prioridad actual: segunda pasada de estabilización y producto autorizada el 11/09/2026; véase docs/SEGUNDA_PASADA_PRODUCTO.md. Primero coordinar y aceptar los recorridos existentes. La ampliación fiscal queda detrás de esta revisión.

Prioridad fiscal posterior: continuar secuencias y autoridad durables, firma XAdES, envío/consulta SRI, RIDE y equivalencia integral según docs/FACTURACION_LOCAL.md; el XML previo no equivale a un emisor completo.

1. Completar aceptación visual de OP01/OP02 con operario y supervisor y OP03 con recepción de dos productos y distribución de gastos. La prueba automatizada de fabricación parcial con operaciones y roles está en el incremento de aceptación.
2. OP04: el incremento de Tesorería añade una preparación por empleado sobre cuenta por pagar conciliable, preservando el asiento de nómina original. Demo con dos empleados, uno liquidado y otro parcial; mantener pendiente la equivalencia laboral integral y los archivos bancarios.
3. Ampliar equivalencia laboral: acumulados y retenciones previas, bases independientes, ausencias, liquidaciones, cargas y exenciones, otros regímenes; documentar diferencias y validar normativa antes de habilitar empresas reales.
4. Continuar aceptación comercial por perfiles. La recuperación ya admite respaldos closeout con --expect-workspace y --expect-treasury; verifica saldos y saneamiento en copia aislada. Distinguir el estado previo contenido en el respaldo de la revisión instalada posteriormente.
5. Retomar gates externos cuando corresponda: Render, validación fiscal real y contrato externo de cierre/versionado para organizaciones que elijan integración. La existencia de API no acredita ese contrato específico.

## Verificación y entrega

- Ejecutar node scripts/verify-governance.cjs antes de modificar y al cerrar. Mantener cadena AuditLock y separar comprobación documental de pruebas funcionales.
- scripts/verify-operational-plan.py valida en copia aislada; --prepare crea otra copia con respaldo. Las pruebas deben poder convivir con la política real ya sembrada.
- scripts/verify-operational-runtime.py comprueba semillas, vistas y concurrencia. Instalar cambios funcionales mediante scripts/install-operational-demo.py solo después de validar; respaldar antes.
- Incremento fiscal nativo instalado con respaldo en demo: acción 581, pestaña Facturación local. Incluye modelos y pantallas; pruebas 14/14 y contraste 258 casos de módulo 11. No atribuirle restauración del respaldo ni emisión SRI, que no se ejecutaron.
- Servicios locales verificados: demo 8369, pilotos 8169/8170 y cliente 8186. No se inició el producto Facturador para preparar XML.

## Incidente de acceso resuelto — 11-09-2026

Usar scripts/start-demo.py --restart con el usuario Windows propietario de la carpeta de sesiones. El usuario restringido no puede escribirla: tempfile.mkstemp reintentaba tras PermissionError y el login no terminaba pese a contraseña correcta. No era un fallo de credenciales ni se corrigió ampliando permisos. El precontrol de escritura ahora se aplica antes de detener la demo en los instaladores de fabricación, operaciones y facturación y al preparar una copia operativa. Si falla, solicitar la ejecución con el usuario propietario; no arrancar directamente con Popen desde el entorno restringido. El diagnóstico temporal fue retirado al volver al arranque normal. Credenciales sin cambios, en el archivo privado ACCESO_DEMO.md.

## Segunda pasada de producto — primer incremento

- erpec_workspace instalado en la demo: centro de trabajo persistente por empresa, menú común y accesos con permisos existentes. Inicio de demo configurado; no asigna masivamente el inicio a otros usuarios.
- Solo la vista de inicio impide editar; su contexto no elimina crear/editar en las áreas. Acción de ventana estable conserva la vista al recargar. Nómina/importaciones con etiquetas y columnas revisadas.
- Cinco pruebas en copia aislada; diez accesos y vistas comprobados en la demo; revisión visual de inicio, recarga, ida/vuelta a nómina e importaciones y menú. Evidencia: docs/evidencias/ERPEC26-SEGUNDA-PASADA.json. No equivale a aceptación de los ciclos comerciales completos.
- Respaldo workspace-install-20260911-140812 recuperado en ec_recovery_107aee9b5a, con archivos coincidentes, centro de trabajo y asientos presentes; no reemplazó la demo. El respaldo contiene la primera versión del centro, anterior a los últimos ajustes visuales.
- Nuevo orden: SP01 coordinación (primer incremento validado), SP02 aceptación transversal, SP03 operación/calidad integral, SP04 puerta comercial. Continúan pendientes la emisión SRI completa y la equivalencia laboral; no declarar producto comercializable ni cerrar fases 04–08.

## SP02 — Compras: incremento de seguimiento y ensayo transversal

- Continúa la segunda pasada. La orden de compra muestra guía derivada de estados nativos, enlaces visibles a recepciones/facturas y distinción entre facturado, pagado y devuelto. Se oculta el botón alternativo sin cantidades facturables.
- Siete pruebas del centro/compras: comprador, bodega y contabilidad; parciales, dos facturas, dos pagos, devolución y nota de crédito; cuenta por pagar de la primera factura conciliada. No se probó el extracto bancario ni se declara aceptación fiscal.
- Hallazgo SP02-D01: documentos de la semilla inicial contienen retención ficticia y clasificación contable sin sanear. La factura de servicio P00001 usa cuenta 110307 y tipo tiquete. Aviso visible en los dos documentos históricos; no se reescribieron asientos publicados. Saneamiento posterior de estos dos documentos aplicado en el incremento de Tesorería descrito al final; no equivale a aceptación fiscal.
- Guía y límites: docs/SP02_COMPRAS.md. Evidencia: docs/evidencias/ERPEC26-SP02-COMPRAS.json. SP02 sigue en curso, con aceptación visual por roles y bancaria pendiente.

## Tesorería y saneamiento instalados — 11-09-2026

- erpec_treasury instalado con respaldo: preparación de pago por empleado, parciales y conciliación exacta con extractos. Demo julio 2026: dos empleados ficticios con política real, netos 1083,14 y 724,40; saldos 0 y 624,40. Sin transferencias externas. Diario de ensayo predeterminado comprobado en el formulario de pago.
- SP02-D01: saneamiento aplicado a los dos documentos históricos identificados. Retenciones artificiales revertidas, documentos compensados sin reescribir líneas originales y sustitutos publicados por 230 y 575 con IVA 15 %. La semilla nueva también fue corregida y probada en copia aislada con rollback. No extender este resultado a todos los documentos de la demo.
- Compras/Tesorería: 14 pruebas en copia aislada, incluidos proveedores con nota de crédito, anticipo, pagos parciales, conciliación y restricción a bodega. No equivalen a homologación bancaria ni aceptación visual integral por todos los perfiles.
- Nuevo alcance autorizado: archivos de pago de nómina **y proveedores** para Pichincha, Guayaquil, Produbanco, Pacífico, Rumiñahui, Internacional y Bolivariano. Compartir validación, versiones de perfiles y trazabilidad en Tesorería, conservando las diferencias de cada servicio. Ver docs/VALIDACION_ARCHIVOS_BANCARIOS.md.
- No copiar como aprobados los perfiles estáticos de SKNOMINA: se encontraron incompatibilidades con fichas oficiales. Todavía no hay generador bancario habilitado ni lotes homologados. Faltan fichas completas recuperables de cuatro entidades y confirmación/aceptación de cada servicio. El límite aparece en el inicio de la demo.
- Accesos de Tesorería: saldos de proveedores, pagos y anticipos y conciliación. Utilizan documentos y pagos nativos; el registro contable no transmite fondos.
- Recuperación aislada del respaldo closeout-install-20260911-160059: base ec_recovery_ff440557d6, archivos coincidentes, dos empleados y sus saldos, documentos saneados por 230/575. El respaldo precede a los accesos de proveedores; no afirmar que recupera esa revisión de interfaz.
- Firma fiscal: certificado recibido y comprobado localmente, RUC y datos de ubicación recibidos en almacenamiento privado. Pendientes régimen tributario, obligación contable y condición de contribuyente especial/agente de retención. La demo conserva RUC vacío. No pedir de nuevo certificado o identificación ya recibidos.
- Motor XAdES aislado en desarrollo: diez ensayos criptográficos con certificado sintético; sin uso del certificado real, integración UI, reserva durable, verificación independiente, confianza/revocación ni envío SRI. No está importado por el módulo ni instalado. No declarar firma fiscal operativa.

## Continuidad pendiente

Completar perfiles bancarios por banco y servicio, lotes inmutables y prevención de sobreasignación, validación en canales bancarios; conservar pendientes los gates fiscales, laborales, aceptación visual integral y calidad comercial de la segunda pasada. La documentación registra alcance y evidencia, no sustituye implementación ni aceptación.


## SP02 — Siguientes temas: ventas y coordinación operativa

- El usuario dejó pendiente la homologación bancaria y autorizó avanzar los demás temas. No volver a bloquear las tareas locales por esa dependencia.
- Nueva entrada de Cotizaciones y pedidos sin el filtro automático «Mis cotizaciones» ni filas ficticias de muestra; conserva las reglas nativas por vendedor y empresa. Seguimiento comercial en el formulario, con entregas, facturación, anticipo expreso, abonos y cobros diferenciados.
- Diecinueve pruebas de compras, ventas y Tesorería aprobadas en copia aislada: entrega parcial, dos facturas, cobros con extracto, devolución y abono, servicios, cancelación, cantidades no entregadas, permisos y protección de nómina. Evidencia: docs/evidencias/ERPEC26-SP02-VENTAS.json.
- Fallos por perfil corregidos: el responsable contable ahora puede crear/actualizar extractos mediante permisos específicos; el control interno de protección de nómina ya no requiere acceso a salarios para trabajar sobre asientos comerciales ajenos a nómina. No se concede acceso adicional a importes salariales.
- Reparación adicional del saneamiento: copia de líneas no conservaba vínculos comerciales. Se restauran únicamente las relaciones exactas de los documentos de la semilla, se coordinan sus impuestos con los pedidos y se comprueba que no cambie el asiento publicado. Una relación ajena o documentación adicional bloquea la reparación. No generalizarla a otros documentos.
- Producción: etiqueta Iniciar producción e indicaciones para motivo de pausa y secuencia; motivo disponible como columna opcional. Importaciones: consulta de costos y bloqueo visual de proveedor, moneda y compras cuando hay costos preparados.
- Guía: docs/SP02_VENTAS.md. Revisión visual de la sesión administradora; no declarar aceptación completa por operario/supervisor ni el expediente de dos productos y divisas. Permanecen pendientes los ciclos visuales integrales, equivalencia laboral, emisión fiscal y puerta comercial.

## OP05 — Anexos fiscales ATS y RDEP: primer incremento — 13-09-2026

- El titular pidió investigar y documentar el alcance de ATS y RDEP, con referencia adicional a lo ya construido en SINKRONET FACTURADOR y SKNOMINA, y luego ejecutar el resultado. Complemento nuevo de PLAN_AMPLIACION_OPERATIVA.md; prompt en .github/prompts/ERPEC26-OP05-ANEXOS-ATS-RDEP.md.
- Investigación contra los esquemas oficiales leídos directamente el mismo día (`ats.xsd`, `Esquema RDEP 2023.xsd`), no contra resúmenes de terceros; fichas técnicas en PDF quedaron sin leer por falta de OCR local. Alcance completo, brechas y fuentes en docs/ALCANCE_ATS_RDEP.md.
- Confirmado: el ATS existe dentro de Facturador pero no está expuesto en su API externa (docs/evidencias/ERPEC26-01.md); no se puede depender de esa integración. El trámite oficial de ambos anexos documenta software de escritorio (DIMM Formularios + plugin) y FTP/portal, no una API de envío.
- Implementado únicamente: agregador RDEP de solo lectura en erpec_payroll (`erpec.payroll.rdep`), que consolida por año fiscal los períodos de nómina ya contabilizados (gross, décimo tercero, décimo cuarto, fondo de reserva, IESS personal, impuesto retenido), más clasificación de empleador/seguridad social en la empresa y discapacidad/cargas/convenio en el empleado, con etiquetas tomadas literalmente de la documentación del esquema SRI. No genera XML ni anexo presentable.
- ATS queda completamente fuera de este incremento: falta el Catálogo ATS oficial (códigos de sustento y tipo de comprobante) y no se inventan. RDEP tampoco genera XML: el esquema exige participación de utilidades, intereses ganados, salario digno, otros ingresos gravados y deducciones desglosadas por categoría que el motor de nómina nativo no calcula todavía; completarlos habría presentado datos tributarios no verificados como reales.
- 27/27 pruebas aprobadas (8 nuevas) en erpec_manufacturing + erpec_imports + erpec_payroll; sin regresiones. Instalado en la demo con respaldo (operational-install-20260913-140837) y verificado en vivo consolidando 3 empleados sintéticos de 2026, sin dejar registros de negocio. Evidencia: docs/evidencias/ERPEC26-OP05-ANEXOS-ATS-RDEP.json.
- No se declara homologación, presentación ante el SRI ni equivalencia con Facturador/SKNOMINA. Continúa pendiente el resto de OP05: catálogo ATS, campos RDEP restantes, generación y validación XML contra los esquemas oficiales, y confirmación del canal de presentación.

## OP05 — Segundo incremento: catálogo ATS y motor RDEP ampliado — 13-09-2026

- El titular pidió cerrar dos brechas concretas: conseguir el Catálogo ATS y ampliar el motor de nómina para cubrir todos los campos RDEP faltantes, sin duplicar el cálculo.
- Catálogo ATS oficial descargado (archivo .xls del portal Alfresco de sri.gob.ec), transcrito en `addons/erpec_fiscal_native/ats_catalog.py` (meses, identificación, 39 tipos de comprobante, 16 códigos de sustento con su cruce válido, 236 países) y verificado con 6 pruebas nuevas. Resuelve el catálogo para codSustento/tipoComprobante/tpIdProv/tpIdCliente; la generación de compras/ventas del ATS sigue pendiente porque falta modelar qué sustento corresponde a cada documento, dato que hoy no existe en el ERP.
- Motor de nómina (`erpec_payroll/engine.py`) ampliado sin duplicar el cálculo: expone `annual_tax_caused`, `personal_expense_rebate` y `annual_tax_after_rebate`, valores que ya calculaba internamente. `annex_rdep.py` añade 14 campos de captura en `erpec.payroll.line` y 5 en `hr.employee` para lo que el motor no puede calcular por sí mismo (utilidades, salario digno, ingresos/aportes/impuesto con otros empleadores, gastos personales desglosados con los topes del Instructivo Formulario 107 del SRI).
- El agregador RDEP ahora genera y valida una vista previa XML completa contra el esquema oficial `Esquema_RDEP_2023.xsd` (copiado en el módulo). Dos campos del esquema (`deducEducartcult`, `benGalpg`) no tienen documentación en ninguna fuente primaria revisada; se envían con un valor neutro marcado explícitamente en el código, no con datos inventados.
- 33/33 pruebas de erpec_manufacturing+erpec_imports+erpec_payroll (6 nuevas) y 20/20 de erpec_fiscal_native+erpec_fiscal_connector (6 nuevas) aprobadas; sin regresiones. Instalado en demo con respaldo (operational-install-20260913-144953). Verificado en vivo: la generación de XML se bloquea correctamente porque la demo mantiene RUC vacío, sin usar un RUC inventado; se probó con éxito en una transacción de prueba con RUC sintético revertida al finalizar.
- Evidencia: docs/evidencias/ERPEC26-OP05-ANEXOS-ATS-RDEP.json (actualizada). Sigue pendiente: sustento tributario por documento para ATS, confirmación narrativa de `deducEducartcult`/`benGalpg`/`intGrabGen`, y el canal de presentación ante el SRI.

## OP05 — Verificación de deducEducartcult y benGalpg — 13-09-2026

- El titular pidió verificar dos hipótesis: que `deducEducartcult` fuera "Educación, Arte y Cultura" y que `benGalpg` fuera un beneficio especial de Galápagos.
- `deducEducartcult` confirmado por fuentes tributarias independientes: el SRI agrupa gastos personales en 6 categorías desde la reforma de 2023, incluida "educación, arte y cultura" como una sola. Corregido en `annex_rdep.py`: `expense_education` + `expense_art_culture` se suman en `deducEducartcult` (los campos legados `deducEduca`/`deducArtycult` ya no se emiten); el tope 0.325× aplica a la suma.
- `benGalpg`: indicio fuerte (no confirmación completa) de que corresponde al Régimen Especial de Galápagos (LOREG) — la Resolución NAC-DGERCGC16-00000443 (2016) creó una tabla diferenciada de gastos personales para ese régimen, derogada por la NAC-DGERCGC21-00000049 (2021). El esquema es de 2023 (posterior a la derogatoria); no se confirmó si el campo conserva efecto vigente. Corregido: la ayuda en pantalla cita ambas resoluciones y el límite de confianza en vez de decir "sin documentación"; se mantiene "NO" por defecto.
- Detalle completo en docs/ALCANCE_ATS_RDEP.md ("Verificación — 13-09-2026"). 35/35 pruebas aprobadas (2 nuevas: suma y tope combinado de educación+arte/cultura con validación de esquema).

## OP05 — Corrección: tope único de gastos personales (no por categoría); benGalpg confirmado vigente 2026 — 13-09-2026

- El titular aportó el mecanismo real 2026 (18% sobre canasta básica de enero según cargas, factor IPCEG 1,803 en Galápagos), contradiciendo el tope por categoría (0.325x/1.3x) implementado antes. Se verificó contra el Boletín NAC-COM-26-006 del SRI (06-02-2026, PDF oficial leído con éxito, no escaneado) antes de corregir.
- Confirmado por fuente primaria: desde la reforma de 2023 NO hay tope por categoría de gasto personal; hay un tope único anual total según cargas familiares (7 a 20 canastas básicas familiares), y el factor IPCEG 1.803 en Galápagos es vigente y actual para 2026 (no la resolución derogada de 2016-2021 encontrada antes). El Instructivo Formulario 107 usado como fuente secundaria resultó ser anterior a la reforma de 2023 y describía un mecanismo ya derogado.
- `addons/erpec_payroll/annex_rdep.py` corregido: nueva `_personal_expense_cap()` reutiliza `parameters['expense_limit']` (ya usado por el motor mensual, coincide exactamente con 7×821.80 para 2026) escalado por cargas familiares y Galápagos, sin duplicarlo; la validación ahora compara la suma de las 7 categorías contra ese tope único.
- Brecha nueva documentada, no corregida: el motor mensual (`engine.calculate()`) sigue sin escalar `expense_limit` por cargas familiares del empleado ni por Galápagos — afecta el cálculo real de retención mensual, no solo el anexo RDEP; queda como tarea propia priorizada.
- 36/36 pruebas aprobadas (3 nuevas). Detalle completo en docs/ALCANCE_ATS_RDEP.md ("Corrección — tercera parte").

## Plan UI/UX autorizado — 13-09-2026

El titular autoriza crear y ejecutar docs/PLAN_HAIKY_UI_UX.md y prompts ERPEC26-UIUX-00 a 03, corregir regresiones, cerrar gobierno, commit y push. Alcance: confirmación encontrable, ventas en ancho reducido, inicio y Áreas. Diagnóstico confirmado: Odoo mueve Confirmar al engranaje en pantallas pequeñas; no era una ausencia funcional. UIUX-00 es gobierno y diagnóstico; las pruebas e instalación de UIUX-01/02 aún no se han ejecutado. El cierre OP05.3 independiente resolvió la divergencia inicial de gobierno. Conservar estados históricos y límites fiscales/laborales/bancarios.

## UI/UX — ejecución y cierre técnico — 13-09-2026

- Plan docs/PLAN_HAIKY_UI_UX.md y prompts ERPEC26-UIUX-00 a 03 ejecutados. Confirmar pedido expuesto junto a la guía mediante operación nativa; tarjetas móviles y listado de escritorio; inicio compacto; submenús por área y etiquetas accesibles.
- 21/21 pruebas de regresión y 9/9 del módulo final. Instalación exclusiva de erpec_workspace con respaldo workspace-install-20260913-152951; hashes instalados coincidentes, diez accesos y vínculos comerciales comprobados. Capturas 375/562/1280 px, búsqueda móvil y teclado. Sin errores observados en la consulta final de consola.
- Corregidos durante la aceptación el selector/prioridad CSS del inicio, la flecha duplicada y los nombres accesibles de formularios/listados. Evidencias: docs/evidencias/ERPEC26-UIUX-02.json e informe ERPEC26-UIUX-INFORME.md. No se confirmó ni emitió ningún documento de negocio durante la revisión visual.
- Cierre técnico en AuditLock.uiUx; estados históricos conservados. Commit y push se comprueban tras cerrar los artefactos. No incluye RDEP concurrente, restauración, conformidad WCAG ni aceptación visual integral de todos los perfiles/ciclos.

## OP05 — Corrección del hallazgo colateral: motor mensual escala el tope por cargas y Galápagos — 13-09-2026

- El titular pidió corregir la brecha documentada en el incremento anterior: `erpec_payroll.engine.calculate()` seguía usando el tope de 0 cargas sin escalar, afectando la retención mensual real (no solo el anexo RDEP).
- `DEPENDENTS_BASKETS`/`GALAPAGOS_IPCEG_FACTOR` y `personal_expense_cap()` se movieron a `erpec_payroll/engine.py` (única implementación); `annex_rdep.py` ahora reutiliza esa función en vez de mantener su propia copia de las constantes.
- `erpec.payroll.line._inputs()` (exclusivo de `calculate()`, nunca de la duplicación de líneas en `action_correct()`) agrega `dependents_count`/`galapagos` leídos de `line.employee_id`; `_copy_inputs()` no se tocó para no romper `action_correct()`, que pasa esos valores directo a `create()`.
- Compatible con lo existente: valores por defecto (0 cargas, fuera de Galápagos) reproducen exactamente el comportamiento anterior; ninguna prueba preexistente cambió su resultado esperado.
- 40/40 pruebas aprobadas (4 nuevas: función aislada, cálculo mensual real con menos impuesto a mayor tope, `action_correct()` sigue funcionando). Instalado y verificado en demo con respaldo. Detalle completo en docs/ALCANCE_ATS_RDEP.md ("Corrección del hallazgo colateral").

## SP02 — Aceptación visual de fabricación parcial — 13-09-2026

- Retomado escenario ficticio en ec_operational_7a74b3c051: operario pausa/reanuda y finaliza dos etapas; supervisor registra parcial y completa la segunda unidad. Órdenes WH/MO/00013-001 y -002 terminadas; 4 componentes consumidos, 2 productos terminados, 4 operaciones terminadas, ningún intervalo abierto.
- La copia antigua necesitó respaldo y actualización de esquema antes del ingreso. Arranque de aceptación admite --directory y reutiliza el precontrol de permisos de sesiones; no altera el selector compartido de pruebas. Demo principal sin cambios de negocio.
- Evidencia y límites en docs/evidencias/ERPEC26-SP02-PRODUCCION-VISUAL.json y docs/SP02_EXPERIENCIA_Y_ACEPTACION.md. El contador heredado desde el 11/09 invalida su uso como costo representativo; no se reajustó la historia. Pendientes venta/valoración representativa, reversión visual, importaciones de dos productos y demás recorridos SP02. No cierra SP02 ni la puerta comercial.

## OP06 — Cumplimiento legal Ecuador: primer incremento — 13-09-2026

- El titular pidió, en respuesta a la necesidad de garantizar cumplimiento legal (Tributario, Facturación Electrónica, ATS, RDEP, Laboral, Protección de Datos, envíos por email), generar y desplegar un plan con su gobierno, ejecutarlo, verificar regresiones y cerrar. Complemento nuevo, independiente de OP01-05 y del plan de impuestos TX00-02 de otra sesión concurrente. Plan: docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md. Prompt: .github/prompts/ERPEC26-OP06-CUMPLIMIENTO-LEGAL-EC.md.
- Tributario, Facturación Electrónica, ATS, RDEP y Laboral: sin código nuevo en este incremento; el plan remite a la documentación ya existente (docs/FACTURACION_LOCAL.md, docs/ALCANCE_ATS_RDEP.md, docs/OPERACIONES_LOCALES_DEMO.md) en vez de duplicarla.
- Protección de Datos (LOPDP) y envíos por email: dominios sin ningún trabajo previo en el proyecto. Investigados contra fuente oficial (Registro Oficial Suplemento 459 del 26-05-2021 para la LOPDP; spdp.gob.ec como regulador operativo; Ley 67 de Comercio Electrónico para el mecanismo de exclusión de correo). Varios plazos/umbrales citados en fuentes secundarias (umbral del RAT, plazos de notificación de brechas) quedan marcados explícitamente como no verificados contra el texto primario.
- Primer incremento de código: módulo `erpec_data_protection` — Registro de Actividades de Tratamiento (RAT, `erpec.data.processing.activity`) y campo de exclusión de correo comercial en `res.partner`. No declara cumplimiento legal ni homologación.
- Corregido durante la prueba: el grupo nuevo no implicaba `base.group_user` (bloqueaba el chatter de `mail.thread`) ni `base.group_partner_manager` (bloqueaba escribir `res.partner`, que por diseño nativo de Odoo solo da lectura a `group_user`). 6/6 pruebas aprobadas en base aislada limpia (no la copia operativa compartida, para no mezclar con el trabajo concurrente de otra sesión sobre `erpec_workspace`).
- Instalación en demo completada el mismo día, tras confirmar que la otra sesión ya había comiteado y estabilizado `erpec.tax.plan` (tabla, access.csv y manifest correctos; demo respondiendo 200 antes de instalar). El `addons_path` de la demo es una copia aislada (`.cache/windows/demo/addons`), no el árbol de desarrollo en vivo, lo que ya la protegía de ediciones concurrentes sin comitear. Respaldo `data-protection-install-20260913-171822`; vista del RAT compila y el botón de exclusión de correo aparece en el formulario de contacto; confirmado además que el admin de la demo NO tiene el grupo por defecto (control de acceso correcto), verificado con una concesión temporal del grupo que se retiró de inmediato. Sin registros de negocio creados.
- No cierra OP06: Tributario/Facturación/ATS/RDEP/Laboral siguen con sus brechas ya documentadas; Protección de Datos solo tiene el RAT (faltan derechos del titular, notificación de brechas, RNPD); envíos por email sigue sin envío real habilitado.


## SP02 y TX — Importaciones, valoración y plan de impuestos — 13-09-2026

- Importación visual por comprador, bodega y contabilidad completada: dos productos, 300 EUR, dos recepciones, flete 30 EUR/34,78 USD y ajuste inverso. Valoración 347,76 → 382,54 → 347,76 USD; asientos balanceados.
- Fabricación nueva WH/MO/00059 con dos intervalos cerrados de esta sesión: materiales 20,00 + trabajo 0,63 = 20,63 USD para dos unidades. Entrega/devolución automatizada por 10,32 USD, revertida al terminar. No se alteró el contador histórico.
- Plan de impuestos instalado: consultas por empresa, artículo, tercero y operación; posiciones fiscales y motor nativos; cuentas de factura/devolución y enlace inverso cuenta→catálogo. No duplica tasas ni valida tratamientos tributarios reales. La consulta guardada es configuración vigente, no una regla paralela ni historial fiscal.
- 32/32 pruebas aprobadas; 40 archivos instalados coincidentes; once accesos comprobados. Respaldo imports-ui-install-20260913-165519 recuperado en ec_recovery_746b09dd18, anterior al cambio, con archivos y Tesorería coincidentes.
- Plan: docs/PLAN_HAIKY_IMPUESTOS.md. Guía: docs/SP02_IMPORTACIONES_VALORACION_IMPUESTOS.md. Evidencia: docs/evidencias/ERPEC26-SP02-IMPORTACIONES-VALORACION.json. TX00–TX02 cubren este incremento técnico. SP02 y las fases históricas continúan abiertas según sus límites.

## OP06 — Segunda pasada sobre Protección de Datos: artículos LOPDP confirmados contra texto primario — 13-09-2026

- El titular pidió una segunda pasada del plan de cumplimiento legal para cerrar brechas, con recordatorio explícito de verificar vigencia 2026. Solo investigación/documentación en este incremento; sin cambios de código ni al módulo `erpec_data_protection`.
- Los tres puntos marcados "no verificado contra fuente primaria" en el incremento anterior quedaron confirmados por lectura directa del texto completo (PDF extraíble, no escaneado; Lexis S.A., cotejado con Registro Oficial Suplemento 459 del 26-05-2021 y Suplemento 435 del 13-11-2023): derechos del titular en Arts. 11-24 LOPDP (acceso/rectificación/eliminación/oposición: 15 días cada uno; portabilidad Art.17; irrenunciabilidad Art.24), notificación de brechas en Arts. 43 (5 días responsable→SPDP, 2 días encargado→responsable) y 46 (3 días al titular si hay riesgo, 3 excepciones), y el umbral del RAT en el Reglamento General Art.38 (100+ trabajadores) con la aclaración del Art.39 (también obligatorio bajo 100 si hay riesgo, tratamiento no ocasional o datos sensibles).
- Pendiente declarado explícitamente: confirmar que ninguna reforma 2022-2026 a la LOPDP ni reemplazo 2024-2026 del Reglamento alteró estos artículos (verificación de vigencia en curso al cierre de este incremento); formato/canal exacto de la SPDP para el RAT y la notificación de brechas; si la SPDP sanciona activamente hoy. El procedimiento operativo de derechos del titular y de notificación de brechas (plantillas, canal, responsable) sigue sin implementarse en código — requeriría un incremento OP06.3 con autorización separada.
- Detalle completo con cita literal de cada artículo: docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md (sección LEGAL-06) y docs/evidencias/ERPEC26-OP06-CUMPLIMIENTO-LEGAL-EC.json (bloque `secondPass`).
- Verificación de vigencia 2026 (segunda consulta, confianza media, fuentes secundarias consistentes): no se encontró reforma a la LOPDP (2022-2026) ni reemplazo del Reglamento General (2024-2026); la SPDP emite normas subordinadas sin tocar esos artículos y **sanciona activamente a privados** (LIGAPRO USD 259.644,01 y Federación Ecuatoriana de Fútbol USD 194.856,16, diciembre 2025, por consentimiento inválido). Existe un proyecto de norma técnica de notificación de brechas (borrador, mayo 2026) aún no finalizado. Detalle en el bloque `secondPass.staleness2026Check` del JSON de evidencia.
