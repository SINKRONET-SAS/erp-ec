# Estado posterior al pronunciamiento técnico

Documento histórico de la versión 18.0.1.11.0 o anterior. El pronunciamiento devuelve DI25-03 para corrección y prevalece la respuesta en [Controles automáticos](DI25-03_CONTROLES_AUTOMATICOS.md). La referencia aislada ya no habilita sustitutos ni 100 canastas en la nómina operativa; los ensayos aritméticos permanecen separados. Las propuestas del borrador no constituyen decisiones aceptadas. DI25-03 sigue observado.

---

# DI25-03 · Borrador de respuestas para el responsable tributario/contable

**PROPUESTA PARA REVISIÓN. No registra aceptación ni homologación.** Las columnas «Respuesta propuesta» y «Fundamento» las redactó el equipo técnico para acelerar la revisión. Solo el responsable, una vez identificado, puede marcar su decisión, corregirla y firmarla en la última tabla. Hasta entonces DI25-03 permanece parcial y DI25-04 no inicia.

## 1. Identificación (completar por el titular y el responsable)

| Dato | Valor |
|---|---|
| Nombre y cargo del responsable tributario/contable | |
| Vínculo con la empresa (interno, contador externo) y RUC o registro profesional | |
| Fecha de la revisión | |
| Medio y ubicación de la evidencia (acta, correo, PDF firmado) | |
| Versión revisada | Módulo erpec_payroll 18.0.1.11.0, commit c47359d o posterior |

## 2. Cómo revisar en la demo (30 minutos)

Demo local: http://127.0.0.1:8369 (acceso en el archivo privado de la demo; no se reproduce aquí).

1. **Áreas → Nómina → Ensayos tributarios de renta.** Abrir en este orden: 02 (otro empleador), 19 (cierre con retenciones), 20 y 22 (100 canastas), 26 a 32 (exenciones). En cada uno comparar el resultado con «Cálculo independiente de referencia» y anotar diferencias en «Observaciones del experto».
2. **Empleado → pestaña Anexo RDEP.** Ver los grupos «Acreditación de exención personal» y «Tope de gastos personales». Comprobar que sin documento del año no se aplica exención.
3. **Áreas → Nómina → Agregador RDEP.** Comprobar los avisos y bloqueos en «Revisión pendiente» y la columna de exención aplicada.
4. Fuentes: DI25-03_EXENCIONES_PERSONALES.md (citas y enlaces), DI25-03_SUPUESTO_ESPECIAL_100_CANASTAS.md y DI25-03_NOMINA_RDEP.md.

## 3. Respuestas propuestas a las decisiones de criterio

| # | Pregunta | Respuesta propuesta | Fundamento y alternativas |
|---|---|---|---|
| D1 | Edad del adulto mayor | Mantener 65 cumplidos al 1 de enero; quien los cumple durante el año queda bloqueado | El texto dice «mayores de sesenta y cinco años» (LRTI art. 9 num. 12). Es la lectura más conservadora y evita aplicar un beneficio sin sustento. Alternativas: aplicar el año completo a quien los cumple en el año, o prorratear. Si el responsable prefiere una, se cambia en un solo punto del motor. Un criterio oficial del SRI, si existe, prevalece sobre esta propuesta. |
| D2 | Entrega del documento después del 15 de enero | Mantener el bloqueo; el responsable decide caso por caso | Reglamento LRTI art. 50: la entrega es hasta el 15 de enero. El reglamento no aclara la retroactividad. Opciones: aplicar desde la entrega y regularizar en la declaración personal, o aceptar el año completo con justificación escrita. |
| D3 | Exención más beneficiosa, no la suma | Aceptar tal como está | La ley dice que no se aplican simultáneamente y rige la más beneficiosa (art. 9 num. 12). Confirmar que se compara el monto ya limitado por la base disponible. |
| D4 | Sustituto | Aceptar un sustituto por caso, proporción por meses y persona sustituida identificada; bloquear el resto | Reglamento LRTI art. 50 lit. b. Los reemplazos dentro del año y los sustitutos de varias personas requieren un tratamiento aparte que hoy no se calcula; permanecen fuera de cobertura. |
| D5 | Grado de discapacidad y tipos del esquema | Aceptar desde 30 % con la escala 60/70/80/100; mantener bloqueado el tipo 00; el tipo 03 no exime la base | Reglamento LOD art. 6. El tipo 00 no tiene descripción en el esquema oficial. El tipo 03 (carga con discapacidad) solo habilita, si se acredita, el tope de 100 canastas. |
| D6 | Retención mensual | Aceptar que la exención reduce la proyección desde el cálculo posterior a la acreditación, sin reliquidar meses contabilizados | La reliquidación retroactiva de retenciones sigue pendiente en el plan (DI25-03_NOMINA_RDEP.md) y requiere su propio oráculo. |
| D7 | Tope de 100 canastas | Aceptar la acreditación con referencia del documento del año; no se valida la calificación sanitaria ni el parentesco | SRI, publicación del 06-02-2026, y LRTI segundo artículo innumerado posterior al art. 10, lit. c. La verificación del certificado sigue a cargo del responsable. |
| D8 | Otros empleadores | Definir que el acumulado del comprobante se importa una sola vez por año y por empleador; mientras no se implemente, mantener el XML bloqueado | Reglamento LRTI art. 96, uso del comprobante previo. Requiere un caso con comprobante anonimizado y resultado anual aprobado. |

