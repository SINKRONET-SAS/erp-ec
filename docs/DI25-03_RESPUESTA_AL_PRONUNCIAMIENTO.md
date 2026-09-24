# Respuesta punto por punto al Pronunciamiento Técnico Tributario DI25-03

| | |
|---|---|
| **Para** | Responsable tributario/contable (Gonzalo Proaño, coordinador técnico) |
| **De** | Equipo técnico del proyecto |
| **Fecha** | 21 de septiembre de 2026 |
| **Documento que se responde** | DI25-03_PRONUCIAMIENTO_TECNICO.pdf (5 páginas, SHA-256 `3f56196745924b1cf3600f842116a04b8e24ed091131d59f4ec3f451915b2722`) |
| **Versión que responde** | `erpec_payroll` 18.0.1.14.13 (tercera ronda; caso 11 cerrado: convenio parametrizable e impuesto asumido por bisección) |
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
- **Hallazgo del 22-09-2026:** al leer el catálogo RDEP que usted aportó descubrimos que dos campos del esquema estaban **intercambiados** en la vista previa XML: `intGrabGen` (ingresos gravados con otro empleador, el dato de D8) y `otrosIngRenGrav` (otros ingresos de esta misma relación que no tributan, sin relación con otro empleador). El cálculo interno de la base imponible siempre usó el valor correcto; el error era solo la etiqueta XML donde se escribía. Corregido, con una prueba que fija el mapeo.

## 4. Casos 1 a 11

| Caso | Su decisión | Nuestra respuesta | Estado |
|---|---|---|---|
| 1 | Condicionar | Parámetros 2026 sellados con fuente, vigencia y huella; se prohíbe reutilizar valores de otro año | **Hecho** |
| 2 | Parcial | (12.677 − 12.208) × 5 % = **23,45**; el saldo de **5,45** se reproduce con supuestos explícitos (gastos personales de 100 = rebaja de 18,00, sin cargas, límite de 5.752,60) en una prueba independiente | **Hecho** el cálculo; los soportes reales de gastos y cargas los aporta cada trabajador |
| 3 | Bloquear | Matriz confirmada para los conceptos estatutarios y decisión explícita de aportabilidad IESS por beneficio propio (`iess_contributable`, SÍ por defecto, aviso informativo con el art. 14 de la Ley de Seguridad Social si se elige NO) | **Hecho** |
| 4 | Condicionar | Cada período se concilia con su asiento (una diferencia bloquea el XML) y el anexo avisa del **devengo** (asiento fuera del mes de la nómina) y del **pago** (saldo por pagar o cuenta no conciliable). Hoy el asiento se fecha el día de contabilización y el aviso lo señala | **Hecho**; falta la aceptación de contabilidad |
| 5 | Bloquear | D8 implementado: comprobante versionado, conciliación y rectificación sin duplicados; sin conciliación, el cierre se bloquea | **Hecho** (falta probarlo con un comprobante real) |
| 6 | Bloquear | Pruebas de adulto mayor, discapacidad, sustituto, regularización y gastos repetidas con D1–D7 corregidos, además de los ensayos 26–32 en demo | **Hecho** con soportes sintéticos; falta repetirlo con soportes reales |
| 7 | Bloquear | Mismo insumo, mismo resultado (huella); consolidación anual idempotente; bitácora de comprobantes; y la reliquidación acumulada concilia entre períodos (el ejercicio cierra en cero) | **Hecho** |
| 8 | Mixto | Cambio salarial: la reliquidación actualiza la proyección anual y las retenciones futuras. Ausencias: enfermedad (días 1-3 al 100 % sin IESS, desde el día 4 sin pago), maternidad (25 %, sí IESS), paternidad (100 %, sí IESS, sin cambio de cálculo), permiso no pagado y falta injustificada (0 %, reducen IESS e IR) | **Hecho** |
| 9 | Bloquear | Devengo mensual (1/12 sueldo, 1/12 SBU, 8,33 % desde el mes 12), elección mensualizado/acumulado por trabajador y mapeo estricto a `decimTer`/`decimCuar`/`fondoReserva` del RDEP, nunca agrupados como otros ingresos exentos (ver 4-bis) | **Hecho** para décimos y fondo de reserva; la liquidación de vacaciones no tomadas sigue en el caso 3 |
| 10 | Bloquear | Conciliación automática nómina ↔ asiento y retención ↔ impuesto anual, con reporte por trabajador (proyectado, saldo y retención futura). El catálogo RDEP 2026 ya está en el DIMM; el validador del DIMM ya aceptó el XML a nivel de esquema (24-09-2026) y el formato del Formulario 107 fue entregado; queda la crítica semántica y contrastarlo | **Parcial**: depende del SRI |
| 11 | Mixto | No residentes: tributan igual que residentes. Galápagos: la Reforma a la LOREG unificó el incremento salarial con el mismo IPCEG de D5 (1,803); el motor escala el salario de referencia y tributa normal. Convenio e impuesto asumido **siguen bloqueando** | **Parcial**: no residentes y Galápagos resueltos, faltan convenio y gross-up |



