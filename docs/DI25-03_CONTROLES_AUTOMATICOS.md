# DI25-03 — Respuesta al pronunciamiento y controles automáticos

El pronunciamiento recibido devuelve la versión 18.0.1.11.0 para corrección. No homologa DI25-03. El encabezado identifica a Gonzalo Proaño como coordinador técnico; los campos finales de firma permanecen vacíos. La recepción del documento no se registra como firma verificada ni como aceptación.

Documento fuente: archivo local DI25-03_PRONUCIAMIENTO_TECNICO.pdf, cinco páginas, SHA256 `3f56196745924b1cf3600f842116a04b8e24ed091131d59f4ec3f451915b2722`. Se revisaron su texto y las cinco páginas renderizadas. No se publica el PDF en el repositorio. Sus enlaces «Abrir fuente oficial» no contienen anotaciones de enlace en el archivo recibido.

## Contraste del incremento anterior

- `c47359d8eb9fac9d7132d0a5c53f17f9156e0ce5`: CI [35645129313](https://github.com/SINKRONET-SAS/erp-ec/actions/runs/35645129313) comprobado directamente: cinco trabajos aprobados y registro Linux con 478 pruebas, cero fallos y errores.
- `61bfdb2bfea60b94dc9fbc0bf92029ab03f8fe92`: solo documentación y gobierno, con `[skip ci]`; no introduce otra versión del código.
- Registro Windows histórico: hash coincidente con la evidencia publicada. Respaldo `.cache/windows/backups/di25-exemptions-20260921T193040Z/database.dump`: hash coincidente `2613d643938045dd3a173183fd99a425b566dc0098c95451081bf3e852546ee2`.
- Comprobación actual independiente: módulo 18.0.1.11.0, 32 ejemplos coincidentes y formularios de empleado, período, ensayo y agregador compilables. Los conteos económicos son 29 asientos, 134 apuntes, ocho períodos y nueve líneas.
- Las huellas anteriores no publican consulta ni serialización. No se afirma que la auditoría nueva reproduzca esos hashes: conserva su propio algoritmo explícito y compara antes/después bajo ese mismo algoritmo. El respaldo y el resultado histórico contienen las huellas originales iguales.
- Las 478 pruebas acreditan la ejecución anterior, pero algunas expectativas incorporaban justamente las reglas observadas por el experto. Se corrigieron esas expectativas con casos negativos y límites explícitos.

## Cambios ejecutables del incremento 18.0.1.12.0

| Observación | Control o corrección | Límite pendiente |
|---|---|---|
| D1: cumplir 65 durante el año | La condición de edad se evalúa para el ejercicio completo; pruebas de enero, diciembre y nacimiento bisiesto. No exige cumplirlos al 1 de enero. Rechaza documento posterior al ejercicio. | Desde 18.0.1.14.1 (criterio del titular, 21-09-2026) el adulto mayor se reconoce por la edad, sin acreditación documental. La edad mínima es 65 años (ley y sello); se espera aclaración sobre una mención de 60. |
| D2: documento tardío | Detecta fecha posterior al 15 de enero para discapacidad/sustitución; no aplica la exención y bloquea cierre/contabilización y XML. Indica regularización documentada. | Falta implementar el expediente de regularización con efecto futuro. No hay casilla para saltar el bloqueo. |
| D3: concurrencia | Conserva el máximo, nunca la suma, y sus pruebas de importes independientes. | Acreditación auténtica y trazabilidad comparativa completa del expediente. |
| D4: sustituto | Una referencia y meses ya no habilitan el beneficio. Detecta otra ficha con el mismo titular y año; no revela el nombre de otra empresa/persona. Bloquea hasta acreditar vigencias y unicidad. | Registro temporal de sustitución, reemplazos y verificación ante autoridad. |
| D5: escala, rebaja y catálogo | Mantiene pruebas de la escala 30/49/50/74/75/84/85/100. Separa rebaja calculada y aplicada; esta última no supera el impuesto causado. El RDEP usa la aplicada. Aviso persistente sobre catálogo 2026 pendiente. | Validación oficial RDEP 2026; no se homologan códigos por analogía. |
| D6: cambios durante el año | Huella de datos tributarios, política, líneas e historial contabilizado. Si cambian después del cálculo, impide cerrar o contabilizar sin recalcular. | Sigue pendiente la reliquidación mensual acumulada; recalcular la proyección no equivale a implementarla. |
| D7: 100 canastas | La referencia aislada deja de reducir la retención operativa. Bloquea cierre/contabilización y XML; los ensayos aritméticos siguen disponibles y separados. | Expediente verificable de autoridad, identidad, vigencia, vínculo y dependencia; no se inventa consulta oficial ni se registran diagnósticos. |
| D8: otro empleador | Detecta valores anteriores sin conciliación certificada; bloquea cierre/contabilización. Señala IESS mayor que ingresos. El XML conserva su bloqueo. | Importación idempotente/versionada por trabajador, origen, año y documento; rectificaciones sustitutivas y conciliación. |
| Casos 3 y 11 | Aviso sobre matriz laboral de beneficios; bloqueo de Galápagos sin elegibilidad, convenio, residencia extranjera e impuesto asumido no cubiertos. | Matriz aprobada por concepto y reglas específicas. |

Estos bloqueos son validaciones automáticas de alcance y consistencia. No equivalen a implementar los flujos que faltan. La autenticidad documental y la aceptación profesional siguen requiriendo una fuente autorizada; un campo de texto o una marca manual no las reemplazan.

## Segunda ronda 18.0.1.13.0: pendientes convertidos en controles automáticos

El titular pidió que los pendientes dejen de ser acciones manuales y pasen, en lo posible, a validaciones automatizadas. Esta ronda convierte en control ejecutable todo lo que no depende de una fuente externa. Cada control tiene pruebas de rechazo y aparece en la interfaz de nómina.

| Pendiente del pronunciamiento | Control automático | Dónde se ve | Lo que sigue siendo externo |
|---|---|---|---|
| Requisito 1 · parámetros 2026 inmutables y auditables (caso 1) | `parameters_seal.py` guarda la tabla, canasta 821,80, topes 7/9/11/14/17/20/100, IPCEG 1,803, escala de discapacidad, edad y plazo, con fuentes, vigencia y una huella SHA-256. Cualquier cambio sin resellar la huella falla. La política y las constantes del motor se contrastan con el sello antes de calcular (bloquea) y en el aviso del período. Coherencia interna de la tabla (±1 USD). Un ejercicio cercano sin sello avisa: no se reutilizan valores de otro año. | Aviso del período; el cálculo se bloquea si un ejercicio sellado se desvía | Cargar y sellar cada ejercicio nuevo con su fuente oficial |
| D8 · importación idempotente, versionada, con rectificaciones | Modelo `erpec.payroll.prior.employer`: clave trabajador + RUC de origen + ejercicio + documento; la misma clave con los mismos datos no crea nada; con otros importes crea la versión siguiente, sustituye a la anterior con bitácora y huella (SHA-256 del archivo o de los valores); nunca se edita ni se elimina. Índice único de una sola versión vigente. | Menú **Nómina → Certificados de otro empleador** | Que el trabajador entregue el comprobante (plazo de 30 días) |
| D8 · conciliación | Los importes de otros empleadores en las novedades deben coincidir con el comprobante vigente (suma del ejercicio, incluidos períodos contabilizados); repetir el acumulado cada mes se detecta; un comprobante no incorporado avisa. Bloquea cierre, contabilización y XML mientras no concilien. La huella del cálculo y del anexo incluye las versiones vigentes. | Aviso del período y del anexo RDEP | Aceptación tributaria del comprobante |
| D4 · sustituto, D7 · 100 canastas | Modelo `erpec.payroll.exemption.dossier`: documento, autoridad, identificación de la persona, vigencia dentro del ejercicio, grado (sustituto) o vínculo (carga). Verificación por otra persona con rol de nómina (segregación de funciones). Se rechaza la verificación si hay solapamiento del mismo sustituido, si el sustituto ya usa el beneficio para otra persona o si la misma carga figura en otro expediente. El sustituto se aplica proporcional a los días acreditados (redondeo al mes más cercano); las 100 canastas exigen cobertura de todo el ejercicio. Verificado es inmutable; se revoca con motivo. | Menú **Nómina → Expedientes de exención** | Consulta a la autoridad competente: la verificación interna la deja escrita y no la sustituye |
| Caso 10 · conciliación nómina, mayor, RDEP | Cada período contabilizado se recalcula contra su asiento (débitos y créditos); una diferencia bloquea el XML. Por trabajador se muestra la brecha entre la retención mensual acumulada y el impuesto anual (D6). | Aviso del anexo RDEP | Reliquidación mensual acumulada (no implementada, ver abajo) |

Corrección del ejecutor de pruebas: cada corrida usa su propio puerto HTTP. CODEX había lanzado dos suites a la vez y la segunda falló por cuatro errores `TestHealth`, que compartían el puerto 8069; no era un defecto del producto.

## Tercera ronda 18.0.1.14.0: cierre de las filas parciales

El titular pidió terminar las filas parciales para poder avanzar. Todo lo que el propio pronunciamiento especifica quedó como control ejecutable; lo que depende de un tercero se dejó explícito.

| Fila | Qué se cerró | Cómo |
|---|---|---|
| **D6 · reliquidación acumulada** | Cada mes recalcula sobre lo acumulado el impuesto causado y la rebaja, resta lo ya retenido (y lo retenido por el empleador anterior certificado) y reparte el saldo entre los meses que faltan. Nunca es negativa; no reabre nóminas. Sin historial rige la proyección anual de siempre, así que los cálculos existentes no cambian. | `engine.calculate` con `prior_*` y `other_*`; la línea toma el historial contabilizado y los comprobantes vigentes. Un año con aumento salarial en el mes 7 cierra con diferencia cero. |
| **D2 · documento tardío** | El procedimiento del pronunciamiento hecho expediente: fundamento registrado, validación realizada, fecha de efecto que nunca cae en un mes contabilizado y verificación por otra persona. Antes de la fecha de efecto la exención no se aplica (aviso); desde ella entra en la reliquidación. | `erpec.payroll.exemption.regularization`, menú **Regularización de documentos tardíos**. |
| **D3 · comparación** | El anexo RDEP conserva el importe de cada exención acreditada y la que se aplicó. | Campo `exemption_comparison` de la línea del anexo. |
| **D7 · rutas separadas** | Discapacidad (con su grado), enfermedad catastrófica, rara y huérfana son condiciones distintas y obligatorias en el expediente de 100 canastas. | Campo `condition` del expediente. |
| **Caso 2** | El saldo de 5,45 se reproduce con supuestos explícitos: gastos de 100 (rebaja de 18,00), sin cargas y límite de 5.752,60. | Prueba independiente. |
| **Caso 4** | El anexo avisa del devengo (asiento fuera del mes de la nómina) y del pago (saldo por pagar o cuenta no conciliable), además de bloquear diferencias de débitos y créditos. | `_settlement_notes` en el anexo. |
| **Caso 8** | El cambio salarial actualiza proyección y retenciones futuras (probado). Las ausencias no se modelan: el estado pasa a bloqueo. | Prueba de aumento y de alta tardía. |
| **Reporte por trabajador (requisito 5)** | El anexo muestra impuesto proyectado, saldo por reliquidar y retención mensual futura sugerida, además de la brecha del ejercicio. | Campos `projected_tax_after_rebate`, `future_monthly_retention`, `months_remaining`. |

La proyección del saldo supone que el último mes se repite durante los meses que faltan; una sobre-retención no genera devolución automática, la deja visible. Ambos criterios salen del texto del pronunciamiento y se ponen a su confirmación.

### Lo que sigue sin poder cerrarse desde el sistema

- **D5 y caso 10:** el catálogo RDEP 2026 ya lo entregó el SRI (en el DIMM instalado; sus tablas de renta y canasta coinciden con los parámetros de nómina). El XML de vista previa pasa el validador oficial del plugin RDEP del DIMM a nivel de esquema (24-09-2026) y el formato del Formulario 107 (2023) ya fue entregado; queda la crítica semántica del DIMM y contrastar el 107. Mientras tanto el XML es vista previa y no se afirma compatibilidad.
- **Casos 3 y 9:** matriz de incidencia por concepto y reglas de devengo y pago de décimos, vacaciones y fondos de reserva. Requieren reglas aprobadas.
- **Caso 8 (ausencias) y caso 11:** requieren reglas y parametrización aprobadas para cada régimen.
- **D1:** resuelto por el titular el 21-09-2026: el adulto mayor se reconoce por la edad que resulta de la fecha de nacimiento, sin acreditación documental (18.0.1.14.1). Queda por aclarar si la edad mínima es 65 años (vigente) o 60.
- **Consulta a la autoridad y aceptación externa:** la verificación de expedientes y regularizaciones es documental e interna; no sustituye la consulta ni la firma del responsable.

## Acceso y verificación

En **Nómina → Períodos y novedades**, el formulario muestra «Controles tributarios automáticos» y el botón «Validar controles tributarios». El cierre y la contabilización invocan las validaciones en servidor; no dependen de pulsar el botón. En **Empleado → Anexo RDEP** se muestran incidencias documentales. En **Ensayos tributarios de renta**, «Rebaja aplicada» permite comprobar que el beneficio no produce impuesto negativo. El agregador advierte la limitación del catálogo oficial.

Ejecutar desde la raíz: `.venv/Scripts/python.exe -X utf8 scripts/verify-di25-demo-runner.py`. Devuelve salida 0 solo si el informe completo pasa; guarda `.cache/di25-demo-audit.json`. Un proceso interrumpido, sin informe o con diferencias devuelve salida 1.

El ejecutor invoca `scripts/verify-di25-demo.py` dentro de Odoo shell en `erpec_demo`. Rechaza otras bases o una empresa con RUC; comprueba los 32 identificadores, entradas, referencias independientes, parámetros fiscales 2026, carga de cuatro formularios y huellas económicas. Emite JSON y hace rollback. Si un ejemplo fue editado, informa la diferencia y lo conserva: no restablece datos para conseguir una aprobación.

La suite integrada incluye once pruebas nuevas específicas de estos controles. Otras siete pruebas del ejecutor comprueban que errores, discrepancias, informe incompleto, otra base o tiempo agotado no produzcan una aprobación falsa; también se ejecutan automáticamente en CI. La ejecución de validación y el despliegue se documentan en [la evidencia del incremento](evidencias/DI25/DI25-03-controles-automaticos.json); este documento no sustituye sus resultados.

## Fuentes y discrepancias

El [portal oficial RDEP](https://www.sri.gob.ec/formularios-e-instructivos1) muestra el programa 2026, pero ficha y catálogo para el ejercicio 2025. Se conserva el XML como vista previa interna.

La [codificación LRTI publicada por el SRI](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/12c884d5-c8d9-4171-becc-1513b990b87a/LEY_DE_REGIMEN_TRIBUTARIO_INTERNO_LRTI.pdf) indica última reforma 01-04-2026; difiere de la fecha 24-10-2025 mencionada en el pronunciamiento. La regla de D1 se implementa conforme al criterio expreso recibido, sin atribuir a la guía enlazada una verificación que el PDF no permite reproducir. El [comunicado SRI de actualización 2026](https://www.sri.gob.ec/detalle-noticias?idnoticia=1324&marquesina=1) confirma la necesidad de reliquidar retenciones futuras por cambios de ingresos, gastos o cargas; D6 sigue abierto.

## Ajuste 18.0.1.14.1: criterios del titular

- **D1:** el adulto mayor se reconoce por la fecha de nacimiento, sin acreditación documental; la discapacidad sigue exigiendo su documento y el aviso cuando falta.
- **D2 y D6:** aprobados por el titular el 21-09-2026, sin la firma del responsable tributario.
- **D5:** el XSD y el catálogo oficiales del SRI que aportó el titular se guardan sin cambios en `addons/erpec_payroll/xsd/Esquema_RDEP_2023.xsd` y `addons/erpec_payroll/reference/Catalogo_RDEP_2024.xlsx`, fijados por huella con pruebas. Verificado en vivo en `sri.gob.ec/formularios-e-instructivos1` (21-09-2026): siguen vigentes para 2024/2025, sin versión 2026 publicada. Al leer el catálogo se corrigieron los códigos de discapacidad (01 no aplica, 02 discapacidad, 03 sustituto, 04 cónyuge/pareja/hijo bajo cuidado, derogado desde 2024), que diferían del orden de la anotación del XSD; no se afirma compatibilidad 2026.

## Ajuste 18.0.1.14.7: caso 9 cerrado (décimos y fondos de reserva)

El titular envió su especificación del caso 9 (devengo mensual 1/12 sueldo/SBU, 8,33 % desde el segundo año, elección mensualizado/acumulado, mapeo estricto a decimTer/decimCuar/fondoReserva). El motor ya implementaba exactamente esto desde una ronda anterior; no hubo que programar nada nuevo, solo confirmarlo y cerrar la fila C09. Queda fuera: la liquidación en dinero de vacaciones no tomadas, sin campo propio hoy, que sigue en el caso 3.

## Ajuste 18.0.1.14.8: caso 3 (parcial) — matriz de incidencia estatutaria e IESS mal clasificado en horas extra/comisión

El titular envió su matriz de incidencia por concepto. Al contrastarla con el catálogo RDEP se encontró que `suelSal` (materia gravada de IESS, desde 2023) y `sobSuelComRemu` (materia NO gravada de IESS) también estaban mal usados: horas extra y comisión, que sí llevan aporte IESS, se reportaban en `sobSuelComRemu` en vez de `suelSal`. Corregido. Se agregó `vacation_payout` (liquidación de vacaciones no gozadas: grava IR, no IESS, reportado en `sobSuelComRemu`), el único rubro estatutario que faltaba. Los beneficios propios de cada empresa quedan fuera: no pueden clasificarse de forma genérica.

## Ajuste 18.0.1.14.9: caso 3 cerrado — decisión de aportabilidad IESS por beneficio propio

El titular pidió que los beneficios propios no queden solo con un aviso, sino con un control de decisión: si aportan a IESS o no, SÍ por defecto, con aviso informativo citando el art. 14 de la Ley de Seguridad Social (Ley 55, RO Suplemento 465, 30-11-2001) cuando se elige NO. Se agregó `iess_contributable` (SÍ/NO, inmutable una vez usado) a `erpec.payroll.benefit.type`; un beneficio con IR sí e IESS no recibe el mismo tratamiento que `vacation_payout` (una sola vez al año, `sobSuelComRemu`). Caso 3 queda **automated**; ninguna fila de la matriz depende ya de un tercero (D5 y caso 10 siguen parciales, pero porque el SRI no ha publicado, no por falta de código).

## Ajuste 18.0.1.14.10: caso 8 (ausencias) cerrado

El titular especificó las reglas de ausencias y, al verificarlas, se corrigieron dos puntos que el propio titular validó antes de programar: enfermedad días 1-3 al 100 % (no 50 %, Oficio PGE 10097) y sin obligación de complementar desde el día 4; paternidad 100 % del empleador sin subsidio del IESS (no comparte el esquema de maternidad, art. 152 Código del Trabajo). Con eso: enfermedad días 1-3 paga 100 % sin aporte a IESS (grava IR, mismo mecanismo que `vacation_payout`); desde el día 4 no se paga nada; maternidad 25 % y sí aporta a IESS; paternidad no cambia ningún cálculo; permiso no pagado y falta injustificada al 0 %, reducen IESS e IR por igual. Nuevos campos en `erpec.payroll.line`: `sick_days`, `maternity_days`, `paternity_days`, `unpaid_leave_days`, `unexcused_absence_days`. Caso 8 pasa a `automated`.

## Ajuste 18.0.1.14.11: caso 11 (regímenes especiales), avance parcial

Al verificar la pieza de no residentes se encontró que la tarifa fija que describíamos aplica a servicios ocasionales de un no residente (proveedor, fuera de nómina), no a una relación de dependencia formal. El titular confirmó que un no residente bajo relación de dependencia formal debe tratarse igual que un residente; se quitó el bloqueo que existía solo por tener residencia extranjera declarada (`ec_rdep_residence_country`), que ahora es dato informativo para el RDEP. El convenio de doble imposición sigue bloqueando aparte. Caso 11 sigue `blocked` en conjunto: faltan el tope por tratado del convenio, la fórmula de grosificación del impuesto asumido y la fuente de las tablas salariales de Galápagos del Consejo de Gobierno (distinta del IPCEG del SRI ya usado en D5).

## Ajuste 18.0.1.14.12: Galápagos resuelto en caso 11

El titular aclaró que la Reforma a la LOREG unificó el incremento salarial de Galápagos (antes 75 %/100 % fijo) con el mismo índice IPCEG que el SRI ya usa en D5 (1,803, ya sellado). El motor ahora escala `wage` (declarado como salario de referencia continental) por ese factor cuando `ec_rdep_ben_galpg='SI'`, antes de IESS, décimos, vacaciones y fondo de reserva; el impuesto se calcula con la tabla progresiva normal. Ya no bloquea por sí solo. No cubre derechos adquiridos de empleados anteriores a la reforma (se declara el salario congelado directo). Siguen bloqueando: convenio de doble imposición e impuesto asumido (gross-up).

## Ajuste 18.0.1.14.13: caso 11 cerrado — convenio de doble imposición y gross-up del impuesto asumido

Con la guía técnica del titular se implementaron los dos mecanismos que quedaban bloqueados en caso 11. **Convenio de doble imposición**: nuevo modelo `erpec.payroll.tax.treaty`, tabla paramétrica por país sin tasas precargadas (cada registro exige su propia referencia normativa, restringido a `group_payroll_manager`); mecanismo `exempt` anula el impuesto a la renta en Ecuador, `capped_rate` fija una tasa tope sobre la base anual en vez de la tabla progresiva y la rebaja de gastos personales. Sigue bloqueando el cierre si el empleado declara convenio aplicable y no hay tratado registrado para su país (dato pendiente, no una brecha de implementación). **Impuesto asumido por el empleador** (gross-up, contrato de ingreso neto en nómina, casillero 381 F107): la LRTI no fija una tarifa fija de grosificación; se agregó `engine.gross_up_assumed_tax`, que resuelve por bisección (50 iteraciones, sin tabla ni fórmula cerrada) el impuesto que el empleador debe asumir contra la misma tabla progresiva (`annual_income_tax`) ya vigente, para que el neto mensual garantizado (`net_income_target`, nuevo campo) llegue íntegro al trabajador sin descontarle nada adicional. El impuesto asumido resultante se reporta en el RDEP (`basImp`, `impRentEmpl`, `valImpAsuEsteEmpl`); se corrigió además `gross_base` en `action_build()` para sumar `employer_assumed_tax` a `basImp`, conforme a la fórmula del catálogo RDEP vigente (gap encontrado al aplicar esa misma fórmula). Caso 11 pasa a `automated`.

## Ajuste 18.0.1.14.6: D8 tenía dos campos RDEP intercambiados

Al analizar la matriz de incidencia por concepto que el titular envió para el caso 3, releímos el catálogo RDEP y encontramos que `intGrabGen` («ingresos gravados generados con otros empleadores», el dato real de D8) y `otrosIngRenGrav` («otros ingresos de esta misma relación que no constituyen renta gravada», sin relación con otro empleador) estaban intercambiados en la vista previa XML. El cálculo interno de la base imponible siempre usó el valor correcto; el error era solo la etiqueta XML. También se corrigió `ingGravConEsteEmpl` (informativo, cálculo automático del SRI) para que sume los seis campos que documenta el catálogo, en vez de solo el sueldo base. Ver `docs/ALCANCE_ATS_RDEP.md`.

## Ajuste 18.0.1.14.5: criterio de redondeo de D4 aprobado

El titular aprobó el criterio de redondeo días→meses para el sustituto (días acreditados / 365 x 12, al entero más cercano). No proviene de una norma: es una decisión de diseño porque el motor solo calcula por meses completos. Queda citada en `exemption_dossier.py`.

## Ajuste 18.0.1.14.4: fundamento legal de D7 (100 canastas)

El titular aportó el texto de la Ley Orgánica de Eficiencia Económica y Generación de Empleo (Registro Oficial, 20-12-2023). Su art. 7 sustituye el literal c) del segundo innumerado posterior al art. 10 de la LRTI: «el monto de la rebaja por gastos personales será equivalente al 18% del menor valor entre: los gastos personales declarados en el respectivo ejercicio fiscal y, el valor de la canasta familiar básica multiplicado por cien (100)». Confirma que el motor ya lo trataba correctamente como tope de la rebaja del 18 %, no como exención de la base. Se citó en `engine.py` y en la matriz. Sigue abierto: la lista de autoridades válidas por condición y si la verificación interna basta como validación documental.

Enlaces oficiales verificados el 22-09-2026 en `sri.gob.ec`:
- Ficha Técnica RDEP 2024 (también válida 2025): https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/b19da703-5b63-4e4b-8222-10d8e3d21c89/Ficha%20Tecnica%20RDEP%202024.pdf
- Catálogo RDEP vigente 2024 (también válido 2025): https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/df5866ad-80cd-4315-8f9f-da8998dae0d5/Cat%c3%a1logo%20vigente%20para%20el%20ejercicio%20fiscal%202024.xls
- Esquema RDEP.xsd (2023): https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/62837cc4-2de7-472c-9108-9b61bce8a38e/Esquema%20RDEP%202023.xsd
- Instructivo del Formulario 107: https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/1e4b0c85-f309-45b0-8a5e-dfd92a8e63d0/INSTRUCTIVO+FORMULARIO+107+COMPROBANTE+DE+RETENCIONES+EN+LA+FUENTE+DEL+IMPUESTO+A+LA+RENTA+POR+INGRESOS+DEL+TRABAJO+EN+RELACI_N+DE+DEPENDENCIA.pdf
- Formulario 107, formato de ejemplo 2023: https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/da612388-e7f6-4391-98e2-77f825d1d3a6/Formulario_107%20-%20Formato%202023.xls
- Página de formularios e instructivos (RDEP): https://www.sri.gob.ec/formularios-e-instructivos1

## Ajuste 18.0.1.14.3: edad mínima de D1 confirmada

El titular subsanó una mención anterior de 60 años y adjuntó la Ley Orgánica de las Personas Adultas Mayores (Registro Oficial 484, 9-V-2019). Su artículo 5 dice: «se considera persona adulta mayor aquella que ha cumplido los 65 años de edad». Coincide con la edad ya sellada en `parameters_seal.py` y con la LRTI art. 9 num. 12 ya citada en `engine.py`; no hubo cambio de lógica, solo se agregó la cita como segunda fuente legal y se cerró la fila D1 de la matriz sin pendiente técnico.

## Reversión y continuación

Se conserva el respaldo previo de base, filestore y módulo. No se reescriben resultados de períodos ni asientos existentes. Para revertir, detener únicamente la demo identificada por su configuración y restaurar conjuntamente base/filestore/módulo del mismo respaldo; no restaurar una base real ni mezclar versiones. Los nuevos campos de huella no se rellenan falsamente para cálculos antiguos: antes de cerrar deben recalcularse las novedades abiertas, o tramitarse una corrección cuando el estado lo requiera.

DI25-03 continúa **observado y no homologado**. Tras la tercera ronda solo quedan abiertas las filas que dependen del SRI (catálogo y validador RDEP 2026, formato del Formulario 107), de reglas aún no aprobadas (casos 3, 8 y 11) y de la confirmación de los criterios adoptados (D1, D2, D6). Después se repite la aceptación externa con evidencia del código exacto. DI25-04 no se inicia.
