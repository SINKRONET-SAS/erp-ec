# REGLAS HAIKY PARA CODEX - NO NEGOCIABLES

## 1. Integridad del texto
- Todo archivo .js, .md, .json debe ser guardado en **UTF-8 sin BOM**.
- Prohibido: caracteres fuera del rango UTF-8 valido, mojibake, secuencias \uFFFF no resueltas.
- Validar explicitamente en cada escritura: `Buffer.from(text, 'utf8').toString('utf8') === text`.

## 2. Zero silent failures
- Ningun `catch (err) {}` vacio.
- Ningun `if (!condition) return;` sin log o error explicito.
- Todo flujo alternativo debe emitir `console.error` estructurado o lanzar `AppError`.
- Todo error de infra (DB, Redis, Signer, SRI) debe tener: `code`, `statusCode`, `correlationId`, `userId` (si existe).

## 3. Zero regresiones tecnicas
- No se elimina ni modifica ninguna funcion publica sin antes verificar usos.
- No se cambia la forma de respuesta de API publica sin plan de compatibilidad.
- Toda migracion de estado debe poder revertirse con un script documentado.

## 4. Zero deuda tecnica en el cambio
- No se dejan `TODO`, `FIXME`, `HACK` sin ticket asociado en el codigo.
- No se duplica logica (DRY estricto en el modulo afectado).
- No se introducen nuevos estados paralelos (ej: `estado` duplicado fuera de la DB).

## 5. Espanol tecnico obligatorio
- Comentarios: espanol tecnico, sin mezcla de ingles.
- Mensajes de log: espanol.
- JSDoc: espanol.
- Nombres de variables: ingles (codigo estandar), documentacion en espanol.
- Mensajes de error visibles al usuario: espanol.

## 6. Validacion por fase (AuditLock)
- Al terminar cada fase se debe generar/actualizar `AuditLock.json` con:
  - `phaseCompleted`
  - `filesModified`
  - `validationChecks` (lista de checks que pasaron)
  - `signature` (SHA256 del contenido del lock anterior + timestamp)
- No se puede iniciar una fase si el `AuditLock` de la fase anterior no esta firmado y valido.

## 7. Orden de ejecucion estricto
- Respetar el orden de fases definido en el plan.
- No adelantar tareas de fases posteriores.
- Cada fase requiere aprobacion explicita (por prompt) antes de continuar.

## 8. Exposicion frontend obligatoria
- Siempre que se ejecute un plan, el avance funcional debe quedar debidamente expuesto en frontend cuando afecte experiencia de usuario, operacion, configuracion o supervision.
- No se considera cerrado un plan si sus entregables quedan ocultos solo en backend, documentacion, contratos, seeds o configuraciones internas.
- Deben quedar configuradas las importaciones, rutas, pantallas indispensables, navegacion y estados UI/UX necesarios para que el usuario pueda encontrar, operar o revisar el avance.
- Si una fase queda bloqueada por fuente externa, validacion legal, credenciales, tienda, banco o entidad publica, el bloqueo debe mostrarse en UI con mensaje claro y siguiente accion.
- El cierre de fase debe validar que la pantalla o acceso frontend compila y no rompe navegacion existente.

## 9. Trazabilidad
- Cada cambio debe incluir en el commit: `phase: <X>` y `task: <Y.Z>`.
- Los logs deben incluir `correlationId` de la operacion.
