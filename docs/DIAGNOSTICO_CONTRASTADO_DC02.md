# Diagnóstico contrastado DC02

Corte: 02-10-2026. Base examinada: `fcbd30bdc6a566465f508120735123466ecc6704`. Se contrasta el adjunto contra archivos, historial y pruebas; no se toma una declaración documental por una ejecución nueva.

| ID | Afirmación o brecha | Clasificación y evidencia | Tratamiento |
|---|---|---|---|
| D01 | Solo ERPEC26-00 ejecutada | Falso positivo actual: plan maestro y lock registran 00–03 cerradas, 04 parcial; existen módulos y evidencias CM28 | Corregir entradas desactualizadas; no cerrar 04–08 |
| D02 | Community sin commit fijado | Falso positivo: `upstream.json`, caché Git limpia y `community-audit.json` coinciden en `b1fd3a9eee5d575848ac649d2f5103537d8de7a4` | Conservar pin y comprobar coherencia automáticamente |
| D03 | Hash distinto demuestra origen Enterprise del runtime | Inferencia no justificada: hashes de manifiestos/versiones diferentes no prueban procedencia; caché ejecutada es Community | Separar inventario de referencia Enterprise del runtime; no actualizar al SHA del adjunto sin validación |
| D04 | HTTP 404 impide auditar ambas fuentes | Falso positivo para el entorno local: ambas raíces existen y hay contratos auditados en `evidencias/ERPEC26-01.md` | No pedir credenciales para repetir auditoría ya disponible; acceso remoto actual no inferido |
| D05 | No hay runtime Odoo/PostgreSQL | Falso positivo: ejecutor integrado, caché y entornos locales disponibles; ensayo nuevo registrado al cierre | Separar infraestructura local de Render |
| D06 | Firma/EDI requieren necesariamente certificate Enterprise o Facturador | Falso positivo para implementación propia: `erpec_fiscal_native/xades.py`, `models.py`, guías y retenciones propios; OP13/OP14 documentan pruebas históricas | Actualizar autoridad nativa; autorización sigue siendo del SRI |
| D07 | ATS y nómina solo futuros conectores | Falso positivo: `erpec_fiscal_ats/models.py`, `erpec_payroll/models.py`, `annex_rdep.py`; CM28-G-EC y DI25/DI26 | Reconocer implementación sin afirmar homologación o equivalencia integral |
| D08 | No hay administración de planes/provisión | Falso positivo: `erpec_entitlements`, `erpec_selfservice`, `scripts/provision-worker.py`, evidencia CM28 | Reconocer alcance local y límites comerciales |
| D09 | Falta producción y aceptación externa | Confirmado como pendiente en plan maestro y lock; presencia de código/CI no lo resuelve | Conservar gates con responsables/acciones de planes existentes |
| D10 | Conteos transitivos del adjunto fiables | Inconsistencia interna: resumen stock 27 y detalle 28; website 38/39; edi_pos 32/34; edi_stock 30/32; reports 30/31 | Usar auditoría del pin y definir conjunto; no mezclar conteos de revisiones distintas |
| D11 | README/contexto de entrada coherentes | Falso negativo: README dice solo análisis estático y enlaza `.github/CODEX/_CONTEXT.md`, inexistente | Corregir README y controlar enlaces locales en CI |
| D12 | Matriz/arquitectura/guía fiscal expresan estado vigente | Falso negativo: matriz aún pide obtener Community; arquitectura declara pendiente firma ya existente; guía no delimita su primer incremento | Publicar matriz actual y separar diseño/evidencia históricos |

La ausencia de acceso remoto del auditor no demuestra ausencia de código. Tampoco se acepta como verificado el SHA `625eb316e702` del adjunto: no es el pin ejecutado y su vigencia no es necesaria para este contraste. No se afirma que una versión más reciente sea compatible.

## Límites del contraste

El inventario Enterprise es referencia de alcance; no se concede autorización para distribuirlo ni se reaudita una versión remota distinta. No se emiten comprobantes ni correos, no se cobran servicios y no se despliega producción en esta pasada. Las aceptaciones legales y comerciales permanecen separadas. El diagnóstico no aporta un defecto reproducible de cálculo; no se cambian fórmulas para satisfacer afirmaciones obsoletas.

Pruebas históricas relevantes: `docs/evidencias/ERPEC26-01.md`, `docs/evidencias/CM28/CM28-G-cierre.json`, `docs/evidencias/CM28/fundador-ecuador.json` y `docs/PLAN_HAIKY_COMPROBANTES_FIRMADOS.md`. Las pruebas nuevas se registran en `docs/evidencias/DC02/validacion.json` al ejecutarse.
