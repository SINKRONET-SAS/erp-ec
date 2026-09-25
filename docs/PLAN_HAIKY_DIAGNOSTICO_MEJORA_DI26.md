# Plan Haiky DI26 — Corrección y mejora posterior a DI25

Fecha: 25-09-2026 (Ecuador). Plan complementario al maestro ERPEC26 y sucesor de DI25 (cerrado y aceptado). No reabre DI25 ni renumera sus fases.
Fuente: [Diagnóstico integral DI26](DIAGNOSTICO_INTEGRAL_DI26.md) y `docs/evidencias/DI26/hallazgos.json`.
Estado vigente: ver `.github/CODEX_CONTEXT.md` y el bloque `diagnosticImprovementDI26` de `.vscode/AuditLock.json`.
Autorización: el titular pidió el 25-09-2026 desplegar este plan, ejecutar todos sus prompts, verificar errores, duplicaciones y regresiones, corregir lo que aparezca y publicar (commit y push).

## Objetivo y alcance

Corregir los 16 hallazgos y las observaciones P3 de DI26 sobre el producto existente, respetando RULES.md y AGENTS.md: una autoridad por cálculo, documento, asiento y cobro; nada de estados paralelos; exposición en frontend de todo avance que afecte al usuario; español de Ecuador en la UI; y ninguna afirmación de cumplimiento sin evidencia.

Límites vigentes: no enviar comprobantes, correos, transferencias ni declaraciones reales; no modificar repositorios fuente; respaldo antes de tocar cualquier instancia; no pedir secretos ya disponibles.

## Fases y dependencias

| Fase | Resultado | Depende | Hallazgos |
|---|---|---|---|
| DI26-00 — Diagnóstico y planificación | Informe, evidencias, plan, prompts y gobierno. Completada como diagnóstico. | — | Todos |
| DI26-A — Operación, esquema y validación reproducible | Versiones coherentes, actualización de todos los módulos instalados, detector de desfase de esquema, sellado y recorridos de UI en el repositorio, pruebas de Tesorería sin depender de la demo sembrada | DI26-00 | DI26-01, DI26-13 |
| DI26-B — Integridad fiscal y de pagos | Sustento ATS estable, identificación bancaria fiel al tipo declarado, cuenta propia desde el diario bancario, datos de ensayo marcados | DI26-A | DI26-02, DI26-03, DI26-12, DI26-11 (cuentas e identificación) |
| DI26-C — Nómina: décimos | Régimen del décimo cuarto por empleado, liquidación de décimos acumulados con fecha legal y pago preparado | DI26-B | DI26-05 |
| DI26-D — Legal y privacidad | RUC del proveedor del sistema en información adicional (Anexo 26, ficha 2.34), exclusión comercial conectada con la lista negra de correo, transparencia del formulario de derechos | DI26-C | DI26-04, DI26-06, DI26-15 |
| DI26-E — Español de Ecuador, UI y accesibilidad | Idioma y zona por defecto, etiquetas en español, avisos veraces, alertas accesibles, sitio en es_EC, superficie de la demo, observaciones P3 | DI26-D | DI26-07, DI26-08, DI26-09, DI26-14, DI26-16, P3 |
| DI26-F — Coherencia documental y aceptación | Evidencias históricas corregidas con nota fechada, menús sin duplicado, regresión integral (suite, desfase, recorridos) | DI26-E | DI26-10, DI26-11 (menús e ingresos), regresión de todos |

Orden estricto DI26-00 → A → B → C → D → E → F. No iniciar una fase sin el cierre firmado de la anterior. DI26-06 tiene plazo legal el 26-09-2026 (60 días desde el Registro Oficial 335 del 28-07-2026); se ejecuta en DI26-D sin saltar el orden porque DI26-A a C no la bloquean en tiempo.

## DI26-A — Operación, esquema y validación reproducible

Tareas / aceptación:

1. **DI26-A.1** Cada módulo propio con cambios de modelo posteriores a su última versión sube de versión; la verificación de versiones queda en una prueba.
2. **DI26-A.2** `scripts/check-schema-drift.py` compara el registro de Odoo con las columnas de cada instancia y sale con código distinto de cero si hay desfase.
3. **DI26-A.3** `scripts/update-instance.py` respalda y actualiza todos los módulos `erpec_*` instalados de una instancia; `manage-odoo.py update()` deja de actualizar solo `erpec_base`.
4. **DI26-A.4** El sellado del AuditLock (`scripts/seal-auditlock.cjs`) y los recorridos de UI (`scripts/ui-menu-crawl.py`, `scripts/ui-roles-battery.py`) viven en el repositorio y son reproducibles.
5. **DI26-A.5** Las pruebas de Tesorería y exportación bancaria crean su propia política de nómina y se ejecutan en una base limpia (y por tanto en CI); solo las pruebas de saneamiento de la demo siguen requiriéndola.

