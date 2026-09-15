# Aprovisionamiento Windows local

**Actualizado 15-09-2026 (OP08): modelo multi-tenant compartido.** Cada cliente ya NO corre en un proceso ni puerto Odoo propio — eso se cobra de forma continua por servicio en Render sin importar el uso, y pone en riesgo la viabilidad financiera del ERP como producto. Ahora todos los clientes corren en un único **servidor compartido** (`scripts/shared-tenant-server.py`), ruteado por subdominio (`db_filter`); cada cliente solo aporta su propia base de datos. Ver docs/PLAN_HAIKY_MULTITENANT.md para el diseño completo y la investigación de `db_filter` contra el código fuente real de Odoo.

El controlador comercial (planes, contratos, cola) se instala en la instancia operadora — el piloto sintético A para ensayos, o `erpec_fundador` (la empresa real de SINKRONET) en el uso real. Desde ERP EC → Contratos y derechos, un contrato vigente con ERP permite solicitar una instancia. Repetir la solicitud conserva el mismo identificador. La instancia del cliente recibe base, localización Ecuador y erpec_base; no recibe los módulos comerciales ni de infraestructura del operador — aislamiento verificado por instalación de módulos por base, no por proceso separado.

El trabajador corre en el equipo operador, con acceso privado al PostgreSQL del clúster y a sus credenciales locales. No recibe comandos ni rutas arbitrarias por API. Crea la base de cada cliente bajo el **rol compartido `erp_tenants`** (no un rol nuevo por cliente: el servidor compartido solo puede abrir bases con un único `db_user`/`db_password` de proceso) y guarda solo la contraseña de aplicación Odoo del cliente bajo `.cache/windows/instances`. El aislamiento real entre clientes es la separación física de bases de PostgreSQL (una conexión a una base no puede leer otra) y la contraseña de aplicación propia de cada base — nunca una credencial de PostgreSQL por cliente. No publicar contraseñas ni el administrador de bases.

## Operación

- Inicializar y arrancar el servidor compartido (una sola vez, luego persiste): `.venv/Scripts/python.exe scripts/shared-tenant-server.py bootstrap` y luego `start`. Sirve `http://<instancia>.localtest.me:8200` en local (`*.localtest.me` resuelve públicamente a 127.0.0.1, sin editar el archivo hosts de Windows).
- Instalar o actualizar el controlador comercial en el piloto A: `.venv/Scripts/python.exe scripts/install-provision.py`.
- Procesar un trabajo pendiente contra la instancia operadora real: `.venv/Scripts/python.exe scripts/provision-worker.py` (usa `erpec_fundador` por defecto). Contra el piloto sintético de ensayo: agregar `--operator a`.
- Mantener el trabajador en ejecución: agregar `--watch` al comando anterior. Se consulta la cola cada diez segundos; cerrar el proceso detiene el trabajador, sin borrar instancias ni afectar al servidor compartido (que sigue sirviendo a los clientes ya listos).
- Repetir el ensayo sintético: `.venv/Scripts/python.exe scripts/verify-provision.py` (usa el piloto A y el servidor compartido; no toca `erpec_fundador`).
- En Instancias y trabajos, seleccionar la compañía correspondiente en el menú superior. El ensayo se identifica como ERP EC ensayo de aprovisionamiento.

Ni el servidor compartido ni el trabajador se han registrado como servicios automáticos al arrancar Windows. El estado disponible acredita la última comprobación del trabajador; no sustituye supervisión continua de disponibilidad. Un trabajador detenido no procesa nuevas altas, vencimientos o suspensiones, pero los clientes ya listos siguen respondiendo (el servidor compartido no depende del trabajador para servir peticiones). La instalación de servicios y monitorización requiere validar el destino operativo antes de publicación.

## Recuperación

La cola usa filas persistentes, bloqueo por organización, reservas de quince minutos y tokens por intento. Un token vencido no puede publicar resultados. Hay tres intentos por transición; tras el límite se requiere revisar el fallo y reintentar explícitamente. Un único trabajador físico por host toma un bloqueo local. La contraseña de aplicación del cliente se guarda antes de crear la base para conservar el destino en los reintentos.

Suspender ya no detiene ningún proceso (no existe uno por cliente): bloquea conexiones nuevas a la base exacta con `ALTER DATABASE ... WITH ALLOW_CONNECTIONS false`, ejecutado como el rol superusuario del clúster, y cierra las conexiones abiertas de esa base. Reactivar revierte el mismo flag y usa la misma base. No se eliminan datos por vencimiento o impago. La aplicación efectiva de límites internos de usuarios y consumos en cada producto, supervisión y medidas productivas deben verificarse antes de comercializar.

Reversión: conservar los archivos privados y respaldos, detener el trabajador, suspender desde el contrato y procesar la suspensión. El servidor compartido puede quedar corriendo sin riesgo mientras se investiga (sigue sirviendo a los clientes ya listos; no ejecuta código del trabajador). Restaurar base en un destino nuevo; no borrar el rol `erp_tenants` ni las bases de clientes para revertir código.

## Pendientes que impiden cerrar la fase 04

El destino de producción ya está definido: Render, con PostgreSQL administrado; PAYPHONE será el proveedor de pagos y Cloudflare administrará el dominio futuro. Windows permanece como piloto local.

La segunda pasada requiere adaptar el servidor compartido y el trabajador a Render (disco persistente, despliegue declarativo, mismo modelo de rol de PostgreSQL compartido y ruteo por subdominio, ahora con el dominio real detrás de Cloudflare en vez de `*.localtest.me`), configurar la aplicación PAYPHONE de prueba y verificar el despliegue y los pagos reales de prueba. Se puede comenzar con la URL HTTPS de Render antes de comprar el dominio. Véase PRODUCCION_RENDER_CLOUDFLARE.md y docs/PLAN_HAIKY_MULTITENANT.md. El ensayo local documentado no acredita estas nuevas validaciones.
