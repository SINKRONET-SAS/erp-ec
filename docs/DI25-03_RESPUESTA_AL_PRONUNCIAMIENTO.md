# Respuesta punto por punto al Pronunciamiento Técnico Tributario DI25-03

| | |
|---|---|
| **Para** | Responsable tributario/contable (Gonzalo Proaño, coordinador técnico) |
| **De** | Equipo técnico del proyecto |
| **Fecha** | 21 de septiembre de 2026 |
| **Documento que se responde** | DI25-03_PRONUCIAMIENTO_TECNICO.pdf (5 páginas, SHA-256 `3f56196745924b1cf3600f842116a04b8e24ed091131d59f4ec3f451915b2722`) |
| **Versión que responde** | `erpec_payroll` 18.0.1.14.5 (tercera ronda; D1/D2/D5/D6/D7 según ajustes previos; D4 con su criterio de redondeo aprobado) |
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

### D1 · Adulto mayor — CORREGIR → **Hecho** (criterio del titular: por la edad, sin acreditación)
- **Respuesta:** la condición se evalúa para el ejercicio en que la persona cumple 65 años; ya no se exige tenerlos al 1 de enero.
- **Evidencia:** pruebas con nacimiento el 1 de enero, el 31 de diciembre y un 29 de febrero (todas reconocen el beneficio) y con quien cumple 64 (no lo reconoce). Un documento posterior al ejercicio se rechaza.
- **Reliquidación al incorporar el dato tarde:** depende de D6 (ver abajo); las nóminas contabilizadas no se reabren.
- **Criterio (titular, 21-09-2026; edad confirmada 22-09-2026):** el adulto mayor se reconoce **por la edad que resulta de la fecha de nacimiento, sin acreditación documental**. El sistema ya no la exige para este caso; la discapacidad sigue exigiendo su documento. La edad mínima es **65 años**, confirmada por el titular con la Ley Orgánica de las Personas Adultas Mayores art. 5 (Registro Oficial 484, 9-V-2019), coincidente con la ya sellada en parámetros y con la LRTI art. 9 num. 12; queda cerrada la duda por los 60 años planteada antes.

### D2 · Documento entregado después del 15 de enero — CORREGIR → **Hecho** (criterio confirmado por el titular del proyecto el 21-09-2026)
- **Respuesta:** un documento de discapacidad o de sustituto entregado después del 15 de enero **no se aplica ni permite cerrar la nómina** hasta que exista una **regularización verificada**. Es el procedimiento que describe su pronunciamiento, hecho expediente: fundamento registrado (criterio formal del responsable o pronunciamiento del SRI), validación realizada, **fecha de efecto que nunca puede caer en un mes ya contabilizado** y verificación por otra persona. Antes de la fecha de efecto la exención no se aplica (queda un aviso); desde ella entra en la reliquidación acumulada (D6), que recalcula las retenciones futuras. Los meses previos quedan sin exención y cerrados, y la diferencia se ve en la conciliación anual del RDEP. No hay casilla para saltar el control.
- **Evidencia:** pruebas de que el documento tardío bloquea sin regularización, de que en borrador no cuenta, de que antes de su fecha solo avisa y desde ella aplica, de que la retención del mes 3 se recalcula (2,00 en el ejemplo) sin tocar los meses 1 y 2, de que la fecha retroactiva se rechaza, de la segregación de funciones, de la coincidencia con la ficha y de la inmutabilidad y revocación con motivo.
- **Criterio:** procedimiento derivado del texto del pronunciamiento, aprobado por el titular del proyecto el 21-09-2026. El sistema **registra** el fundamento; no lo evalúa. La firma de aceptación del responsable sigue en blanco.

### D3 · Concurrencia de adulto mayor y discapacidad — ACEPTAR → **Hecho**
- **Respuesta:** se aplica una sola vez la exención más favorable, nunca la suma. El anexo RDEP conserva ahora la **comparación**: el importe de cada exención acreditada y la que se aplicó (por ejemplo, «elderly 12000.00; disability 14649.60 → aplicada: disability»).
- **Evidencia:** pruebas de «mejor de las dos, nunca la suma», de límite por la base disponible y de la comparación en el anexo.

### D4 · Sustituto y cambio dentro del ejercicio — ACEPTAR CON CONDICIONES → **Hecho** (criterio de redondeo aprobado por el titular, 22-09-2026)
- **Respuesta a sus condiciones:**
  - *Registrar identificación de la persona con discapacidad, del sustituto, porcentaje, documento y fechas:* el expediente verificado exige todos esos datos.
  - *Un solo sustituto por persona y beneficio usado una sola vez:* se rechaza la verificación si otro sustituto ya cubre a la misma persona en fechas que se solapan y si el mismo trabajador ya usa el beneficio para otra persona.
  - *Reemplazo durante 2026:* el beneficio se distribuye proporcional al tiempo acreditado de cada sustituto.
  - Sin expediente verificado, el sustituto no se aplica y bloquea el cierre.
