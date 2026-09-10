# ERPEC26-02 — Windows nativo verificado

Odoo Community 18 oficial ejecutándose con Python 3.12.14 y PostgreSQL 17.11. Dos procesos HTTP locales independientes, dos roles PostgreSQL sin privilegios de administración y bases y filestores separados. No se ha incorporado código Enterprise.

## Evidencia ejecutada

- Instalación de base, l10n_ec y módulo propio erpec_base; plan contable Ecuador cargado en ambas compañías.
- Prueba real de rechazo de conexión PostgreSQL de un rol a la base de la otra organización.
- Alta de contacto sintético y adjunto en A: no visibles en B.
- Respaldo pg_dump y restauración en una base nueva; registro recuperado y SHA256 del archivo restaurado coincidente. El nombre de la última base restaurada figura en ERPEC26-02-validacion.json.
- Navegador real automatizado: inicio de sesión, vista ERP EC, fila de la compañía y captura después de cargar los datos. Interfaz en español de Ecuador y sin errores JavaScript capturados. Captura local ignorada: .cache/windows/odoo-desktop.png.
- Actualización del módulo y repetición de aislamiento/restauración después de configurar el idioma.

## Alcance y límites

Piloto local sintético, accesible solamente desde esta máquina. No es publicación en la nube, servicio automático de Windows ni homologación fiscal. No se han probado carga productiva, PDF, pagos ni conexiones reales a SKNOMINA/Facturador. El aviso de instalación sobre la descripción reStructuredText de un módulo upstream no impidió instalar ni abrir la aplicación; no se atribuye una corrección al núcleo ajeno.

Los conectores pendientes se indican en la pantalla Estado de la suite. Instalar Community no concede derechos comerciales ni activa APIs de otros productos.

## Reproducción y reversión

Seguir docs/INSTALACION_WINDOWS.md. scripts/verify-windows.py comprueba servicios reales y conserva respaldos y bases de restauración sintéticos para revisión. scripts/manage-odoo.py detiene únicamente los PIDs cuya línea de ejecución corresponde a los archivos de configuración de este piloto.

Conservar .cache/windows y las credenciales antes de cambiar versiones. Restaurar en una base y filestore nuevos; no reemplazar ni eliminar la instalación anterior sin comprobar el resultado. No se tocaron bases PostgreSQL ajenas ni los productos fuente.