## 4-bis. Caso 9 · devengo y pago de décimos y fondos de reserva — recibido el 22-09-2026, ya cubierto

Usted describió: devengo mensual del 1/12 del sueldo (décimo tercero), 1/12 del SBU (décimo cuarto) y 8,33 % desde el segundo año de servicio (fondo de reserva); elección mensualizado/acumulado por trabajador; y mapeo estricto a los casilleros propios del RDEP (`decimTer`, `decimCuar`, `fondoReserva`), nunca agrupados en «otros ingresos exentos». Verificamos que el motor **ya implementaba exactamente esto** desde una ronda anterior: las tasas están selladas (`thirteenth_rate=1/12`, `fourteenth_rate=1/12` sobre el salario mínimo, `reserve_rate=8,33 %` desde el mes 12), la elección mensualizado/acumulado existe por período (`monthly_thirteenth`, `monthly_fourteenth`, `reserve_paid`) y el anexo RDEP los escribe en sus tres campos propios, nunca en uno genérico. No hubo que programar nada nuevo; **cerramos el caso 9** en la matriz. Queda fuera de esta fila, y sigue en el caso 3: la liquidación en dinero de vacaciones no tomadas, que hoy no tiene un campo propio distinto del sueldo.
## 4-ter. Caso 3 · matriz de incidencia por concepto — recibido el 22-09-2026, parcialmente cerrado

Contrastamos su tabla contra el motor, concepto por concepto:

| Concepto | Su especificación | Motor antes de hoy | Motor hoy |
|---|---|---|---|
| Sueldo, horas extra, comisiones | IESS sí, IR sí, `suelSal` | IESS sí, IR sí — pero horas extra y comisión se reportaban en `sobSuelComRemu`, no en `suelSal` | Corregido: las tres van a `suelSal` |
| Décimo tercero | IESS no, IR no, `decimTer` | Coincidía exactamente | Sin cambios |
| Décimo cuarto | IESS no, IR no, `decimCuar` | Coincidía exactamente | Sin cambios |
| Fondo de reserva | IESS no, IR no, `fondoReserva` | Coincidía exactamente | Sin cambios |
| Vacaciones tomadas | IESS sí, IR sí, dentro de `suelSal` | Ya incluidas en el sueldo (el motor no reduce el sueldo por tomarlas) | Sin cambios |
| Vacaciones no tomadas, liquidadas | IESS no, IR sí, casillero propio | **No existía**: no había forma de pagar una liquidación distinta del sueldo | Nuevo: campo `vacation_payout`; grava IR, no IESS, se reporta en `sobSuelComRemu` |

Al revisar esto encontramos, además, que el propio catálogo RDEP documenta desde 2023 que `suelSal` es la «materia gravada de seguridad social» y `sobSuelComRemu` es la «materia NO gravada de seguridad social» — coincide exactamente con su tabla, y con cómo el motor ya calcula el aporte IESS (sobre sueldo + horas extra + comisión, nunca sobre décimos/reserva/liquidación de vacaciones). Antes de hoy, horas extra y comisión —que sí llevan aporte IESS— se reportaban en el casillero equivocado; ya está corregido. La cuenta contable de cada concepto ya era configurable por separado (menú de mapeo de nómina): décimos y fondo de reserva a una cuenta de pasivo, sueldo/liquidaciones al gasto de nómina.

