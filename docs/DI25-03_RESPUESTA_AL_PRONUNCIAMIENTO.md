# Respuesta punto por punto al Pronunciamiento Técnico Tributario DI25-03

| | |
|---|---|
| **Para** | Responsable tributario/contable (Gonzalo Proaño, coordinador técnico) |
| **De** | Equipo técnico del proyecto |
| **Fecha** | 21 de septiembre de 2026 |
| **Documento que se responde** | DI25-03_PRONUCIAMIENTO_TECNICO.pdf (5 páginas, SHA-256 `3f56196745924b1cf3600f842116a04b8e24ed091131d59f4ec3f451915b2722`) |
| **Versión que responde** | `erpec_payroll` 18.0.1.13.1, commit `a753558` |
| **Estado** | DI25-03 sigue **observado y no homologado**. No solicitamos firma: solicitamos revisar los puntos marcados «Necesitamos de usted». |

## 1. Pronunciamiento

Aceptamos la decisión «observar y devolver para corrección». No registramos la recepción del documento como aceptación ni como firma: sus campos de nombre, cargo, firma y fecha están vacíos y así permanecen. Todo lo que sigue es una respuesta técnica; ningún control automático sustituye su criterio ni una absolución vinculante del SRI.

Cómo leer las respuestas: **Hecho** = existe un control ejecutable con pruebas; **Parcial** = existe una parte y se indica lo que falta; **No hecho** = no está implementado y se explica por qué.

## 2. Vigencia y parámetros verificados para 2026

Contrastamos cada cifra del pronunciamiento con el motor de cálculo, con cálculos independientes:

| Parámetro | Pronunciamiento | Motor | Resultado |
|---|---|---|---|
| Fracción básica IR 2026 | USD 12.208; 5 % hasta USD 15.549 | 12.208 y 15.549 al 5 % | Coincide |
| Canasta familiar de enero | USD 821,80 | 821,80 (límite sin cargas 5.752,60 = 7 × 821,80) | Coincide |
| Rebaja por gastos personales | 18 % del menor entre gasto y límite, sin superar el impuesto | 18 %; la rebaja aplicada nunca supera el impuesto causado | Coincide |
| Límites por cargas | 7 / 9 / 11 / 14 / 17 / 20 canastas | 5.752,60 / 7.396,20 / 9.039,80 / 11.505,20 / 13.970,60 / 16.436,00 | Coincide |
| Límite especial | 100 canastas | 82.180,00 | Coincide |
| IPCEG Galápagos | 1,803, sujeto a elegibilidad | 1,803; el caso 11 lo bloquea sin elegibilidad | Coincide |

**Control nuevo:** estos valores están ahora **sellados** (`parameters_seal.py`) con su fuente, fecha de vigencia y una huella SHA-256. Un cambio sin resellar la huella falla, y el cálculo se bloquea si la política o las constantes del motor se desvían de lo sellado. Un ejercicio cercano sin sello avisa: no se reutilizan valores de otro año.

**Discrepancia que ponemos a su consideración:** la codificación de la LRTI publicada por el SRI que consultamos indica «última reforma 01-04-2026», mientras que el pronunciamiento cita 24-10-2025. No cambia ninguna regla aplicada, pero preferimos que la fuente citada sea la misma.

## 3. Decisiones D1 a D8

### D1 · Adulto mayor — CORREGIR → **Hecho** (con una pregunta)
- **Respuesta:** la condición se evalúa para el ejercicio en que la persona cumple 65 años; ya no se exige tenerlos al 1 de enero.
- **Evidencia:** pruebas con nacimiento el 1 de enero, el 31 de diciembre y un 29 de febrero (todas reconocen el beneficio) y con quien cumple 64 (no lo reconoce). Un documento posterior al ejercicio se rechaza.
- **Reliquidación al incorporar el dato tarde:** depende de D6 (ver abajo); las nóminas contabilizadas no se reabren.
- **Necesitamos de usted:** el sistema exige una acreditación del año (referencia y fecha) para reconocer al adulto mayor, aunque la edad se deduce de la fecha de nacimiento. ¿Debe seguir siendo obligatoria esa acreditación documental, o basta la fecha de nacimiento?