- **Evidencia:** pruebas de expediente ausente, verificado, período parcial, dos sustitutos consecutivos, solapamiento rechazado, uso único del beneficio y verificación por otra persona.
- **Criterio (titular, 22-09-2026):** el motor trabaja con meses enteros, así que la proporción se calcula por **días acreditados sobre días del año, redondeada al mes más cercano** (181 días → 6 meses); es una decisión de diseño, no una regla legal, y el titular la aprobó. Queda citada en `exemption_dossier.py`.
- **Límite:** la verificación es documental e interna, por otra persona con rol de nómina; no sustituye la verificación ante la autoridad competente.

### D5 · Porcentaje de discapacidad y RDEP — CORREGIR → **Parcial**
- **Respuesta:** escala de 30 %–49 % → 60 %; 50 %–74 % → 70 %; 75 %–84 % → 80 %; 85 %–100 % → 100 %, sobre el doble de la fracción básica (24.416,00 al 100 %; 14.649,60 al 30 %). Menos de 30 % se rechaza. La exención de la base y la rebaja por gastos personales van **separadas** en el modelo: la rebaja aplicada nunca supera el impuesto causado y es la que usa el RDEP.
- **Catálogo oficial (21-09-2026):** el titular adjuntó el catálogo RDEP («Catálogo vigente para el ejercicio fiscal 2024») y el esquema XSD, ambos descargados del propio portal del SRI. Verificamos en vivo en `https://www.sri.gob.ec/formularios-e-instructivos1` que la Ficha Técnica y el Catálogo que publica el SRI hoy son, por nombre y tamaño (176 KB), los mismos archivos: siguen vigentes **«para el ejercicio fiscal 2024 (también válido para 2025)»**, sin una versión 2026 publicada, aunque el programa DIMM RDEP sí tiene una compilación de marzo de 2026. El catálogo quedó en `addons/erpec_payroll/reference/Catalogo_RDEP_2024.xlsx`, fijado por huella con una prueba.
- **Corrección de los códigos de discapacidad:** al leer la hoja TABLAS del catálogo encontramos que el orden real es **01 No aplica, 02 Discapacidad, 03 Sustituto, 04 Cónyuge/pareja/hijo bajo su cuidado**, distinto del que traía la anotación de texto del XSD (que usábamos antes). El motor, el formulario del empleado y el anexo ya usan el orden del catálogo. El código 04 aparece «vigente hasta el periodo 2023» en el propio catálogo: el motor lo rechaza para 2024 en adelante. El código 00 solo era válido antes de 2013 y también se rechaza. Cuatro pruebas nuevas fijan esto por huella contra el archivo del titular; si el SRI publica un catálogo distinto, fallarán hasta que se ajuste el código.
- **Sobre «tipo 00» y «tipo 04»:** no los homologamos ni fijamos por analogía; están explícitamente en el catálogo con las descripciones citadas arriba.
- **No hecho:** validar los demás campos del anexo (no solo el de discapacidad) contra el catálogo completo, y contra el Formulario 107 oficial; ambos permanecen como vista previa.
- **Necesitamos de usted:** avisarnos si consigue una versión 2026 distinta a la que verificamos hoy en el portal del SRI.

### D6 · Cambios durante el año — ACEPTAR CON CONDICIONES → **Hecho** (criterio confirmado por el titular del proyecto el 21-09-2026)
- **Respuesta:** implementada la **reliquidación mensual acumulada** que su pronunciamiento describe: cada mes se recalculan, sobre lo acumulado, el impuesto causado y la rebaja; se restan las retenciones ya efectuadas (y las certificadas del empleador anterior); y el saldo se reparte entre los meses que faltan. La retención nunca es negativa y no se reabren nóminas contabilizadas. Sin historial del ejercicio rige la proyección anual de siempre, de modo que los cálculos existentes no cambian. Una huella impide cerrar o contabilizar si algo cambió después de calcular.
- **Evidencia:** un ejercicio de 12 meses con un aumento salarial en el mes 7 retiene 170 durante seis meses y 260 durante los seis restantes, y cierra con diferencia **cero** entre el impuesto anual y lo retenido. Pruebas de sobre-retención (queda en cero, sin negativos), de ingresos certificados del empleador anterior y de alta tardía. El anexo muestra por trabajador el impuesto proyectado, el saldo por reliquidar y la retención mensual futura sugerida.
- **Criterio:** método aprobado por el titular del proyecto el 21-09-2026: **el último mes se repite durante los meses que faltan** y una sobre-retención **no genera devolución automática**, solo queda visible.