## 4. Respuestas propuestas por fila de la matriz

| # | Fila | Respuesta propuesta | Condición |
|---|---|---|---|
| 1 | Año variable, orden distinto | Aceptar | Confirmar que la política del caso es la aplicable a la empresa real |
| 2 | Tarifa 2026 | Aceptar | Contraste con la tabla oficial del SRI; base 12.677 → 23,45 y rebaja 18 % → 5,45 |
| 3 | Beneficio corregido | Aceptar el comportamiento; observar las bases legales | Definir por concepto la base de IESS, IR, décimos, vacaciones y reserva |
| 4 | Préstamo corregido | Aceptar | Saldos 150, 250 y 150; una fila vigente |
| 5 | Otros empleadores | Bloquear expresamente | Hasta el caso con comprobante (D8) |
| 6 | Exenciones personales | Aceptar con las respuestas D1 a D7 | Documento del año y datos completos por empleado |
| 7 | Acumulados y gastos | Bloquear expresamente | Hasta la importación única y su conciliación |
| 8 | Cambios de sueldo y ausencias | Aceptar el cambio salarial anual; bloquear las ausencias | Falta el efecto por base laboral |
| 9 | Décimos y reserva | Bloquear expresamente | Falta devengo, pagos y mapeo RDEP |
| 10 | Cierre anual | Bloquear expresamente | Falta el cierre completo y su referencia |
| 11 | Galápagos, no residencia, convenio, impuesto asumido | Galápagos: aceptar solo el factor de gastos; resto bloquear | Confirmar la elegibilidad insular por empleado |

Nota para el titular: las filas marcadas «Bloquear expresamente» conducen a un cierre con alcance limitado, no a un cierre completo. La matriz vigente y su plan indican que la aceptación del experto no sustituye las integraciones pendientes; decidir si se cierra DI25-03 con esos bloqueos documentados o si se implementan antes las filas 5, 7, 8, 9, 10 y 11 requiere una instrucción explícita del titular.

## 5. Decisión del responsable (completar y firmar)

| Ítem | Decisión | Alcance: años y regímenes | Resultado esperado revisado | Evidencia | Fecha |
|---|---|---|---|---|---|
| D1 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| D2 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| D3 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| D4 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| D5 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| D6 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| D7 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| D8 | ☐ Acepta ☐ Observa ☐ Bloquea | | | | |
| Fila 1 a 11 | Marcar cada una en DI25-03_PAQUETE_ACEPTACION.md | | | | |

Firma del responsable: __________________ Cargo: __________________ Fecha: __________

## 6. Después de la firma

1. El equipo técnico transcribe las decisiones al paquete de aceptación y a la matriz, sin modificarlas.
2. Si alguna respuesta cambia una regla, se ajusta en `engine.py`, se repiten las referencias y la suite.
3. Solo con todas las filas resueltas por el responsable se genera `docs/evidencias/DI25/DI25-03-cierre.json`, se firma el AuditLock y se habilita DI25-04.