### D2 · Documento entregado después del 15 de enero — CORREGIR → **Parcial**
- **Respuesta:** se eliminó cualquier decisión discrecional. Un documento de discapacidad o de sustituto entregado después del 15 de enero **no aplica la exención** y bloquea el cierre, la contabilización y el XML. No existe casilla ni excepción manual para saltar el bloqueo, y no se aplica retroactivamente sobre nóminas cerradas.
- **Evidencia:** prueba de que un documento del 1 de febrero deja la exención en cero y el cierre bloqueado con el mensaje de regularización.
- **No hecho:** el **procedimiento escrito de regularización** (validación, fecha de efecto, retenciones futuras, conciliación anual). Sin él, cualquier regla que implementáramos sería una decisión nuestra, justo lo que el pronunciamiento prohíbe.
- **Necesitamos de usted:** la redacción de ese procedimiento (pasos, campos y fecha de efecto). Con eso lo convertimos en un expediente con control.

### D3 · Concurrencia de adulto mayor y discapacidad — ACEPTAR → **Hecho** (mejora pendiente)
- **Respuesta:** se aplica una sola vez la exención más favorable, nunca la suma; el tipo aplicado queda registrado en el anexo RDEP.
- **Evidencia:** pruebas de «mejor de las dos, nunca la suma» y de límite por la base disponible.
- **Pendiente propio:** conservar, como evidencia del expediente, el cálculo comparativo de la opción no aplicada. Hoy queda el tipo aplicado, no la comparación.

### D4 · Sustituto y cambio dentro del ejercicio — ACEPTAR CON CONDICIONES → **Hecho** (con una decisión)
- **Respuesta a sus condiciones:**
  - *Registrar identificación de la persona con discapacidad, del sustituto, porcentaje, documento y fechas:* el expediente verificado exige todos esos datos.
  - *Un solo sustituto por persona y beneficio usado una sola vez:* se rechaza la verificación si otro sustituto ya cubre a la misma persona en fechas que se solapan y si el mismo trabajador ya usa el beneficio para otra persona.
  - *Reemplazo durante 2026:* el beneficio se distribuye proporcional al tiempo acreditado de cada sustituto.
  - Sin expediente verificado, el sustituto no se aplica y bloquea el cierre.
- **Evidencia:** pruebas de expediente ausente, verificado, período parcial, dos sustitutos consecutivos, solapamiento rechazado, uso único del beneficio y verificación por otra persona.
- **Necesitamos de usted:** el motor trabaja con meses enteros, así que la proporción se calcula por **días acreditados sobre días del año, redondeada al mes más cercano** (181 días → 6 meses). ¿Acepta ese redondeo o prefiere otra regla?
- **Límite:** la verificación es documental e interna, por otra persona con rol de nómina; no sustituye la verificación ante la autoridad competente.

### D5 · Porcentaje de discapacidad y RDEP — CORREGIR → **Parcial**
- **Respuesta:** escala de 30 %–49 % → 60 %; 50 %–74 % → 70 %; 75 %–84 % → 80 %; 85 %–100 % → 100 %, sobre el doble de la fracción básica (24.416,00 al 100 %; 14.649,60 al 30 %). Menos de 30 % se rechaza. La exención de la base y la rebaja por gastos personales van **separadas** en el modelo: la rebaja aplicada nunca supera el impuesto causado y es la que usa el RDEP.
- **Sobre «tipo 00» y «tipo 03»:** no los homologamos ni fijamos por analogía. El tipo 00 no tiene descripción en el esquema y **no aplica exención**; el anexo declara pendiente la compatibilidad con el catálogo 2026 y el XML permanece como vista previa interna.
- **No hecho:** validar el archivo con el catálogo y el validador oficiales de 2026. Al corte, el portal muestra el programa 2026 pero la ficha y el catálogo visibles son de 2025.
- **Necesitamos de usted:** avisarnos cuando el SRI publique la ficha técnica y el catálogo 2026; entonces se carga y se valida.

### D6 · Cambios durante el año — ACEPTAR CON CONDICIONES → **Parcial**
- **Respuesta:** no se reabren nóminas contabilizadas. Una **huella** de datos tributarios, política, líneas e historial impide cerrar o contabilizar si algo cambió después de calcular; hay que recalcular antes. La **brecha** entre la retención mensual acumulada y el impuesto anual se muestra por trabajador en el anexo.
- **No hecho:** la reliquidación mensual acumulada (recalcular el impuesto causado y la rebaja, restar lo retenido y distribuir el saldo entre los meses futuros). Cambia la retención de cada mes y no la implementamos sin su criterio.
- **Necesitamos de usted:** el método de distribución (saldo dividido para los meses restantes, con qué redondeo y tratamiento del último mes) y casos de aceptación con resultado esperado.