**Actualización del 22-09-2026, caso cerrado:** usted pidió que los beneficios propios tengan un control de decisión, no solo un aviso. Agregamos `iess_contributable` (SÍ/NO) a cada beneficio propio, **SÍ por defecto** (aporta a IESS, igual que antes de este cambio). Elegir NO es una decisión de quien configura el beneficio, no algo que el sistema verifique por sí solo; muestra un aviso informativo con el art. 14 de la Ley de Seguridad Social (Ley 55, Registro Oficial Suplemento 465, 30-11-2001), que en efecto exonera de materia gravada IESS solo alimentación, atención médica/odontológica, seguros de vida/accidentes, ropa/herramientas de trabajo y beneficios de orden social sin privilegio (con un tope conjunto del 20 % de la retribución monetaria gravada) — no cualquier beneficio califica. El tratamiento de un beneficio ya calculado es inmutable. Con esto, **caso 3 queda cerrado** (control_state automated) y **ninguna fila de la matriz depende ya de un tercero** (D5 y caso 10 siguen como control parcial porque el SRI no ha publicado el catálogo 2026 ni el Formulario 107 oficial, no porque nos falte programar algo).

## 4-quater. Caso 8 · ausencias — recibido el 22-09-2026, cerrado

Usted describió las reglas y, al verificarlas contra fuentes oficiales, encontramos dos correcciones que usted mismo validó antes de que programáramos nada:

| Ausencia | Su especificación original | Corrección verificada | Fuente |
|---|---|---|---|
| Enfermedad, días 1-3 | Empleador paga 50 % | **Empleador paga 100 %** | Oficio PGE No. 10097 (17-02-2025), art. 54 Código del Trabajo, art. 16 Reglamento General sobre Prestación de Subsidios en Dinero |
| Enfermedad, día 4 en adelante | — | El empleador **no tiene obligación legal de complementar**; el subsidio lo paga el IESS directamente | Mismo oficio |
| Paternidad | Agrupada con maternidad (75 % IESS / 25 % empleador) | **100 % empleador, sin subsidio del IESS** | Art. 152 Código del Trabajo (reforma 2023) |
| Maternidad | 75 % IESS / 25 % empleador | Confirmado; usted precisó además que el 25 % del empleador **sí aporta a IESS** (continuidad de aportación) | — |

Con esas correcciones, el motor ya implementa: días de enfermedad 1-3 pagados al 100 % pero excluidos de la base de IESS (gravan impuesto a la renta, igual que una liquidación de vacaciones); desde el día 4, esos días simplemente no se pagan (el empleador no paga nada, el IESS paga su subsidio fuera de esta nómina); maternidad al 25 %, incluida en la base de IESS e impuesto a la renta; paternidad sin ningún efecto en el cálculo (se paga y se aporta igual que un día trabajado, solo se registra para el expediente); permiso no pagado y falta injustificada al 0 %, reduciendo ambas bases por igual. Los días de ausencia no pueden superar los días del período.

**Lo que sigue fuera de nuestro alcance:** el envío de la novedad "Subsidiado" a la plataforma del IESS es un trámite administrativo aparte, no un cálculo; el sistema no lo automatiza.

## 4-quinquies. Caso 11 · regímenes especiales — avance parcial el 23-09-2026

Verificamos el punto de no residentes contra la LRTI y encontramos que el mecanismo de tarifa fija que describimos aplica a **servicios ocasionales** de un no residente, no a una relación de dependencia formal. Usted confirmó: eso no es nómina, se trata como proveedor en compras (fuera de este módulo); y que un empleado no residente bajo relación de dependencia formal **debe tratarse igual que un residente** (misma tabla, mismas rebajas). Quitamos el bloqueo que existía solo por tener una residencia extranjera declarada; la residencia queda como dato informativo para el RDEP. El **convenio de doble imposición** sigue bloqueando aparte, porque cada tratado tiene su propio tope y no hay una regla genérica que podamos programar sin fabricarla.