Reversión: las versiones y scripts se revierten con git; las actualizaciones de instancia tienen respaldo previo.

## DI26-B — Integridad fiscal y de pagos

1. **DI26-B.1** Leer los avisos del plan de impuestos no altera el sustento ATS guardado; el sustento solo se recalcula al cambiar producto, tercero o empresa, y nunca pisa un valor manual.
2. **DI26-B.2** La exportación bancaria usa el tipo de identificación declarado; conserva pasaportes alfanuméricos y rechaza identificaciones que no cumplan el formato del banco.
3. **DI26-B.3** La cuenta propia de la empresa se toma de la cuenta del diario bancario de nómina (una sola autoridad); se retira `erpec.bank.company.account`.
4. **DI26-B.4** Una empresa puede marcarse como de ensayo; sus archivos XML de anexos se nombran como ensayo no presentable y la UI lo advierte. La empresa ficticia de la demo queda marcada.

Reversión: migración de datos de cuentas propias documentada; restaurar desde respaldo si se requiere el modelo retirado.

## DI26-C — Nómina: décimos

1. **DI26-C.1** Régimen del décimo cuarto (Sierra/Amazonía o Costa/Insular) por empleado con valor por defecto de la empresa.
2. **DI26-C.2** Liquidación de décimos: suma lo acumulado no pagado de los períodos contabilizados hasta el mes de corte, propone el corte y la fecha límite legal (décimo tercero: 24 de diciembre, art. 111 CT; décimo cuarto: 15 de marzo Costa/Insular y 15 de agosto Sierra/Amazonía), traslada el pasivo a nómina por pagar y permite registrar el pago por empleado sin duplicar lo ya liquidado.
3. **DI26-C.3** Pantallas, permisos y pruebas; el corte es editable porque el texto legal habla de "año calendario" y el corte de noviembre es práctica del Ministerio del Trabajo.

Reversión: la liquidación se revierte con asiento inverso mientras no tenga pagos conciliados.

## DI26-D — Legal y privacidad

1. **DI26-D.1** Todo comprobante nativo (factura, notas, liquidación, retención, guía) incluye `campoAdicional nombre="RUC Proveedor"` cuando la empresa emite con este sistema como sistema de terceros (Ficha Técnica 2.34, Anexo 26); validado contra el XSD de cada comprobante y visible en el RIDE.
2. **DI26-D.2** La exclusión comercial del contacto y la lista negra de correo son la misma autoridad: marcar la exclusión agrega el correo a la lista negra y la exclusión refleja la lista negra.
3. **DI26-D.3** El formulario público de derechos informa responsable, finalidad, base y conservación de los datos que recoge.

## DI26-E — Español de Ecuador, UI y accesibilidad

1. **DI26-E.1** Idioma por defecto es_EC y zona America/Guayaquil para contactos y empresas; el aprovisionamiento lo aplica a cada inquilino; migración para bases existentes.
2. **DI26-E.2** Ningún campo propio visible con etiqueta automática en inglés.
3. **DI26-E.3** Avisos veraces en la factura (vista previa) y en el RDEP.
4. **DI26-E.4** Alertas con `role` en todas las vistas propias; el sitio público usa es_EC por defecto.
5. **DI26-E.5** La demo retira módulos ajenos al producto sin romper dependencias del ERP, con respaldo previo.
6. **DI26-E.6** Observaciones P3: mojibake de `install-fiscal.py`, tildes, usuario de prueba activo, advertencia de `compute_sudo`.

## DI26-F — Coherencia documental y aceptación

1. **DI26-F.1** Las afirmaciones falsas de DI25 (certificado propio, talón, ventas ATS, envío masivo) se corrigen con nota fechada, sin borrar la historia.
2. **DI26-F.2** Una sola entrada de menú para las retenciones contables; las dos vías de ingresos no gravados quedan explicadas en la UI.
3. **DI26-F.3** Regresión integral: suite completa, desfase de esquema 0 en todas las instancias, recorrido de menús y batería de roles sin errores, CI verde.

## Responsables

- Técnico: ejecutor del prompt autorizado.
- Tributario/contable: confirma cortes de décimos y el RUC del proveedor por empresa cuando corresponda.
- Titular: decide sobre datos de la demo y aceptación.

## Gobierno

Cada fase crea `docs/evidencias/DI26/DI26-X-cierre.json`, actualiza el contexto y sella el AuditLock (`scripts/seal-auditlock.cjs`). Commits con `phase: DI26-X task: DI26-X.Y`.