### D7 · Límite de 100 canastas — RECHAZAR → **Hecho** (con un vacío señalado)
- **Respuesta:** aceptamos el rechazo. La referencia aislada ya **no reduce la retención ni habilita el tope** y bloquea el cierre. Solo se aplica con un expediente verificado que cubra **todo el ejercicio**; para una carga exige identificación, relación o dependencia económica, y se rechaza el doble uso de la misma carga. El sistema no emite diagnósticos ni guarda datos de salud: solo referencia, autoridad y vigencia.
- **Evidencia:** pruebas de referencia aislada sin efecto, vigencia parcial que no aplica, expediente completo que sí aplica y carga usada dos veces.
- **Vacío que reconocemos:** el pronunciamiento pide **rutas documentales separadas** para discapacidad y para enfermedad catastrófica, rara o huérfana. El expediente hoy distingue titular y carga, pero no esa condición. Está **no hecho**; lo proponemos como campo obligatorio con su propia lista de autoridades y documentos.
- **Necesitamos de usted:** la lista de autoridades y documentos válidos para cada condición, y confirmar si la verificación documental interna (por otra persona) le parece suficiente como «validación documental» mientras no exista consulta a la fuente oficial.

### D8 · Ingresos y retenciones del empleador anterior — CORREGIR → **Hecho** (alcance acotado)
- **Respuesta a sus tres exigencias:**
  - *Idempotente por trabajador, empleador de origen, ejercicio y documento, con versión y huella:* registrar dos veces la misma clave con los mismos datos no crea nada; con otros importes crea la versión siguiente. La huella es la del archivo, o la de los valores si no se adjunta.
  - *La rectificación sustituye a la anterior con bitácora, sin duplicar:* la versión anterior queda «sustituida» con su bitácora de cambios; nunca se edita ni se elimina, y solo puede haber una vigente por clave.
  - *Bloqueo con historia incompleta:* las novedades que declaran importes de otro empleador deben **conciliar** con el comprobante vigente; si no, se bloquean el cierre, la contabilización y el XML. Repetir el acumulado cada mes se detecta.
- **Evidencia:** pruebas de idempotencia, rectificación, hash de archivo, repetición mensual, faltante y descuadre.
- **Alcance real:** es un **registro** idempotente por formulario; no existe importación de archivos estructurados. El Formulario 107 no existe como salida del sistema; el XML del RDEP sigue siendo vista previa.
- **Pendiente externo:** entrega del comprobante por el trabajador (30 días) y su aceptación tributaria.

## 4. Casos 1 a 11

| Caso | Su decisión | Nuestra respuesta | Estado |
|---|---|---|---|
| 1 | Condicionar | Parámetros 2026 sellados con fuente, vigencia y huella; se prohíbe reutilizar valores de otro año | **Hecho** |
| 2 | Parcial | (12.677 − 12.208) × 5 % = **23,45** verificado con cálculo independiente. El saldo de 5,45 no se declara validado: falta demostrar gastos, cargas, límite y la rebaja de 18,00 | **Parcial**, como usted indica |
| 3 | Bloquear | Aviso persistente de que los beneficios propios no tienen matriz de incidencia; hoy es aviso, no bloqueo | **No hecho** |
| 4 | Condicionar | Cada período contabilizado se concilia con su asiento (débitos y créditos); una diferencia bloquea el XML. Falta conciliar saldos, devengo y pago | **Parcial** |
| 5 | Bloquear | D8 implementado: comprobante versionado, conciliación y rectificación sin duplicados; sin conciliación, el cierre se bloquea | **Hecho** (falta probarlo con un comprobante real) |
| 6 | Bloquear | Pruebas de adulto mayor, discapacidad, sustituto y gastos repetidas con D1–D7 corregidos, además de los ensayos 26–32 en demo | **Parcial** (faltan soportes reales) |
| 7 | Bloquear | Mismo insumo, mismo resultado (huella); consolidación anual idempotente; bitácora de comprobantes. Falta la reliquidación acumulada | **Parcial** |
| 8 | Mixto | Cambio salarial: la proyección anual se actualiza y la brecha de retención se muestra. Ausencias: **bloqueadas**, sin reglas definidas | **Parcial** |
| 9 | Bloquear | La base gravable del motor excluye décimos tercero y cuarto (no forman parte de la proyección); no hay prueba dedicada ni reglas de devengo, pago y mapeo RDEP para vacaciones y fondos de reserva | **No hecho** |
| 10 | Bloquear | Conciliación automática nómina ↔ asiento y retención acumulada ↔ impuesto anual, visible en el anexo. Falta el Formulario 107 y el validador oficial | **Parcial** |
| 11 | Mixto | Galápagos sin elegibilidad, residencia extranjera, convenio, impuesto asumido y otros ingresos **bloquean el cierre**; el factor 1,803 no se usa sin soporte | **Hecho** como bloqueo; las reglas de cada régimen no existen |