### D7 · Límite de 100 canastas — RECHAZAR → **Hecho** (con una consulta externa)
- **Respuesta:** aceptamos el rechazo. La referencia aislada ya **no reduce la retención ni habilita el tope** y bloquea el cierre. Solo se aplica con un expediente verificado que cubra **todo el ejercicio**, con la **condición acreditada por rutas separadas**: discapacidad (con su grado), enfermedad catastrófica, enfermedad rara y enfermedad huérfana son campos distintos y obligatorios. Para una carga exige identificación, relación o dependencia económica, y se rechaza el doble uso. El sistema no emite diagnósticos ni guarda datos de salud: solo referencia, autoridad, condición y vigencia.
- **Fundamento legal (aportado por el titular, 22-09-2026):** verificamos en el texto oficial que el titular adjuntó el art. 7 de la **Ley Orgánica de Eficiencia Económica y Generación de Empleo** (Registro Oficial, 20-12-2023), que sustituye el literal c) del segundo innumerado posterior al art. 10 de la LRTI: «el monto de la rebaja por gastos personales será equivalente al 18% del menor valor entre: los gastos personales declarados en el respectivo ejercicio fiscal y, el valor de la canasta familiar básica multiplicado por cien (100)». Confirma lo que el motor ya calculaba: **no es una exención de la base imponible**, es el tope de la rebaja del 18 %, igual mecanismo que el tope general por cargas familiares. Queda citado en `engine.py`.
- **Evidencia:** pruebas de referencia aislada sin efecto, vigencia parcial que no aplica, expediente completo que sí aplica, carga usada dos veces y cada condición como ruta propia.
- **Necesitamos de usted:** la lista de autoridades válidas por condición (hoy la autoridad se registra como texto libre; para discapacidad sería previsiblemente CONADIS y para catastrófica/rara/huérfana la autoridad sanitaria nacional, pero no lo asumimos sin su confirmación) y si la verificación documental interna por otra persona basta como «validación documental» mientras no exista consulta a la fuente oficial.

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
| 2 | Parcial | (12.677 − 12.208) × 5 % = **23,45**; el saldo de **5,45** se reproduce con supuestos explícitos (gastos personales de 100 = rebaja de 18,00, sin cargas, límite de 5.752,60) en una prueba independiente | **Hecho** el cálculo; los soportes reales de gastos y cargas los aporta cada trabajador |
| 3 | Bloquear | Aviso persistente de que los beneficios propios no tienen matriz de incidencia; hoy es aviso, no bloqueo | **No hecho** |
| 4 | Condicionar | Cada período se concilia con su asiento (una diferencia bloquea el XML) y el anexo avisa del **devengo** (asiento fuera del mes de la nómina) y del **pago** (saldo por pagar o cuenta no conciliable). Hoy el asiento se fecha el día de contabilización y el aviso lo señala | **Hecho**; falta la aceptación de contabilidad |
| 5 | Bloquear | D8 implementado: comprobante versionado, conciliación y rectificación sin duplicados; sin conciliación, el cierre se bloquea | **Hecho** (falta probarlo con un comprobante real) |
| 6 | Bloquear | Pruebas de adulto mayor, discapacidad, sustituto, regularización y gastos repetidas con D1–D7 corregidos, además de los ensayos 26–32 en demo | **Hecho** con soportes sintéticos; falta repetirlo con soportes reales |
| 7 | Bloquear | Mismo insumo, mismo resultado (huella); consolidación anual idempotente; bitácora de comprobantes; y la reliquidación acumulada concilia entre períodos (el ejercicio cierra en cero) | **Hecho** |
| 8 | Mixto | Cambio salarial: la reliquidación actualiza la proyección anual y las retenciones futuras (probado). Ausencias: el módulo **no las modela**; no hay cálculo que aceptar hasta que se definan sus efectos | Salarial **hecho**; ausencias **bloqueadas** |
| 9 | Bloquear | La base gravable del motor excluye décimos tercero y cuarto (no forman parte de la proyección); no hay prueba dedicada ni reglas de devengo, pago y mapeo RDEP para vacaciones y fondos de reserva | **No hecho** |
| 10 | Bloquear | Conciliación automática nómina ↔ asiento y retención ↔ impuesto anual, con reporte por trabajador (proyectado, saldo y retención futura). Falta el formato oficial del Formulario 107 y el validador RDEP 2026, que publica el SRI | **Parcial**: depende del SRI |
| 11 | Mixto | Galápagos sin elegibilidad, residencia extranjera, convenio, impuesto asumido y otros ingresos **bloquean el cierre**; el factor 1,803 no se usa sin soporte | **Hecho** como bloqueo; las reglas de cada régimen no existen |

## 5. Requisitos mínimos para una nueva homologación

