# Contexto vigente ERPEC26

Actualizado: 11-09-2026. Leer junto con RULES.md, docs/PLAN_HAIKY_ERPEC26.md y docs/PLAN_AMPLIACION_OPERATIVA.md. Este contexto orienta la continuidad; no acredita por sí mismo avances funcionales.

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
