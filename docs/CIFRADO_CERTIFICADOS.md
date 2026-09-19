# Cifrado en reposo del certificado de firma (.p12) y su contraseña

## Qué cambió (19-09-2026)
Antes el archivo `.p12` y su contraseña se guardaban en claro en PostgreSQL (solo protegidos por permisos). Cualquiera con un respaldo o volcado de la base los obtenía. Ahora se guardan **cifrados** (Fernet: AES + HMAC-SHA256) con una clave que **no está en la base de datos**.

- Los campos `p12_file` y `p12_password` son solo de entrada: siempre se leen vacíos (también por RPC). Al guardarlos se cifran y se registra `p12_loaded` y la huella SHA-256 del archivo.
- Solo el servidor descifra, en memoria, al verificar o firmar (`_signing_material()`).
- Cada texto cifrado queda atado a su registro y campo (HKDF por contexto `cert:<id>:p12|password`): copiarlo a otro registro no sirve. Cualquier alteración se detecta.
- Cargar un archivo o contraseña nuevos invalida la verificación (hay que verificar de nuevo).

## Dónde vive la clave maestra
En este orden: variable de entorno `ERPEC_SECRET_KEY` (mínimo 32 caracteres) → opción `erpec_secret_key` de `odoo.conf` → archivo `erpec_secret.key` que se genera una sola vez en el directorio de datos (`data_dir`, fuera de la base y fuera del filestore de la base).
- **En Render/producción usar `ERPEC_SECRET_KEY`** y guardarla en el gestor de secretos de la plataforma.
- **Respaldar la clave aparte de los respaldos de la base.** Si se pierde, los certificados guardados no se recuperan y deben volver a cargarse (el sistema lo indica con un mensaje claro).
- Cambiar la clave invalida los certificados cifrados con la anterior (no hay rotación automática todavía).

## Migración de lo que estaba en claro
`erpec_fiscal_sri` 18.0.1.5.0/18.0.1.5.1 cifra y borra el texto plano de las columnas antiguas. Aplicada en el Fundador y en la demo, con `VACUUM FULL` de la tabla para eliminar las versiones antiguas de la fila.
- Defecto encontrado y corregido en la propia migración: la columna binaria de Odoo guarda el archivo como texto base64 y la primera versión cifró ese texto, no los bytes del `.p12`. Se detectó al verificar el certificado real del Fundador (no abría), se corrigió el código, se agregó la migración de reparación 1.5.1 y pruebas que ejecutan ambas migraciones. No se perdió nada: el original se recuperó descifrando.

## Límites honestos
- No protege contra quien tenga acceso al servidor en ejecución (puede leer la clave y la memoria).
- Los respaldos hechos **antes** del 19-09-2026 pueden contener el certificado en claro (demo). Los respaldos del Fundador posteriores a la carga se hicieron excluyendo los datos de la tabla del certificado. Conviene borrar respaldos viejos que ya no se necesiten.
- Residuos en archivos WAL o discos no se pueden garantizar limpios desde aquí.
- La credencial de PayPhone (`erpec_payphone`) tiene la misma debilidad de guardarse sin cifrar y **no se cambió** en este incremento.
