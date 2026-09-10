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

## 10. Procedencia y aplicación de reglas
- Consolidado desde RULES.md de SKNOMINA y SINKRONET FACTURADOR. Copias y hashes en docs/referencias y docs/evidencias/fuentes.json.
- Se conservan las reglas comunes y la exposición frontend exigida por SKNOMINA. Extender UTF-8 sin BOM a Python, XML, YAML, CSV y scripts propios.
- Las instrucciones explícitas del usuario prevalecen. Esta solicitud autoriza crear el repositorio y desplegar el plan; no se declara ejecutada la implementación.
- No pedir de nuevo autorizaciones ya otorgadas para el mismo alcance. Las fases se ejecutan por sus prompts y conforme a la autorización vigente.

## 11. Licencias y arquitectura
- Base: Odoo Community 18 oficial, con commit fijado después de verificar procedencia, soporte y dependencias. La versión es una decisión inicial revisable antes de construir.
- No incorporar módulos OEEL-1/OPL-1 sin autorización compatible. La carpeta Enterprise solo es referencia de capacidades; no constituye origen aprobado de distribución.
- Inventariar licencias transitivas y avisos; no asumir que LGPL de la raíz cubre todos los módulos. Revisar por separado componentes AGPL.
- La licencia del código propio nuevo queda pendiente de decisión del titular; no relicenciar aportes de terceros ni publicar código propietario.
- Mantener separados núcleo Community, módulos propios y administración SaaS. No compartir bases de datos ni contraseñas entre productos.
- Una sola autoridad por cálculo laboral, autorización fiscal, asiento y cobro. Cualquier traslado de lógica debe incluir equivalencia, migración y retirada controlada del duplicado.

## 12. Integridad de integración y operación
- Vincular organización de la suite, tenant SKNOMINA, empresa Facturador e instancia/compañía Odoo con identificadores explícitos; nunca asociar solo por correo o RUC recibido.
- Credenciales por organización, mínimo privilegio, secretos fuera de Git, aislamiento verificable y auditoría con correlationId.
- Usar idempotencia persistente, outbox/inbox o equivalentes durables, reintentos acotados, conciliación y defensa contra eventos repetidos o fuera de orden.
- Distinguir pago del servicio, capacidad contratada, aprovisionamiento y autorización fiscal. Una factura aceptada en cola no es una factura autorizada.
- Distinguir productos contratados de acceso API y cuotas. Versionar planes sin modificar silenciosamente contratos activos; migración explícita y revisable.
- Para cambios en repositorios externos, revisar sus reglas, conservar trabajo ajeno y producir commits independientes vinculados al plan.
- No afirmar homologación, cumplimiento legal, restauración o despliegue sin evidencia. Importes, impuestos y formatos de la copia de 2025 requieren validación vigente antes de producción.

## 13. Cadena de gobierno reproducible
- Lock canónico: .vscode/AuditLock.json; contexto: .github/CODEX_CONTEXT.md.
- Génesis: docs/evidencias/AuditLock.genesis.json con fase previa nula. No representa implementación.
- Para cada cierre, guardar bytes exactos del lock anterior en docs/evidencias, registrar su SHA256 y firmar SHA256(bytes anteriores concatenados con updatedAt UTF-8).
- Añadir hashes de entregables al lock, sin incluir el propio lock. Comprobar cadena y entregables con node scripts/verify-governance.cjs.
- La firma es un encadenamiento de integridad, no una firma digital de identidad. Solo registrar validaciones realizadas, con alcance y limitaciones.
