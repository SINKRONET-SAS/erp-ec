# Contexto vigente ERPEC26

Actualizado: 11-09-2026. Leer junto con RULES.md, docs/PLAN_HAIKY_ERPEC26.md y docs/PLAN_AMPLIACION_OPERATIVA.md. Este contexto orienta la continuidad; no acredita por sí mismo avances funcionales.

## Autorización y decisiones

- Continuar los prompts del plan y su ampliación OP01–OP04; commit y push autorizados. Repositorio privado SINKRONET-SAS/erp-ec, rama codex/erpec26-implementacion, base main.
- Prioridad actual: desarrollo local en Windows con Odoo Community. Render continúa aplazado; Cloudflare se reserva para el dominio futuro. No pedir Render como requisito para tareas locales independientes.
- PAYPHONE ya tuvo una transacción externa verificada mediante túnel: docs/evidencias/ERPEC26-04-payphone-local.json. No repetir la solicitud como si nunca se hubiera probado.
- SKNOMINA sí tiene API. El titular autorizó trasladar lógica propia al ERP para calcular localmente. La API sigue como alternativa y referencia de contraste; no se exige otro servicio para la demo.
- La demo usa parámetros laborales reales Ecuador 2026; empleados y operaciones son ficticios. Los parámetros artificiales de regresión no deben alimentar la semilla de demostración.
- Mantener una autoridad por empresa/año. No migrar empresas reales ni retirar SKNOMINA sin equivalencia integral y corte controlado. No modificar repositorios fuente ni incorporar código Enterprise sin permiso.

## Estado comprobado

- Fases históricas 00–03 completadas. Fase 04 parcial, con aprovisionamiento local probado y validación Render pendiente. Las fases 05–08 no se declaran cerradas por los incrementos locales autorizados.
- Demo: http://127.0.0.1:8369, base erpec_demo, usuario demo. RUC vacío. Mantener separadas demo, emisor y copias de pruebas; credenciales únicamente en almacenamiento privado local.
- Fabricación: parciales, órdenes pendientes, desperdicio/desmontaje, faltantes, lotes/series, planificación, dos operaciones dependientes, pausa con motivo, concurrencia y valoración. El costo nativo incluye ocupación del centro, incluidas pausas.
- Importaciones: expediente enlazado a compras, recepciones, documentos y costos nativos; FIFO/AVCO, duplicados, clasificación, divisas, mercancía vendida y ajuste inverso.
- Nómina nativa: parámetros reales 2026, novedades, aprobación, cierre, asiento idempotente, reversión y corrección; versión activa inmutable. Equivalencia con SKNOMINA solo parcial, no integral.
- Instalación y recuperación verificadas del incremento anterior: docs/evidencias/ERPEC26-OPERACIONES-LOCAL.json. Guía: docs/OPERACIONES_LOCALES_DEMO.md. Conservar evidencias históricas sin reescribirlas.
- Validaciones adicionales de este incremento: docs/evidencias/ERPEC26-OPERACIONES-ACEPTACION.json. Distinguir ensayos automatizados en copia de recorridos visuales en la demo. La revisión visual sigue pendiente: el inicio de sesión se registra exitoso en servidor, pero el control del navegador agota su espera sin completar el recorrido; causa aún sin resolver.

## Cola de ejecución

1. Completar aceptación visual de OP01/OP02 con operario y supervisor y OP03 con recepción de dos productos y distribución de gastos. La prueba automatizada de fabricación parcial con operaciones y roles está en el incremento de aceptación.
2. OP04: período con dos empleados y centros; completar pagos y conciliación de la nómina por pagar. La cuenta neta de la semilla actual es pasivo corriente y todavía no constituye un flujo de pago conciliado.
3. Ampliar equivalencia laboral: acumulados y retenciones previas, bases independientes, ausencias, liquidaciones, cargas y exenciones, otros regímenes; documentar diferencias y validar normativa antes de habilitar empresas reales.
4. Ensayo comercial transversal y recuperación acorde al incremento instalado. El script de recuperación actual comprueba el estado anterior a la primera instalación operativa; adaptar su expectativa antes de usar respaldos de actualizaciones posteriores.
5. Retomar gates externos cuando corresponda: Render, validación fiscal real y contrato externo de cierre/versionado para organizaciones que elijan integración. La existencia de API no acredita ese contrato específico.

## Verificación y entrega

- Ejecutar node scripts/verify-governance.cjs antes de modificar y al cerrar. Mantener cadena AuditLock y separar comprobación documental de pruebas funcionales.
- scripts/verify-operational-plan.py valida en copia aislada; --prepare crea otra copia con respaldo. Las pruebas deben poder convivir con la política real ya sembrada.
- scripts/verify-operational-runtime.py comprueba semillas, vistas y concurrencia. Instalar cambios funcionales mediante scripts/install-operational-demo.py solo después de validar; respaldar antes.
- En este incremento cambian pruebas y documentación, no modelos ni pantallas: no requiere reinstalación funcional de la demo. No atribuirle una nueva instalación o restauración.
