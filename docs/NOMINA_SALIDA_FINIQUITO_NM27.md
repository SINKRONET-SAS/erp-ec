# NM27 — salida de empleados, rol proporcional y acta de finiquito

Nueva pasada de nómina contrastada con la referencia `C:\proyectos web\nuevo_nomina` (planes RSF26 «rol primero, finiquito después» y RCF26; solo lectura, sin modificar esa fuente). Antes de esta fase `erpec_payroll` no tenía salida, finiquito ni prorrateo por fecha de salida: el rol pagaba 30 días a cualquier empleado incluido en el período.

## Qué se incorporó (módulo `erpec_payroll` 18.0.1.15.0)

| Capacidad | Dónde |
|---|---|
| Rol proporcional: campo «Fecha de salida» en la línea del rol; el sueldo se prorratea hasta ese día sobre base 30. Una salida en el último día del mes (también febrero) paga el mes completo | `engine.days_worked`, `erpec.payroll.line.end_date` |
| Salida con dos modalidades: **rol primero** (el rol del mes de salida paga el proporcional y el acta no repite el sueldo) o **con finiquito** (el mes de salida no tiene rol y el acta paga el sueldo pendiente) | `erpec.payroll.exit`, menú Nómina → Salidas y finiquitos |
| Doble pago imposible: un rol del mes de salida con modalidad `con_finiquito`, un rol posterior a la salida o un rol sin la fecha de salida correcta se rechazan, al crear la línea y al calcular o emitir el acta | `PayrollExit._line_conflict` (autoridad única) y `Line._check_exit_rules` |
| Acta de finiquito: sueldo pendiente, décimo tercero y cuarto proporcionales, vacaciones no gozadas, fondo de reserva pendiente, indemnización por despido intempestivo y bonificación por desahucio; descuentos de IESS personal sobre el sueldo pendiente y otros descuentos manuales; PDF imprimible y numeración `FIN-AAAA-nnnnn` | `settlement.py`, `exit_report.xml` |
| Con rol primero el acta exige el rol del mes de salida ya cerrado; cualquier cambio de roles o datos tras el cálculo obliga a recalcular (huella SHA-256) | `action_approve` |
| Estados: borrador → calculado → acta emitida → pagado (con fecha y referencia informadas) / anulado | `erpec.payroll.exit.state` |
| Lo ya pagado por mensualización se descuenta: el motor ahora registra `thirteenth_paid`, `fourteenth_paid` y `reserve_paid` en el resultado del rol (aditivo; roles anteriores quedan en cero) | `engine.calculate`, `_paid_by_payroll` |

## Mejoras sobre la referencia

- Vacaciones: la referencia pagaba todo lo devengado en la relación sin restar los días gozados; aquí se descuentan los días gozados informados y el adicional por antigüedad se acumula por año (art. 69, hasta 15 días).
- Décimo cuarto: usa el régimen regional ya existente del empleado (Sierra/Amazonía o Costa/Insular) en lugar de aproximar por días de servicio; sin régimen definido el cálculo se rechaza.
- Fondo de reserva: se descuenta lo pagado directamente y lo ya acreditado en roles cerrados.
- Febrero y el día 31 se tratan de forma consistente en el prorrateo.

## Límites declarados

- Solo empresas y versiones DEMO (misma restricción que el cierre de nómina nativa); no se activa nómina real.
- No contabiliza el finiquito, no retiene impuesto a la renta, no archiva al empleado, no transmite pagos ni archivos bancarios.
- El IESS personal se calcula solo sobre el sueldo pendiente; vacaciones, desahucio e indemnización no llevan retención en este cálculo y requieren revisión laboral. La bonificación por desahucio usa años completos de servicio; el décimo tercero y cuarto no incorporan ingresos variables.
- Préstamos, anticipos y equipos pendientes se concilian a mano en «Otros descuentos».
- Causales con visto bueno, caso fortuito o fallecimiento no se calculan automáticamente.
- El acta es un documento interno; su legalización no se acredita aquí.

## Pruebas

`erpec_payroll/tests/test_exit_settlement.py`: prorrateo, días comerciales, vacaciones, modalidades, descuento de beneficios ya pagados, causales y validaciones, flujo completo rol primero, bloqueo con finiquito, rol que contradice la modalidad, recálculo, anulación y reimpresión del acta.

## Licencia por enfermedad (contraste con LE26 de la referencia)

Antes, `sick_days` pagaba siempre los tres primeros días al 100 % en cada mes (se reiniciaban si el reposo cruzaba de mes), nada desde el cuarto día, y no exigía acreditar el derecho al subsidio del IESS. Ahora, en la pestaña Ausencias de la línea del rol:

| Regla | Comportamiento |
|---|---|
| Sin evidencia | El cálculo se rechaza como «pendiente de revisión»; nunca se descuenta el 100 % por falta de datos. Se exige certificado (referencia y origen), calificación del derecho con respaldo y continuidad del episodio |
| Con derecho al subsidio | Días 1 a 3 del **episodio** al 100 % (los días previos certificados evitan reiniciar el conteo cada mes, también con recaídas); desde el día 4 paga el IESS y el empleador solo el complemento opcional documentado (0 % por defecto) |
| Sin derecho | El empleador paga el 50 % hasta 60 días por año; el saldo anual suma cierres anteriores del ejercicio más los días registrados fuera del sistema; al agotarse se rechaza y exige resolución de RR. HH. |
| Subsidio del IESS | Informativo (porcentaje 75/66, base y referencia); se muestra en el rol y **no** se suma al neto. Certificado particular exige constancia de validación del IESS para días subsidiados |
| Tratamiento fiscal | Se conserva la regla vigente: lo pagado por el empleador no aporta a IESS y grava renta (campo `sobSuelComRemu` del RDEP) |

Límites: no hay conexión con el IESS ni se valida la calificación, los tramos 70/73 o 182/185 ni los plazos de revalidación (se informan, no se infieren); el tope de 60 días es un parámetro operativo, no una interpretación confirmada del plazo legal de dos meses; sin aprobación cronológica por licencia ni expediente médico propios (el certificado se referencia, no se almacena). Las líneas con `sick_days` ya registradas deben completarse antes de recalcular; los cierres aprobados no cambian.