## 5. Requisitos mínimos para una nueva homologación

| Requisito | Respuesta |
|---|---|
| Corregir D1, D2, D5, D7, D8 y documentar D3, D4, D6 | D1, D5 (escala/rebaja), D7 y D8 corregidos; D2 y D6 con bloqueo pero sin el procedimiento; D3 y D4 documentados en este escrito |
| Tabla de parámetros 2026 inmutable y auditable | **Hecho:** sello con fuentes, vigencia y huella |
| Reporte reproducible por trabajador (ingresos proyectados, deducciones, exenciones, impuesto causado, rebaja, retenciones previas y saldo por meses) | **Parcial:** el anexo y los ensayos muestran base anual, exención, impuesto causado, rebaja aplicada, retenciones y la brecha; el **saldo distribuido en meses futuros** depende de D6 |
| Validar RDEP con catálogo y validador oficiales 2026 | **No hecho:** pendiente de la publicación del SRI; la salida se mantiene como vista previa y no afirmamos compatibilidad |
| Probar altas tardías, cambio de cargas, cambio de empleador, sustitución, rectificación, discapacidad desde 30 %, 100 canastas y duplicidades | **Parcial:** hay pruebas de documento tardío, cambio de cargas, D8, sustitución, revocación y nuevo expediente, escala desde 30 %, 100 canastas y doble uso. No hay prueba específica del alta tardía de un empleado en el año |
| Conciliar nómina, mayor, Formulario 107 y RDEP | **Parcial:** nómina ↔ asiento y retención ↔ impuesto anual; no existe Formulario 107 |
| Evidencia con versión, commit, base de pruebas y firma del responsable de ejecución | Versión y commit abajo; **la firma queda en blanco**: no la ponemos por usted ni por nadie |

## 6. Decisiones que necesitamos de usted

1. **D1:** ¿la acreditación documental del adulto mayor sigue siendo obligatoria?
2. **D2:** redacción del procedimiento de regularización de un documento tardío.
3. **D4:** ¿se acepta la proporción por días redondeada al mes más cercano?
4. **D6:** método de reliquidación de las retenciones futuras y casos de aceptación.
5. **D7:** autoridades y documentos de cada condición (discapacidad, catastrófica, rara, huérfana) y si la verificación interna por otra persona basta como validación documental.
6. **Caso 3:** matriz aprobada de incidencia por concepto (IR, IESS, décimos, vacaciones, reserva, contabilidad y RDEP).
7. **Caso 8 (ausencias) y caso 11:** reglas para cada régimen y para las ausencias.
8. **Fuente normativa:** confirmar la fecha de la última reforma de la LRTI que debe citarse.

## 7. Evidencia y cómo reproducirla

- **Versión y commit:** `erpec_payroll` 18.0.1.13.1; commit `a753558` en `codex/erpec26-implementacion`.
- **Pruebas:** 533 en Windows y 533 en Linux (CI 35664339580, cinco trabajos aprobados), 0 fallos y 0 errores; 5 omisiones de tesorería que requieren la demo sembrada. El módulo de nómina pasó de 124 a 168 pruebas.
- **Matriz de pendientes:** en la aplicación, **Nómina → Matriz de aceptación DI25-03**; en `docs/DI25-03_MATRIZ_ACEPTACION.md`. Una prueba exige que cada control citado tenga pruebas que existan.
- **Demo:** base `erpec_demo` actualizada con respaldo previo (base, filestore y módulo); auditoría de solo lectura en verde (32 casos con referencia coincidente y sin problemas).
- **Reproducir:** `python scripts/test-integrated.py` (suite completa en base aislada) y `python scripts/verify-di25-demo-runner.py` (auditoría de la demo, solo lectura).
- **Menús nuevos:** Certificados de otro empleador, Expedientes de exención y Matriz de aceptación DI25-03.

## 8. Límites

Nada de lo anterior está homologado ni presentado al SRI. Los controles automáticos validan alcance y consistencia; no reemplazan su criterio, la verificación ante la autoridad competente ni una absolución vinculante de consulta del SRI. Los datos de la demo son sintéticos.