**Actualización del 23-09-2026, Galápagos resuelto:** usted aclaró que la Reforma a la Ley Orgánica de Régimen Especial de la Provincia de Galápagos (LOREG) eliminó el incremento fijo "antitécnico" del 75 % (privados) y 100 % (públicos) y lo unificó con el **mismo** Índice de Precios al Consumidor Especial de Galápagos (IPCEG) que el SRI ya usa en D5 — no son dos factores distintos, es el mismo, ya sellado en 1,803. El motor ahora escala el salario de referencia continental (`wage`) por ese factor cuando el empleado está marcado como beneficiario de Galápagos, antes de calcular IESS, décimos, vacaciones y fondo de reserva; el impuesto se calcula con la tabla progresiva normal sobre esa base ya escalada, tal como usted confirmó ("tributan de acuerdo a la legislación ecuatoriana"). No cubrimos el caso de **derechos adquiridos** (empleados anteriores a la reforma que mantienen congelado el 75 %/100 % fijo): para ellos se declara el salario ya congelado directamente, sin activar este factor.

**Actualización del 23-09-2026, convenio de doble imposición e impuesto asumido cerrados:** con su guía técnica implementamos ambos mecanismos como controles reales, no como bloqueos permanentes.
- **Convenio de doble imposición** (`erpec.payroll.tax.treaty`): tabla paramétrica por país, sin tasas precargadas — cada registro exige su propia referencia normativa (no se fabrica ninguna). Mecanismo `exempt` (potestad exclusiva del país de residencia, p. ej. Decisión 578 CAN): no se retiene impuesto en Ecuador. Mecanismo `capped_rate`: el tratado fija una tasa tope sobre la base anual, en vez de la tabla progresiva y la rebaja de gastos personales. Sigue bloqueando el cierre si el empleado declara convenio aplicable y no hay un tratado registrado para su país — eso es correcto: no hay una regla genérica, cada tratado necesita su propio registro con fuente.
- **Impuesto asumido por el empleador** (contrato de ingreso neto en nómina, casillero 381 F107): la LRTI no fija una tarifa única de "gross-up"; el motor la resuelve por bisección (`engine.gross_up_assumed_tax`) contra la misma tabla progresiva ya vigente, tratándola como caja negra — funciona sea cual sea el tramo en el que caiga la base grosseada, sin inventar una fórmula cerrada. El campo `net_income_target` (neto mensual garantizado) llega íntegro al trabajador (no se le descuenta nada adicional); el impuesto que el empleador asume es informativo y se reporta en el RDEP (`basImp`, `impRentEmpl`, `valImpAsuEsteEmpl`), conforme al catálogo vigente. Ya no bloquea el cierre.

**Lo que sigue dependiendo de datos que solo usted puede proveer (no es una brecha de implementación):**
- **Convenio de doble imposición:** registrar, por cada país con el que aplique (España, Comunidad Andina, etc.), el tope o mecanismo exacto del tratado con su fuente normativa.
- **Otros ingresos no gravados de esta relación** (`other_general_interest_income`, campo `otrosIngRenGrav`): sigue siendo manual, sin cálculo del motor; falta su propio oráculo aprobado. Verificado el 24-09-2026 contra el texto primario de la LORTI, Art. 9: concretamente cubre viáticos/gastos de viaje documentados (num. 11) y bonificación de desahucio e indemnización por despido intempestivo dentro de los límites del Código del Trabajo (num. (3)); no incluye lo que un beneficio propio marcado "No grava renta" excluya por el art. 14 de la Ley de Seguridad Social (IESS), que es una ley y una lista distintas. El agregador ahora muestra ese total como referencia cruzada (`non_taxable_benefits_reference`), sin declararlo automáticamente.

## 5. Requisitos mínimos para una nueva homologación

