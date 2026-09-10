# Aprovisionamiento Windows local

El controlador se instala solo en el piloto A del operador. Desde ERP EC → Contratos y derechos, un contrato vigente con ERP permite solicitar una instancia. Repetir la solicitud conserva el mismo identificador. La instancia del cliente recibe base, localización Ecuador y erpec_base; no recibe los módulos comerciales ni de infraestructura del operador.

El trabajador corre en el equipo operador, con acceso privado al PostgreSQL del piloto y a sus credenciales locales. No recibe comandos ni rutas arbitrarias por API. Genera una base, rol, filestore y contraseña por instancia, bajo .cache/windows/instances. Verifica autenticación en la base exacta antes de registrar el inicio. No publicar contraseñas ni el administrador de bases.

## Operación

- Instalar o actualizar el controlador: .venv/Scripts/python.exe scripts/install-provision.py.
- Procesar un trabajo pendiente: .venv/Scripts/python.exe scripts/provision-worker.py.
- Mantener el trabajador en ejecución: .venv/Scripts/python.exe scripts/provision-worker.py --watch. Se consulta la cola cada diez segundos; cerrar el proceso detiene el trabajador, sin borrar instancias.
- Repetir el ensayo sintético: .venv/Scripts/python.exe scripts/verify-provision.py.
- En Instancias y trabajos, seleccionar la compañía correspondiente en el menú superior. El ensayo se identifica como ERP EC ensayo de aprovisionamiento.

Los procesos del piloto y del trabajador no se han registrado como servicios automáticos al arrancar Windows. El estado disponible acredita la última comprobación del trabajador; no sustituye supervisión continua de disponibilidad. Un trabajador detenido no procesa nuevas altas, vencimientos o suspensiones. La instalación de servicios y monitorización requiere validar el destino operativo antes de publicación.

## Recuperación

La cola usa filas persistentes, bloqueo por organización, reservas de quince minutos y tokens por intento. Un token vencido no puede publicar resultados. Hay tres intentos por transición; tras el límite se requiere revisar el fallo y reintentar explícitamente. Un único trabajador físico por host toma un bloqueo local. Credenciales e identificación se guardan antes de crear la base para conservar el destino en los reintentos.

Suspender detiene únicamente el proceso cuyo PID y línea de ejecución corresponden a la instancia. Reactivar usa la misma base y archivos. No se eliminan datos por vencimiento o impago. La aplicación efectiva de límites internos de usuarios y consumos en cada producto, supervisión y medidas productivas deben verificarse antes de comercializar.

Reversión: conservar los archivos privados y respaldos, detener el trabajador, suspender desde el contrato y procesar la suspensión. Si el controlador no está disponible, verificar el PID y su configuración antes de detenerlo manualmente. Restaurar base y filestore en un destino nuevo; no borrar roles ni bases para revertir código.

## Pendientes que impiden cerrar la fase 04

El flujo probado parte de una autorización comercial sintética. No existe aún proveedor de pagos configurado ni un evento auténtico validado; tampoco hay servidor público/dominio/HTTPS definidos. No se debe sustituir esa evidencia por el retorno del navegador o por una marca manual de pagado.

Se necesitan el proveedor y ambiente de pruebas de cobro, y el servidor Windows/dominio destinado al servicio. Las credenciales se configurarán fuera de Git. Hasta superar esos criterios, fase 04 permanece parcial y fases 05–08 no comienzan por dependencia del plan. Para las fases fiscales posteriores también serán necesarios los entornos autorizados de SKNOMINA, Facturador y SRI de pruebas.
