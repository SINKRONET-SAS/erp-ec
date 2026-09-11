# Piloto Linux previo a Render — fase ERPEC26-04

Este incremento prepara y verifica contenedores en el Docker ya instalado. No instala otro servidor PostgreSQL en Windows ni utiliza las bases del piloto de los puertos 8169, 8170 y 8186. La prueba crea PostgreSQL 17 dentro de una red Docker nueva, sin publicar su puerto, con roles sin privilegios administrativos y datos sintéticos. Sus contenedores se detienen al finalizar; volúmenes y registros se conservan.

## Arranque e imágenes

El Dockerfile descarga exclusivamente Community oficial, commit `b1fd3a9eee5d575848ac649d2f5103537d8de7a4`. Python 3.12 y PostgreSQL 17 se fijan por digest; las dependencias Python se fijan en `deployment/linux/requirements-linux.lock`. Los paquetes Debian se obtienen del repositorio de la distribución: no se afirma reproducibilidad byte a byte ni auditoría de vulnerabilidades completa. Conservar el digest de la imagen validada para desplegar exactamente ese artefacto.

Desde la raíz del repositorio:

```powershell
docker build --build-arg ERPEC_PROFILE=customer -f deployment/linux/Dockerfile -t erpec-linux-customer:phase04 .
docker build --build-arg ERPEC_PROFILE=controller -f deployment/linux/Dockerfile -t erpec-linux-controller:phase04 .
.venv\Scripts\python.exe scripts/verify-linux.py --profile customer
.venv\Scripts\python.exe scripts/verify-linux.py --profile controller
```

El perfil cliente contiene `erpec_base` y `erpec_runtime`; el controlador añade catálogo, cola y PayPhone. Se separan físicamente los módulos propios. No hay credenciales de PayPhone ni Render en las imágenes. `.dockerignore` permite solamente fuentes explícitas; excluye credenciales, cachés, repositorio Git, respaldos y entornos virtuales.

El runtime acepta una base ya creada y perteneciente al usuario de su conexión. No crea bases ni roles ni requiere superusuario. La identidad de 32 caracteres hexadecimales debe coincidir entre base y filestore. La inicialización requiere base vacía y `ERPEC_BOOTSTRAP=1`; una inicialización interrumpida puede reintentarse con la misma identidad. Las pruebas de recuperación registradas distinguen la recreación terminada de un fallo durante instalación: esto último aún no tiene prueba de inyección de caída.

Al terminar la primera instalación, retirar `ERPEC_BOOTSTRAP` y `ODOO_ADMIN_PASSWORD` del entorno de despliegue. Los arranques posteriores no reinstalan módulos ni restablecen la contraseña. `ODOO_MASTER_PASSWORD` sigue siendo secreto requerido y no debe compartirse con el administrador del cliente. El archivo de configuración se genera en `/tmp` con permisos 0600. Odoo se ejecuta como UID 10001. El bloqueo del filestore impide ejecutar dos procesos sobre el mismo disco.

## Variables del servicio

| Variable | Valor o uso |
|---|---|
| `DATABASE_URL` | Conexión privada de la base asignada, sin parámetros adicionales |
| `DB_SSLMODE` | `require` por defecto; `disable` solo en la red Docker local del ensayo |
| `ERPEC_INSTANCE_ID` | Identidad inmutable de 32 caracteres hexadecimales |
| `ERPEC_COMPANY_NAME` | Nombre inicial de la organización |
| `ODOO_ADMIN_PASSWORD` | Contraseña inicial privada; no se vuelve a aplicar tras inicializar |
| `ODOO_MASTER_PASSWORD` | Clave privada del gestor de bases, cuya enumeración está deshabilitada |
| `ERPEC_BOOTSTRAP` | `1` únicamente para inicialización o recuperación explícita incompleta |
| `PORT` | Puerto HTTP del servicio; predeterminado 10000 |
| `ERPEC_PROFILE` | Argumento de construcción `customer` o `controller`; cambiarlo requiere otra imagen y otra base |

El disco se monta en `/var/data/odoo`: contiene filestore, sesiones e identidad. Si la base está inicializada y el disco pierde su identidad, el arranque falla en vez de crear archivos vacíos silenciosamente. La salud `/erpec/health` consulta la base real y su identidad; no usa la base administrativa `postgres`. El estado de la suite identifica la plataforma como Linux y expone la validación Render pendiente.

## Plantilla Render para revisar

`deployment/render.customer.example.yaml` es una plantilla de una instancia cliente, no el aprovisionador automático de la suite. No se ha aplicado. Región Virginia, capacidades de 2 GB para Odoo y 1 GB para PostgreSQL, y disco de 5 GB son valores provisionales para revisar con el titular, no una cotización ni un dimensionamiento productivo. Aplicar la plantilla crea recursos de pago. No se modifican los dominios ni se trasladan los datos locales con este archivo.

La base administrada es exclusiva del cliente, con acceso público bloqueado. El controlador necesitará su propio servicio, base, disco y secretos. El trabajador no podrá montar el disco de otro servicio. En Render debe verificarse que el UID 10001 pueda escribir en el punto de montaje, que el usuario de la base tenga los permisos esperados y que el acceso TLS funcione. Esas verificaciones no se deducen del ensayo Docker.

## Verificación y reversión

El verificador crea un contacto y un adjunto en filestore, cambia la contraseña y recrea el contenedor sobre el mismo disco. Comprueba autenticación, conservación de datos, separación de módulos, acceso PostgreSQL cruzado rechazado y fallos visibles ante disco ausente o identidad incorrecta. Guarda evidencia sin secretos en `.cache/linux/<ensayo>/result.json`; las credenciales y registros de ese directorio son privados. No realiza cargos ni llama a PayPhone o Render.

Para revertir el ensayo, detener únicamente los contenedores cuyo nombre y etiqueta correspondan al prefijo del informe. No borrar volúmenes. El runtime no modifica los pilotos Windows ni sus configuraciones; no hay migración de datos que revertir. Una futura actualización de módulos en producción requerirá respaldo coordinado de base y filestore y procedimiento específico de restauración; este arranque no actualiza automáticamente módulos existentes.

## Pendientes reales de fase 04

PayPhone sandbox ya fue confirmado con evidencia en `ERPEC26-04-payphone-local.json`. Continúan pendientes el adaptador Render de la cola (alta idempotente, conciliación, suspensión y reactivación), su exposición operativa, selección del espacio/región/recursos, permisos reales de PostgreSQL administrado, HTTPS y recuperación sobre Render. La instalación Linux del controlador no convierte al trabajador Windows en trabajador Render. No ejecutar `scripts/provision-worker.py` desde una instalación cloud.

Falta validar el generador PDF compatible con Odoo, dimensionamiento, seguridad de dependencias y respaldo/restauración conjunta antes de producción. El contenedor de este incremento no incluye wkhtmltopdf. Los comprobantes fiscales y conectores siguen pendientes de fases posteriores. No se cierra fase 04 ni se adelantan 05–08.

Referencias oficiales consultadas: [Docker en Render](https://render.com/docs/docker), [Blueprints](https://render.com/docs/blueprint-spec), [discos persistentes](https://render.com/docs/disks) y [PostgreSQL administrado](https://render.com/docs/postgresql-creating-connecting).