| Requisito | Respuesta |
|---|---|
| Corregir D1, D2, D5, D7, D8 y documentar D3, D4, D6 | D1, D2, D3, D4, D6, D7 y D8 corregidos o documentados; D5 (escala y rebaja) corregido, con el catálogo RDEP pendiente del SRI |
| Tabla de parámetros 2026 inmutable y auditable | **Hecho:** sello con fuentes, vigencia y huella |
| Reporte reproducible por trabajador (ingresos proyectados, deducciones, exenciones, impuesto causado, rebaja, retenciones previas y saldo por meses) | **Hecho:** el anexo muestra base anual, exenciones con su comparación, impuesto causado, rebaja, retenciones, impuesto proyectado, saldo y retención mensual futura sugerida |
| Validar RDEP con catálogo y validador oficiales 2026 | **No hecho:** pendiente de la publicación del SRI; la salida es vista previa y no afirmamos compatibilidad |
| Probar altas tardías, cambio de cargas, cambio de empleador, sustitución, rectificación, discapacidad desde 30 %, 100 canastas y duplicidades | **Hecho:** hay pruebas de documento tardío regularizado, alta tardía de un empleado, cambio de cargas, empleador anterior, sustitución, revocación y nuevo expediente, escala desde 30 %, 100 canastas por condición y doble uso |
| Conciliar nómina, mayor, Formulario 107 y RDEP | **Parcial:** nómina ↔ asiento (con devengo y pago) y retención ↔ impuesto anual; el Formulario 107 oficial depende del SRI |
| Evidencia con versión, commit, base de pruebas y firma del responsable de ejecución | Versión y commit abajo; **la firma queda en blanco**: no la ponemos por usted ni por nadie |

## 6. Decisiones que necesitamos de usted

Con esta versión ya no hay filas de la matriz que dependan de que nosotros programemos algo más. Lo que sigue depende de su criterio o del SRI:

1. **D1, D2, D4 y D6:** aprobados por el titular del proyecto (D1: reconocimiento por la edad sin acreditación, a los 65 años, confirmado el 22-09-2026 con la Ley Orgánica de las Personas Adultas Mayores; D4: redondeo días→meses del sustituto, aprobado el 22-09-2026); queda la firma de aceptación del responsable tributario.
2. **D7:** lista de autoridades válidas por condición y si la verificación interna por otra persona basta como validación documental (el fundamento legal del tope ya quedó verificado).
3. **Caso 3 y caso 9:** matriz aprobada de incidencia por concepto y reglas de devengo y pago de décimos, vacaciones y fondos de reserva.
4. **Caso 8 (ausencias) y caso 11:** reglas para cada régimen y para las ausencias.
5. **D5 y caso 10:** verificamos hoy en `sri.gob.ec` que el catálogo y la ficha siguen vigentes para 2024/2025, sin versión 2026 ni Formulario 107 publicados; avísenos si consigue una versión distinta.
6. **Fuente normativa:** confirmar la fecha de la última reforma de la LRTI que debe citarse.

## 7. Evidencia y cómo reproducirla

- **Versión y commit:** `erpec_payroll` 18.0.1.14.2 en `codex/erpec26-implementacion` (el identificador del commit y de su CI se registran en el commit de evidencia que sigue a esta entrega).
- **Pruebas:** 552 en Windows, 0 fallos y 0 errores; 5 omisiones de tesorería que requieren la demo sembrada. La ronda anterior (18.0.1.13.1, commit `a753558`) tuvo 533 en Windows y en Linux (CI 35664339580). El módulo de nómina pasó de 124 a 187 pruebas.
- **Matriz de pendientes:** en la aplicación, **Nómina → Matriz de aceptación DI25-03**; en `docs/DI25-03_MATRIZ_ACEPTACION.md`. Una prueba exige que cada control citado tenga pruebas que existan.
- **Demo:** base `erpec_demo` actualizada con respaldo previo (base, filestore y módulo); ahora en 18.0.1.14.2; auditoría de solo lectura en verde (32 casos con referencia coincidente y sin problemas) y matriz visible con 13 controles automáticos, 2 parciales, 2 bloqueos y 2 dependencias de terceros.
- **Reproducir:** `python scripts/test-integrated.py` (suite completa en base aislada) y `python scripts/verify-di25-demo-runner.py` (auditoría de la demo, solo lectura).
- **Menús nuevos:** Certificados de otro empleador, Expedientes de exención, Regularización de documentos tardíos y Matriz de aceptación DI25-03.

## 8. Límites

Nada de lo anterior está homologado ni presentado al SRI. Los controles automáticos validan alcance y consistencia; no reemplazan su criterio, la verificación ante la autoridad competente ni una absolución vinculante de consulta del SRI. Los datos de la demo son sintéticos.
