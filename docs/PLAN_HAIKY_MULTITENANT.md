# Plan HAIKY — Aprovisionamiento multi-tenant compartido (reemplaza un proceso por cliente)

Autorizado por el titular el 15-09-2026, en respuesta a una preocupación de viabilidad financiera real: el diseño de aprovisionamiento entregado en OP07 (`scripts/provision-worker.py`) crea **un proceso Odoo dedicado y un puerto propio por cada cliente**. En Render (o cualquier nube), cada servicio activo se cobra de forma continua sin importar su uso — ese modelo pondría un costo fijo mensual por cliente que no escala. Este plan lo reemplaza por el patrón real de Odoo.sh/Odoo Online: **un servidor compartido, una base de datos por cliente**, sin proceso ni puerto dedicados. No declara la migración a Render completada; solo corrige la arquitectura antes de esa migración.

## Investigación previa (fuente: código real de Odoo 18, `.cache/odoo-community/odoo`)

- `db_filter` (`odoo/http.py`, función `db_filter`) construye un regex a partir del encabezado `Host`: `%d` es la primera etiqueta del host (antes del primer punto), `%h` es el host completo sin puerto. Con `dbfilter = ^erp_%d$`, una petición a `<instancia>.dominio.com` selecciona automáticamente la base `erp_<instancia>` — sin necesidad de fijar `-d`/`db_name`.
- La lista de bases se consulta en vivo contra PostgreSQL en cada petición (`odoo/service/db.py`, `list_dbs`) — **crear una base nueva no requiere reiniciar el servidor compartido**; la primera petición a esa base ya funciona.
- No existe un indicador nativo de "base suspendida" que `db_filter` respete. `list_dbs()` sí filtra por `datallowconn` de PostgreSQL — por eso `ALTER DATABASE ... WITH ALLOW_CONNECTIONS false/true` (ejecutado como superusuario del clúster) es el mecanismo correcto para suspender/reactivar un cliente sin tocar el proceso compartido ni borrar datos.
- `list_db = False` sigue siendo obligatorio en el servidor compartido: con `list_db = True` cualquier visitante podría listar los nombres de todas las bases de clientes.
- Ningún módulo del proyecto usaba `%d`/`%h` ni ruteo por subdominio antes de este incremento; `scripts/provision-worker.py`, `scripts/create-demo.py` y `scripts/windows-local.py` fijaban `dbfilter = ^{nombre}$` por proceso — exactamente el patrón que se reemplaza para clientes nuevos.

## Diseño

- **Servidor compartido nuevo** (`scripts/shared-tenant-server.py`, patrón `bootstrap`/`start` igual que `windows-local.py`): un único proceso Odoo en `.cache/windows/shared` (puerto 8200 en local), `dbfilter = ^erp_%d$`, `list_db = False`, sin `db_name` fijo, `addons_path` con el árbol completo del proyecto. Sirve **todas** las bases `erp_<instancia>` de clientes aprovisionados, sin importar cuántas existan ni cuál las vendió.
- **`scripts/provision-worker.py` simplificado**: ya no genera `odoo.conf` por cliente, no copia `addons/`, no arranca ni administra un proceso ni un puerto por cliente. El alta pasa a ser: crear rol+base PostgreSQL (igual que antes) → instalar `base,l10n_ec,erpec_base` con una llamada CLI de un solo uso contra el clúster compartido (`-d erp_<instancia> -i ... --stop-after-init --no-http`, sin archivo de configuración) → verificar salud contra el servidor compartido usando el subdominio del cliente. La suspensión/reactivación ya no detiene un proceso: alterna `ALLOW_CONNECTIONS` de la base en PostgreSQL.
- **`erpec.provision.endpoint`**: pasa de `http://127.0.0.1:{8180+id}` (puerto por cliente) a `http://{instancia}.localtest.me:8200` en local (`*.localtest.me` resuelve públicamente a 127.0.0.1, confirmado en este equipo; evita editar el archivo hosts de Windows). En producción sería `https://{instancia}.<dominio real>` detrás de Cloudflare, sin puerto — mismo esquema que ya usa Odoo.sh.
- **La instancia operadora (control comercial: planes, contratos, cola) sigue separada del servidor compartido de clientes.** `erpec_fundador` (OP07) y el piloto sintético `erpec_a` (usado solo por `scripts/verify-provision.py` para el ensayo automatizado, sin mezclarse con datos reales) siguen siendo procesos propios de un solo inquilino — venden y controlan el acceso, pero el cliente aprovisionado corre en el servidor compartido, no en la instancia del operador. Esto separa correctamente "quién vende" de "dónde corre el cliente", igual que una plataforma SaaS real.
- **No se migran instancias ya aprovisionadas** (los directorios `.cache/windows/instances/*` creados antes de este incremento, si existen) — quedan documentadas como parte del modelo anterior, sin tocarlas, hasta que se decida una migración explícita.

## Alcance de este incremento

Entrega y prueba el modelo completo **en local** (mismo patrón de todo el proyecto: sin Render todavía). Explícitamente fuera de alcance, documentado como pendiente:
- Adaptar el servidor compartido y el trabajador a Render (disco persistente, despliegue declarativo, límites de recursos reales) — ver docs/PRODUCCION_RENDER_CLOUDFLARE.md, que ya marcaba esto como pendiente antes de este plan.
- Registrar el servidor compartido o el trabajador como servicios de arranque automático de Windows.
- Migrar clientes ya aprovisionados con el modelo de un proceso por cliente.
- Límites de recursos por inquilino dentro del servidor compartido (un cliente con uso intensivo podría afectar a otros; el aislamiento de procesos se pierde a cambio del ahorro de costo — documentar el trade-off, no resolverlo aquí).

## Verificación de punta a punta

1. Pruebas de `erpec_provision` en base aislada nueva (sin cambios de contrato en el modelo, solo el cálculo de `endpoint`).
2. `scripts/verify-provision.py` adaptado: ya no verifica que un proceso se detenga al suspender (no existe un proceso por cliente); verifica en su lugar que la base deje de responder tras `ALLOW_CONNECTIONS false` y vuelva a responder tras reactivarla, y que dos clientes aprovisionados en el mismo servidor compartido no se mezclen (módulos del operador ausentes, acceso cruzado de roles rechazado — igual que antes).
3. Ensayo real: levantar el servidor compartido, aprovisionar un cliente sintético vía la cola de `erpec_a` (igual que hoy), y confirmar por HTTP real que `<instancia>.localtest.me:8200` sirve esa base específica — sin abrir un puerto ni un proceso nuevo.
4. Gobierno del proyecto: este plan, `CODEX_CONTEXT.md`, `AuditLock.json` y prompt de fase, mismo patrón que los incrementos anteriores.