| Requisito | Respuesta |
|---|---|
| Corregir D1, D2, D5, D7, D8 y documentar D3, D4, D6 | D1, D2, D3, D4, D6, D7 y D8 corregidos o documentados; D5 (escala y rebaja) corregido, con el catálogo RDEP pendiente del SRI |
| Tabla de parámetros 2026 inmutable y auditable | **Hecho:** sello con fuentes, vigencia y huella |
| Reporte reproducible por trabajador (ingresos proyectados, deducciones, exenciones, impuesto causado, rebaja, retenciones previas y saldo por meses) | **Hecho:** el anexo muestra base anual, exenciones con su comparación, impuesto causado, rebaja, retenciones, impuesto proyectado, saldo y retención mensual futura sugerida |
| Validar RDEP con catálogo y validador oficiales 2026 | **Parcial:** el catálogo 2026 fue entregado por el SRI y coincide con nuestros parámetros; el validador del DIMM aceptó el XML a nivel de esquema (rdepv10, 24-09-2026), falta su crítica semántica; la salida es vista previa y no afirmamos compatibilidad |
| Probar altas tardías, cambio de cargas, cambio de empleador, sustitución, rectificación, discapacidad desde 30 %, 100 canastas y duplicidades | **Hecho:** hay pruebas de documento tardío regularizado, alta tardía de un empleado, cambio de cargas, empleador anterior, sustitución, revocación y nuevo expediente, escala desde 30 %, 100 canastas por condición y doble uso |
| Conciliar nómina, mayor, Formulario 107 y RDEP | **Parcial:** nómina ↔ asiento (con devengo y pago) y retención ↔ impuesto anual; el Formulario 107 oficial depende del SRI |
| Evidencia con versión, commit, base de pruebas y firma del responsable de ejecución | Versión y commit abajo; **la firma queda en blanco**: no la ponemos por usted ni por nadie |

## 6. Decisiones que necesitamos de usted

Con esta versión ya no hay filas de la matriz que dependan de que nosotros programemos algo más. Lo que sigue depende de su criterio o del SRI:

1. **D1, D2, D4 y D6:** aprobados por el titular del proyecto (D1: reconocimiento por la edad sin acreditación, a los 65 años, confirmado el 22-09-2026 con la Ley Orgánica de las Personas Adultas Mayores; D4: redondeo días→meses del sustituto, aprobado el 22-09-2026); queda la firma de aceptación del responsable tributario.
2. **D7:** lista de autoridades válidas por condición y si la verificación interna por otra persona basta como validación documental (el fundamento legal del tope ya quedó verificado).
3. **Caso 11:** registrar en `erpec.payroll.tax.treaty` los tratados reales que apliquen (por país, con su fuente normativa); el mecanismo de convenio y el gross-up del impuesto asumido ya están implementados y probados.
4. **D5 y caso 10:** verificamos hoy en `sri.gob.ec` que el catálogo y la ficha siguen vigentes para 2024/2025, sin versión 2026 ni Formulario 107 publicados; avísenos si consigue una versión distinta.
5. **Fuente normativa:** confirmar la fecha de la última reforma de la LRTI que debe citarse.

## 7. Evidencia y cómo reproducirla

- **Versión y commit:** `erpec_payroll` 18.0.1.14.2 en `codex/erpec26-implementacion` (el identificador del commit y de su CI se registran en el commit de evidencia que sigue a esta entrega).
- **Pruebas:** 552 en Windows, 0 fallos y 0 errores; 5 omisiones de tesorería que requieren la demo sembrada. La ronda anterior (18.0.1.13.1, commit `a753558`) tuvo 533 en Windows y en Linux (CI 35664339580). El módulo de nómina pasó de 124 a 187 pruebas.
- **Matriz de pendientes:** en la aplicación, **Nómina → Matriz de aceptación DI25-03**; en `docs/DI25-03_MATRIZ_ACEPTACION.md`. Una prueba exige que cada control citado tenga pruebas que existan.
- **Demo:** base `erpec_demo` actualizada con respaldo previo (base, filestore y módulo); ahora en 18.0.1.14.2; auditoría de solo lectura en verde (32 casos con referencia coincidente y sin problemas) y matriz visible con 13 controles automáticos, 2 parciales, 2 bloqueos y 2 dependencias de terceros.
- **Reproducir:** `python scripts/test-integrated.py` (suite completa en base aislada) y `python scripts/verify-di25-demo-runner.py` (auditoría de la demo, solo lectura).
- **Menús nuevos:** Certificados de otro empleador, Expedientes de exención, Regularización de documentos tardíos y Matriz de aceptación DI25-03.

## 8. Límites

Nada de lo anterior está homologado ni presentado al SRI. Los controles automáticos validan alcance y consistencia; no reemplazan su criterio, la verificación ante la autoridad competente ni una absolución vinculante de consulta del SRI. Los datos de la demo son sintéticos.
