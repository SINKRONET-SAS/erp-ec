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

Prioridad fiscal autorizada: continuar secuencias y autoridad durables, firma XAdES, envío/consulta SRI, RIDE y equivalencia integral según docs/FACTURACION_LOCAL.md; el XML previo no equivale a un emisor completo.

1. Completar aceptación visual de OP01/OP02 con operario y supervisor y OP03 con recepción de dos productos y distribución de gastos. La prueba automatizada de fabricación parcial con operaciones y roles está en el incremento de aceptación.
2. OP04: período con dos empleados y centros; completar pagos y conciliación de la nómina por pagar. La cuenta neta de la semilla actual es pasivo corriente y todavía no constituye un flujo de pago conciliado.
3. Ampliar equivalencia laboral: acumulados y retenciones previas, bases independientes, ausencias, liquidaciones, cargas y exenciones, otros regímenes; documentar diferencias y validar normativa antes de habilitar empresas reales.
4. Ensayo comercial transversal y recuperación acorde al incremento instalado. El script de recuperación actual comprueba el estado anterior a la primera instalación operativa; adaptar su expectativa antes de usar respaldos de actualizaciones posteriores.
5. Retomar gates externos cuando corresponda: Render, validación fiscal real y contrato externo de cierre/versionado para organizaciones que elijan integración. La existencia de API no acredita ese contrato específico.

## Verificación y entrega

- Ejecutar node scripts/verify-governance.cjs antes de modificar y al cerrar. Mantener cadena AuditLock y separar comprobación documental de pruebas funcionales.
- scripts/verify-operational-plan.py valida en copia aislada; --prepare crea otra copia con respaldo. Las pruebas deben poder convivir con la política real ya sembrada.
- scripts/verify-operational-runtime.py comprueba semillas, vistas y concurrencia. Instalar cambios funcionales mediante scripts/install-operational-demo.py solo después de validar; respaldar antes.
- Incremento fiscal nativo instalado con respaldo en demo: acción 581, pestaña Facturación local. Incluye modelos y pantallas; pruebas 14/14 y contraste 258 casos de módulo 11. No atribuirle restauración del respaldo ni emisión SRI, que no se ejecutaron.
- Servicios locales verificados: demo 8369, pilotos 8169/8170 y cliente 8186. No se inició el producto Facturador para preparar XML.

## Incidente de acceso resuelto — 11-09-2026

Usar scripts/start-demo.py --restart con el usuario Windows propietario de la carpeta de sesiones. El usuario restringido no puede escribirla: tempfile.mkstemp reintentaba tras PermissionError y el login no terminaba pese a contraseña correcta. No era un fallo de credenciales ni se corrigió ampliando permisos. El precontrol de escritura ahora se aplica antes de detener la demo en los instaladores de fabricación, operaciones y facturación y al preparar una copia operativa. Si falla, solicitar la ejecución con el usuario propietario; no arrancar directamente con Popen desde el entorno restringido. El diagnóstico temporal fue retirado al volver al arranque normal. Credenciales sin cambios, en el archivo privado ACCESO_DEMO.md.
