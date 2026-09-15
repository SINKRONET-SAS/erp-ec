# ERPEC26-OP08 — Aprovisionamiento multi-tenant compartido

Leer AGENTS.md, RULES.md, el contexto histórico, docs/PLAN_HAIKY_MULTITENANT.md, docs/ALCANCE_AUTOSERVICIO.md, docs/APROVISIONAMIENTO_WINDOWS.md y docs/PRODUCCION_RENDER_CLOUDFLARE.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Reemplazar el modelo de aprovisionamiento de OP07 (un proceso Odoo y un puerto dedicados por cliente) por el patrón real de las plataformas SaaS de Odoo: un servidor compartido sirviendo muchas bases de datos, ruteado por subdominio vía `db_filter` (`%d`), sin proceso ni puerto por cliente. La razón es financiera, no técnica: un servicio dedicado por cliente en Render se cobra de forma continua sin importar el uso, y pone en riesgo la viabilidad del ERP como producto.

No inventar mecanismos que Odoo no soporte nativamente. Confirmar contra el código fuente real de Odoo (`.cache/odoo-community/odoo`) cualquier comportamiento de `db_filter`, listado de bases o suspensión antes de programar sobre un supuesto no verificado. No declarar el modelo listo para Render: este incremento es local, igual que todo el proyecto hasta ahora.

## Criterios de aceptación

Cada incremento de esta fase debe: (1) no perder el aislamiento de datos entre inquilinos (un cliente no debe poder leer ni escribir la base de otro, ni ver los módulos comerciales del operador); (2) no requerir reiniciar el servidor compartido para dar de alta un cliente nuevo; (3) conservar los datos de un cliente suspendido (nunca borrar ni truncar); (4) probarse en base aislada y con un ensayo real por HTTP antes de cualquier instalación. Un incremento que no pueda cumplir (1)-(4) se limita a documentación, sin código.

## Verificación y cierre

Añadir o adaptar pruebas significativas y evidencia en docs/evidencias/. Instalar solo con respaldo previo. Commits con phase: ERPEC26-OP08 y task: ERPEC26-OP08.N. No cerrar la fase por un incremento: la adaptación a Render, el registro del servidor compartido como servicio automático, los límites de recursos por inquilino y la migración de clientes ya aprovisionados con el modelo anterior permanecen pendientes hasta autorización explícita.

## Primer incremento autorizado — 15-09-2026

El titular pidió el rediseño completo tras plantear la preocupación de costo. Se entrega: `scripts/shared-tenant-server.py` (servidor compartido nuevo, `dbfilter=^erp_%d$`, `list_db=False`); `scripts/provision-worker.py` simplificado (sin proceso ni puerto por cliente, alta por instalación CLI de un solo uso, suspensión/reactivación por `ALLOW_CONNECTIONS` de PostgreSQL); `erpec.provision.endpoint` con esquema de subdominio (`*.localtest.me` en local, sin editar el archivo hosts); `scripts/verify-provision.py` adaptado al nuevo modelo de suspensión. Detalle completo en docs/PLAN_HAIKY_MULTITENANT.md.
