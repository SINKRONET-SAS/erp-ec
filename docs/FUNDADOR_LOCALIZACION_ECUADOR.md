# Localización Ecuador en el fundador

Acceso local: http://127.0.0.1:8199/web/login, usuario `fundador`, con su contraseña existente. La compañía operadora mantiene Ecuador, USD, plan contable `ec`, idioma `es_EC` y zona `America/Guayaquil`.

## Dónde encontrar las funciones

| Aplicación | Funciones |
|---|---|
| Contabilidad | Plan de cuentas Ecuador, facturas, impuestos configurados y retenciones contables |
| Facturación electrónica | Preparación local de facturas, emisiones SRI, establecimientos, puntos de emisión, certificado, matriz fiscal y **Anexo ATS (agregador)** |
| Inventario | **Guías de remisión SRI** en operaciones |
| Nómina local | Períodos y novedades, versiones y autoridad, beneficios y **Agregador RDEP** |
| Activos fijos | Altas, calendario de depreciación y asientos según la configuración contable |

La presencia del menú no acredita habilitación tributaria para producción. Se conservan las configuraciones previas; no se cambian tasas, ambiente SRI, certificado ni credenciales. No se envían comprobantes, correos ni pagos durante esta intervención.

## ATS: validación de salida

El módulo estaba sin instalar en el fundador. En el ensayo sobre su copia se detectó además que podía descargar XML incompatible con el XSD incorporado. Ahora valida el XML antes de ofrecerlo; si falla, conserva el detalle agregado y muestra el motivo. Al reconstruir, elimina la descarga anterior para evitar entregar una versión obsoleta.

La copia existente expuso una razón social con puntuación y valores negativos de ventas que el esquema incorporado no admite. La protección impide descargar ese XML: no cambia la razón social ni los importes contables para hacerlo pasar. La resolución fiscal del formato y de las notas de crédito continúa pendiente antes de usar esos datos en una declaración. ATS y RDEP mantienen sus avisos de ensayo y no se presentan como homologados.

## Evidencia y recuperación

- `docs/evidencias/CM28/fundador-ecuador-restore.json`: restauración aislada, conteos, adjuntos y recuperación de certificado.
- `docs/evidencias/CM28/fundador-ecuador-rehearsal.json`: cinco fallos iniciales registrados y repetición corregida de 15 pruebas sin fallos ni errores.
- `docs/evidencias/CM28/fundador-ecuador-update.json`: respaldo de base, archivos, configuración y código; huellas de asientos antes/después y esquema.
- `docs/evidencias/CM28/fundador-ecuador.json`: comprobación con usuario fundador, menús y nueve pantallas.

Validar el respaldo para reversión con `.venv/Scripts/python.exe scripts/restore-cm28-instance.py --report docs/evidencias/CM28/fundador-ecuador-update.json`. La opción `--apply` restaura explícitamente y conserva una copia adicional de la base actual; no se ejecutó sobre el fundador durante la validación. Claves y respaldos permanecen fuera de Git.
