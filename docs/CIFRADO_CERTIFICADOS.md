# Cifrado en reposo de secretos: certificado de firma (.p12) y token de PayPhone

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
- La clave se puede **rotar** sin volver a cargar nada (ver «Rotación de la clave» abajo).

## Migración de lo que estaba en claro
`erpec_fiscal_sri` 18.0.1.5.0/18.0.1.5.1 cifra y borra el texto plano de las columnas antiguas. Aplicada en el Fundador y en la demo, con `VACUUM FULL` de la tabla para eliminar las versiones antiguas de la fila.
- Defecto encontrado y corregido en la propia migración: la columna binaria de Odoo guarda el archivo como texto base64 y la primera versión cifró ese texto, no los bytes del `.p12`. Se detectó al verificar el certificado real del Fundador (no abría), se corrigió el código, se agregó la migración de reparación 1.5.1 y pruebas que ejecutan ambas migraciones. No se perdió nada: el original se recuperó descifrando.

## Límites honestos
- No protege contra quien tenga acceso al servidor en ejecución (puede leer la clave y la memoria).
- Los respaldos hechos **antes** del 19-09-2026 pueden contener el certificado en claro (demo). Los respaldos del Fundador posteriores a la carga se hicieron excluyendo los datos de la tabla del certificado. Conviene borrar respaldos viejos que ya no se necesiten.
- Residuos en archivos WAL o discos no se pueden garantizar limpios desde aquí.

## PayPhone (19-09-2026, misma fecha, segundo incremento)
El token de la aplicación PayPhone se guardaba en claro en `erpec_payphone_provider.token`. Ahora usa el mismo mecanismo:
- El almacén de cifrado vive en el módulo compartido **`erpec_secrets`** (`erpec_fiscal_sri.secret_store` queda como alias de compatibilidad); `erpec_fiscal_sri` y `erpec_payphone` dependen de él. Cualquier módulo nuevo con credenciales debe usarlo.
- `token` es solo de entrada (se lee siempre vacío); se guarda en `token_encrypted` con contexto `payphone:<id>:token`; `token_loaded` indica que hay uno cargado. `_bearer_token()` lo descifra únicamente al llamar a PayPhone. El `StoreID` no es un secreto y sigue en claro.
- Migración `erpec_payphone` 18.0.1.1.0 aplicada con respaldo (excluyendo los datos de las tablas con secretos) y `VACUUM FULL` en el Fundador y en el piloto sintético `erpec_a`. En ambos se comprobó que el token descifra; el certificado del Fundador sigue verificado.
- Script reutilizable: `encrypt-instance.py <carpeta>` (en el scratchpad de la sesión) hace respaldo, actualización y purga; el procedimiento equivale a `-i erpec_secrets -u <módulos con secretos>`.
- Quedan bases de pruebas residuales del clúster local (`erpec_pp_test_*`) con tokens sintéticos en claro; no son instancias reales y conviene eliminarlas.

## Rotación de la clave (19-09-2026)
**Formato:** los secretos se guardan como `v2:<id de clave>:<token>`; el id (8 hex del SHA-256 de la clave) dice con qué clave se cifró sin descifrar. Los `v1:` antiguos se siguen leyendo.
**Claves anteriores** (solo para descifrar mientras dura la rotación): `ERPEC_SECRET_KEY_PREVIOUS` (varias separadas por coma), opción `erpec_secret_key_previous` de `odoo.conf` o el archivo `erpec_secret.previous`.

**Desde la pantalla** (administrador del sistema): Ajustes > Técnico > *Rotación de claves de secretos* muestra el origen y el id de la clave vigente y cuántos secretos hay por clave (nunca los secretos). Dos botones:
- *Generar clave nueva y re-cifrar* (cuando la clave vive en el archivo `erpec_secret.key`): crea la clave nueva, guarda la anterior en `erpec_secret.previous` y re-cifra todo.
- *Re-cifrar con la clave vigente*: cuando el operador ya definió la clave nueva por variable de entorno u `odoo.conf`.

**Desde la línea de comandos:** `python scripts/rotate-secret-key.py <instancia>` (o `--estado` para solo informar).

**Con clave en variable de entorno (Render):** (1) generar una clave nueva de 32+ caracteres; (2) `ERPEC_SECRET_KEY_PREVIOUS` = clave actual, `ERPEC_SECRET_KEY` = la nueva; (3) reiniciar; (4) *Re-cifrar con la clave vigente*; (5) comprobar que «pendientes con otra clave» es 0; (6) recién entonces retirar `ERPEC_SECRET_KEY_PREVIOUS`. Guardar la clave nueva en el gestor de secretos.

**Garantías:** antes de escribir, el re-cifrado descifra todo en memoria; si algún secreto no se puede descifrar (falta una clave anterior) **no se modifica nada** y se informa cuáles. Solo un administrador del sistema puede rotar. Cada secreto nuevo que un módulo agregue debe registrarse con `secret_store.register(modelo, campo, contexto)` para entrar en la rotación.

**Límite:** una rotación no protege un respaldo antiguo ya filtrado (sigue descifrable con la clave vieja); sirve para acotar el daño futuro y para sustituir una clave sospechosa. Tras rotar, respaldar el archivo de claves (`erpec_secret.key` y `erpec_secret.previous`) aparte de la base.

## Bases residuales eliminadas
Se borraron las 6 bases `erpec_pp_test_*` (tokens sintéticos en claro), tras comprobar que no tenían conexiones, ninguna configuración las usaba y no tenían rol propio. Las instancias reales (`erpec_fundador`, `erpec_a`, `erpec_b`, `erpec_demo`) no se tocaron. El clúster local conserva otras bases de prueba de otras familias (`ec_operational_*`, `ec_recovery_*`, `erp_*`, etc.) que no se revisaron ni borraron.

## Despliegue Linux (20-09-2026)
- `deployment/linux/runtime.py` **exige** `ERPEC_SECRET_KEY` (mínimo 32 caracteres) y no arranca sin ella; la plantilla `deployment/render.customer.example.yaml` la declara con `sync: false` para que la fije una persona. Generarla con `python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(48)).decode())"` y guardar una copia **fuera** del proveedor: perderla deja ilegibles el certificado de firma y el token de PayPhone.
- En Windows local la clave vive en `erpec_secret.key` del directorio de datos de cada instancia y su respaldo en `.cache/windows/backups/claves-*`. No se conservan respaldos anteriores al cifrado (purgados el 20-09-2026).
- `workers = 0` es deliberado: los proveedores tipo PaaS exponen un solo puerto y con workers > 0 Odoo mueve el websocket (chat, notificaciones) a otro puerto (`gevent_port`) que exigiría enrutar en un proxy. Para más capacidad, escalar con más instancias (una base por cliente) o poner Nginx delante y subir `workers` a 2×núcleos+1 con `proxy_mode = True` (ya activo) y el puerto de longpolling enrutado; no se cambia por defecto sin poder probarlo.
- TLS lo termina el proveedor (Render) y `proxy_mode = True`; la base exige `sslmode=require`.

## Estado
- Clave maestra en despliegue real: obligatoria en Linux (resuelto). Retirar las claves anteriores (`erpec_secret.previous`) tras un periodo de confianza sigue siendo una decisión operativa del titular.
