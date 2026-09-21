# Estado vigente: pronunciamiento observado y controles automáticos

El pronunciamiento técnico recibido devuelve DI25-03 para corrección; no existe homologación. Ver [DI25-03_CONTROLES_AUTOMATICOS.md](DI25-03_CONTROLES_AUTOMATICOS.md) para las correcciones, bloqueos ejecutables y límites. La autenticidad de certificados, la importación versionada de otro empleador, la reliquidación mensual acumulada y la conciliación anual completa permanecen pendientes. Sustitutos y 100 canastas no se habilitan en nómina mediante una referencia aislada; los ensayos sintéticos siguen disponibles. Esta sección prevalece sobre los estados históricos siguientes.

---

# DI25-03 · Paquete para la aceptación del responsable tributario y laboral

Estado: pendiente de revisión. Este documento prepara la decisión; no la registra. Un «continuar» genérico no cuenta como homologación (ver DI25-03_MATRIZ_ACEPTACION.md).

Responsable tributario/contable: __________ (identificación pendiente del titular) · Fecha de revisión: __________ · Medio de evidencia: __________

## Cómo cerrar DI25-03

DI25-03 se cierra cuando cada fila de la matriz tiene una de estas dos salidas, ambas con evidencia: (a) aceptación del responsable con el alcance, el período y el resultado esperado indicados; o (b) bloqueo expreso del régimen, visible en la interfaz, con su siguiente acción. Lo implementado y ensayado no sustituye esa decisión. Con las decisiones registradas se genera `docs/evidencias/DI25/DI25-03-cierre.json`, se firma el AuditLock y recién entonces se habilita DI25-04.

## Estado por fila de la matriz

| # | Fila | Estado técnico | Casos / pruebas | Falta para cerrar |
|---|---|---|---|---|
| 1 | Año variable, orden distinto | Automatizado | Pruebas del RDEP; oráculo 60 | Política aplicable a una empresa real |
| 2 | Tarifa 2026 | Oráculo aritmético independiente | Base 12.677 → 23,45 / 5,45 | Aceptación del responsable |
| 3 | Beneficio corregido | Automatizado | Pruebas de beneficios | Bases legales separadas por concepto |
| 4 | Préstamo corregido | Automatizado y visible | Saldos 150 / 250 / 150 | Ninguno técnico |
| 5 | Otros empleadores | Ensayos 01–03; XML **bloqueado** | Referencias con IESS y retenciones separadas | Comprobante anonimizado y resultado anual aprobado |
| 6 | Exenciones personales | **Implementado**: adulto mayor, discapacidad, sustituto, tope de 100 canastas; acreditación con bloqueos | Ensayos 20–32; pruebas de motor, nómina mensual y RDEP; ver DI25-03_EXENCIONES_PERSONALES.md | Aceptación y las decisiones de la sección siguiente |
| 7 | Acumulados y gastos | Ensayo 02; agregación de flujos probada | — | Importación única contra comprobante y conciliación |
| 8 | Cambios de sueldo y ausencias | Ensayos 04–05 | — | Días, descuento y efecto por base laboral |
| 9 | Décimos y reserva | Ensayo 18 (separación informativa) | — | Devengo, pagos y mapeo RDEP integral |
| 10 | Cierre anual | Ensayo 19 (impuesto y retenciones) | — | Cierre completo del anexo y referencia aprobada |
| 11 | Galápagos, no residencia, convenio, impuesto asumido | Tope de gastos con factor 1,803; resto **bloqueado** | Ensayos 12–17 y 24 | Aplicabilidad y caso completo por régimen |

## Decisiones de criterio que el responsable debe confirmar o corregir

Estas reglas quedaron implementadas como supuestos explícitos. Si el responsable las corrige, se cambian en un solo lugar (`engine.py`) y se repiten las referencias.

1. **Edad del adulto mayor.** El texto legal dice «mayores de sesenta y cinco años». Se cubre solo el ejercicio completo: 65 años cumplidos al 1 de enero. Quien los cumple durante el año queda bloqueado. ¿Corresponde prorratear, aplicar el año completo o exigir otra fecha?
2. **Entrega del documento.** Se exige hasta el 15 de enero (Reglamento LRTI, art. 50). Una entrega posterior bloquea el anexo. ¿Se aplica retroactivamente, desde la entrega o solo en la declaración personal?
3. **Simultaneidad.** Se aplica la exención más beneficiosa, nunca la suma. Confirmar que se compara el monto ya limitado por la base.
4. **Sustituto.** Proporción por meses de ejercicio y un solo sustituto por caso; se exige identificar a la persona sustituida. Confirmar tratamiento de reemplazos dentro del año y de sustitutos de varias personas.
5. **Discapacidad.** Solo desde 30 % y con la escala del Reglamento LOD, art. 6: 30-49 % aplica 60; 50-74 %, 70; 75-84 %, 80; 85-100 %, 100. El tipo 00 del esquema queda bloqueado por falta de descripción oficial; el tipo 03 no exime la base.
6. **Retenciones mensuales.** La exención reduce la proyección mensual desde el cálculo posterior a la acreditación; no reliquida meses ya contabilizados.
7. **Tope de 100 canastas.** Se acredita con referencia del año; no se valida la calificación sanitaria ni el parentesco.
8. **Otros empleadores.** Confirmar el mecanismo (importe acumulado del comprobante, una sola vez por año) para poder levantar el bloqueo del XML.

## Registro de la decisión (completar por el responsable)

| # | Decisión | Alcance: años y regímenes | Resultado esperado revisado | Evidencia revisada | Fecha |
|---|---|---|---|---|---|
| 1 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 2 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 3 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 4 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 5 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 6 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 7 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 8 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 9 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 10 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| 11 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |

## Trabajo técnico que sigue independiente de la aceptación

- Importación única de acumulados de otro empleador con control de duplicados por año (fila 7), para poder ensayarla con un comprobante anonimizado.
- Modelo de ausencias con efecto separado en IESS, IR, décimos, vacaciones y reserva (fila 8).
- Devengo, pago y mapeo RDEP de décimos y reserva (fila 9); conciliación de casilleros y comparación separada de contenido económico y estructura XML (fila 10).
- Aplicabilidad y casos de Galápagos, no residencia, convenios e impuesto asumido; hasta entonces el bloqueo se conserva (fila 11).
