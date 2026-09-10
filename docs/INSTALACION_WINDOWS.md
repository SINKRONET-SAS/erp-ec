# Instalación Windows nativa

Requisitos: Python 3.12 x64, PostgreSQL 17 y Git. En la máquina de implementación existe Python 3.12.14 en el runtime local y PostgreSQL 17.11 en Program Files. El runtime del asistente no es requisito para otras máquinas: pasar la ruta de Python 3.12 instalado.

Desde la raíz, ejecutar PowerShell:

    ./scripts/setup-windows.ps1 -Python 'RUTA/AL/python.exe'
    .venv/Scripts/python.exe scripts/windows-local.py bootstrap
    .venv/Scripts/python.exe scripts/manage-odoo.py update
    .venv/Scripts/python.exe scripts/verify-windows.py

La creación inicial es solo para un directorio nuevo. Si ya existe .cache/windows/credentials.json, se detiene para evitar sobrescribir datos. Ante una inicialización incompleta, revisar logs antes de cualquier reparación. No ejecutar bootstrap sobre una instalación productiva.

Piloto A: http://127.0.0.1:8169 ; piloto B: http://127.0.0.1:8170 . Usuario admin; claves distintas en .cache/windows/credentials.json, que no se versiona. Conservar ese archivo privado. Cada proceso usa configuración en .cache/windows/a u b. PostgreSQL local escucha en 127.0.0.1:55487. No se usa el servicio ni las bases PostgreSQL existentes.

Los respaldos sintéticos de validación quedan en .cache/windows/backups, y su restauración se realiza en una nueva base restore_*. La prueba conserva la evidencia para inspección; no sustituye una política productiva de respaldos ni una copia consistente mientras otros usuarios escriben.

PDF: wkhtmltopdf no se detectó en la máquina. La generación PDF de reportes Odoo requiere instalar y validar el binario compatible antes de ofrecerla. No bloquea probar acceso, aislamiento y restauración del piloto; tampoco se declara PDF verificado.

La vista ERP EC → Estado de la suite expone que los conectores y la suscripción todavía están pendientes. No concede integraciones por instalar el módulo. Los módulos propios de este piloto se mantienen privados (Other proprietary); no se concede una licencia abierta nueva al código del titular.

Reversión: detener solo los procesos del piloto y conservar .cache/windows; volver al commit anterior para código. Nunca borrar bases o archivos para revertir una actualización; restaurar una copia en un destino nuevo y validar antes de sustituir una instancia.

Para detener los dos procesos Odoo del piloto: `.venv/Scripts/python.exe scripts/manage-odoo.py stop`. Para volver a iniciarlos: `.venv/Scripts/python.exe scripts/windows-local.py start`. La operación `update` también configura español de Ecuador y reinicia ambos procesos. PostgreSQL del piloto permanece activo; estos comandos no detienen servicios ajenos.

El catálogo y los contratos ya están disponibles en ERP EC. El controlador local del operador y sus límites de validación se describen en APROVISIONAMIENTO_WINDOWS.md. La implementación fiscal y el acceso público siguen pendientes.
