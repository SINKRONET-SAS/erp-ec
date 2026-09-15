# Producción: Render, Cloudflare y PAYPHONE

Decisión del usuario: Windows para desarrollo y piloto local; producción en Render con PostgreSQL y los servicios necesarios. PAYPHONE será el proveedor de pagos; el usuario creará una aplicación de prueba. El dominio se contratará posteriormente y se administrará mediante Cloudflare.

## Distribución prevista

- Render: Odoo Community en contenedor Linux, controlador de la suite y trabajador de aprovisionamiento separados. PostgreSQL administrado con credenciales y permisos mínimos por organización; verificar el esquema de aislamiento soportado antes de crear bases o roles. No asumir privilegios de superusuario del PostgreSQL local.
- Archivos Odoo: filestore persistente por instancia y respaldo coordinado con PostgreSQL. El sistema de archivos ordinario de Render es efímero. Un disco persistente conserva su contenido entre reinicios y despliegues; dimensionar y revisar sus restricciones antes de escalar.
- Cloudflare: DNS y, cuando se configure, proxy/protección del dominio hacia Render. La interfaz dinámica Odoo también se sirve desde Render. Cloudflare Pages solo sería una opción separada si posteriormente se construye una web estática; no está solicitada ni desplegada aquí.
- PAYPHONE: cobro del servicio, con confirmación verificable desde servidor. Facturador conserva su función de emisión fiscal. La selección del proveedor no demuestra que exista una aplicación, credencial o transacción validada.

Render proporciona una dirección onrender.com y terminación HTTPS. Se puede preparar el piloto público con esa dirección antes de comprar el dominio; la compatibilidad de la URL de retorno y confirmación debe verificarse con la aplicación PAYPHONE elegida. Cuando exista el dominio, comprobar DNS, certificados y conexión segura Cloudflare–Render.

## Segunda pasada de fase 04

1. Preparar imagen Linux reproducible desde Community oficial fijado, configuración de puertos/salud y despliegue declarativo. No reutilizar requirements-windows.txt ni rutas Windows sin revisar su compatibilidad.
2. Implementar un adaptador Render para la cola: altas idempotentes, estados de despliegue, conciliación, suspensión y reactivación que conserven datos. El trabajador Windows actual (OP08: modelo multi-tenant compartido, ver docs/PLAN_HAIKY_MULTITENANT.md) usa msvcrt y un clúster local para su propio candado de un solo trabajador por host, y ya no crea proceso ni puerto por cliente — pero sigue sin ser un trabajador Render listo para producción: falta adaptar el servidor compartido (hoy un solo proceso `workers=0`) y el ruteo por subdominio (hoy `*.localtest.me`) al dominio real detrás de Cloudflare.
3. Aislar controlador y clientes, secretos y permisos PostgreSQL. Diseñar almacenamiento de filestore y probar recuperación ante redeploy y reinicio. No asumir que un trabajador separado puede montar el mismo disco de otro servicio.
4. Configurar la aplicación PAYPHONE de prueba fuera de Git; implementar el flujo según su contrato oficial y probar confirmaciones, rechazos, duplicados y recuperación. Un retorno del navegador no concede servicio.
5. Verificar interfaz pública, HTTPS, salud, trabajos persistentes y separación de organizaciones sobre el despliegue real. Usar inicialmente la URL de Render; validar el dominio Cloudflare cuando esté contratado.
6. Registrar evidencia y cerrar fase 04 solo al superar los criterios. Mantener fases 05–08 pendientes de esa dependencia.

## Datos pendientes

Acceso al proyecto/espacio de Render y elección de región y recursos; aplicación PAYPHONE de prueba disponible y configuración privada de credenciales. No se han creado ni contratado recursos en esta actualización. El dominio propio pendiente no impide preparar ni probar mediante la URL de Render.

## Referencias oficiales consultadas

- [Servicios web y URL/HTTPS de Render](https://render.com/docs/web-services).
- [Discos persistentes de Render](https://render.com/docs/disks).
- [Trabajadores de Render](https://render.com/docs/background-workers).
- [DNS y proxy de Cloudflare](https://developers.cloudflare.com/fundamentals/concepts/how-cloudflare-works/).

Esta decisión actualiza el destino de producción. Las evidencias de fases anteriores siguen describiendo exclusivamente pruebas Windows locales; no se reinterpretan como pruebas Linux, Render o PAYPHONE.
