# Plan Haiky DC02 — contraste del diagnóstico y mejora de continuidad

Fecha: 02-10-2026 (Ecuador). Autorización: solicitud del titular de contrastar falsos positivos/negativos, implementar correcciones, verificar regresiones, cerrar gobierno y realizar commit/push. Raíz comprobada: `C:/proyectos web/ERP/_EC`; `C:/proyectos web/ERP_EC` no existe. Se usan `.github/CODEX_CONTEXT.md`, `.vscode/AuditLock.json` y `.github/prompts` de la raíz comprobada.

## Alcance verificado

El adjunto describe principalmente ERPEC26-00 y un bloqueo de ERPEC26-01. El contraste reconoce los incrementos posteriores sin declarar cerradas las fases maestras 04–08. Los defectos actuales reproducidos son información de entrada desactualizada, enlace de contexto roto y falta de controles de coherencia documental. No se necesita reimplementar firma, nómina, ATS ni aprovisionamiento existentes para corregirlos.

Informe: [DIAGNOSTICO_CONTRASTADO_DC02.md](DIAGNOSTICO_CONTRASTADO_DC02.md). Evidencias nuevas en `docs/evidencias/DC02/`. Las evidencias anteriores son históricas y se citan como tales.

| Fase | Dependencia | Entrega y aceptación | Estado de ejecución |
|---|---|---|---|
| DC02-00 | Gobierno existente válido | Contrastar afirmaciones, identificar límites, desplegar plan y prompts; sellar diagnóstico | Cerrada: contraste |
| DC02-A | DC02-00 sellada | Corregir README, matriz, arquitectura y guía fiscal; controlar enlaces y coherencia del pin en CI | Cerrada: correcciones verificadas |
| DC02-B | DC02-A sellada | Pruebas negativas, suite integrada, revisión de diferencias, cierre trazable, commit/push | Cerrada; implementación publicada |

## Ejecución y reversión

La orden vigente autoriza los tres prompts en secuencia; no requiere otra aprobación por fase. Cada cierre preserva bytes del lock anterior, hashes, comprobaciones ejecutadas y estado del complemento DC02. Los estados maestros y pendientes externos se conservan. No incorporar `.claude/` preexistente al sellado ni al commit.

No hay migración de datos ni modificación de API o de repositorios fuente. Reversión mediante un commit inverso de los cambios DC02 y un nuevo eslabón de gobierno; no restaurar un lock histórico sobre cambios posteriores. La exposición es el README y las guías de entrada del repositorio: no cambia la interfaz operativa del ERP ni exige instalar módulos.

## Pendientes externos conservados

Render y operación productiva (cuenta, dimensionamiento, región y secretos en plataforma), primer envío fiscal productivo supervisado, aceptación normativa/bancaria, SMTP real y decisiones comerciales/licencia propia. Ver planes maestros y `pendingChecks` del lock. Un cierre DC02 solo acredita el contraste y sus correcciones; no acredita esas aceptaciones ni elimina sus dependencias.

## Cierre local DC02

Fases 00, A y B ejecutadas. Validación: 704 pruebas integradas (0 fallos/errores, 3 omisiones cubiertas por 25 pruebas de Tesorería en copia de demo sin omisiones), 30 pruebas de control aprobadas, 30 enlaces y 46 módulos Community auditados. Evidencia: [validacion.json](evidencias/DC02/validacion.json). No se encontraron regresiones en lo ejecutado. Los pendientes externos de D09 se conservan; no son cerrados por DC02. Implementación publicada en 007fdd2db65397225cbbab4ac5c0c612b32992eb. El resultado remoto se consulta por SHA en GitHub; no se atribuye anticipadamente aprobación a un commit posterior de cierre.
