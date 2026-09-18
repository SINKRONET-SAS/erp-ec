# ERPEC26-OP12 — Beneficios propios configurables por empresa y libro de anticipos/préstamos

## Origen

El titular señaló (verbatim): "los diferentes clientes en su proceso de nómina y contratación tienen diferentes beneficios, usar como referencia nuevo_nomina, ya que la parametrización no permite configurarlos según la necesidad de cada cliente... Igualmente para los anticipos." `erpec.payroll.policy` (OP10-A1) solo cubre parámetros LEGALES/nacionales (salario mínimo, tasas IESS, décimos, etc.), uniformes por ley para todas las empresas de un año — no existía ninguna capa para que cada cliente configure sus propios beneficios adicionales (bonos, subsidios) ni para llevar un libro de anticipos/préstamos con cuota fija; `advances`/`loans` eran solo un campo Float manual por período, sin catálogo reutilizable ni control de saldo.

## Investigación de referencia (solo lectura, sin copiar código)

`nuevo_nomina` separa dos conceptos distintos, ninguno igual a "un catálogo de beneficios con banderas independientes por impuesto":

- **`NoveltyTypeConfig`** (`novelty_type_configs`): catálogo de tipos de "novedad" (bonos, descuentos) por tenant, con banderas `affectsIess`/`affectsIncomeTax`/`affectsDecimos`/`affectsVacation` independientes — pero esas banderas son más finas de lo que `erpec_payroll/engine.py` puede honrar de verdad: el motor solo distingue DOS baldes (`bonus`/`commission`→grava IESS+renta+décimos+vacaciones+reserva todos juntos; `non_taxable_income`→no grava nada). Copiar sus 4 banderas independientes habría sido presentar una configuración que el cálculo no puede aplicar de verdad.
- **`EmployeeBenefit`** (`beneficios_empleados`): el verdadero libro de anticipos/préstamos — `montoTotal`, `saldoPendiente`, `cuotaMensual` (cuota fija), `anioInicio`/`mesInicio`, estado con flujo de aprobación (`pendiente`→`aprobado`→`descontado`/`anulado`). Sin tope legal por ley encontrado en su código (ninguna referencia al Código del Trabajo); el único tope es estructural: `cuotaMensual <= montoTotal`.

## Diseño adaptado (no copiado)

**Beneficios propios** (`erpec.payroll.benefit.type` + `erpec.payroll.benefit.line`): catálogo por empresa con una sola bandera real y honesta (`taxable`), que decide si el monto entra al balde `bonus` o al balde `non_taxable_income` del motor existente — sin inventar granularidad que el cálculo no puede cumplir. Se asigna por línea de período, editable solo en borrador.

**Anticipos y préstamos** (`erpec.payroll.advance` + `erpec.payroll.advance.deduction`): libro con `amount_total`/`installment_amount`/`balance` (saldo = total − suma de cuotas aplicadas, siempre derivado, nunca escrito a mano), flujo `draft`→`approved`→`cancelled`, fecha de inicio de descuento. Las cuotas se generan SOLO al calcular el período (`action_calculate()`), recalculando desde cero cada vez para no duplicar ni perder consistencia ante un recálculo. `min(saldo, cuota)` se suma al balde `advances`/`loans` del motor existente, encima de lo que se escriba a mano en esos mismos campos (no reemplaza la captura manual de un anticipo puntual no ligado al libro).

**Corrección real encontrada durante el diseño**: el reporte de rol de pago (A2, `reports.xml`) leía `line.advances`/`line.loans` directamente — con el libro activo, esos campos solo reflejan la parte manual, no el total real ya incluido en `deductions`/`net`. Se agregaron `result_advances`/`result_loans` (mismo patrón `_RESULT_FIELD_MAP` ya usado para todo lo demás) y se corrigió el reporte para usarlos, evitando subestimar el descuento real mostrado al empleado.

## Verificación

15 pruebas nuevas (74 en total en `erpec_payroll`, 0 fallos/errores). Dos bugs reales encontrados y corregidos en las propias pruebas durante su escritura (no en el código de producción): una comparación "manual vs. libro" reutilizaba el mismo empleado para ambos períodos, así que el anticipo aplicaba legítimamente a los dos (comportamiento correcto, verificado aparte) e invalidaba la comparación; y una colisión con la restricción única de período (empresa/año/mes/versión) al crear un segundo período de comparación en el mismo mes. Reinstalado en demo con respaldo previo. Ensayo real contra la demo: un bono que grava IESS y una cuota de anticipo aplicada automáticamente en dos períodos consecutivos, saldo del anticipo bajando de 300 a 180 a 60 sin intervención manual.

## Pendiente explícito

- No se copian las plantillas de novedades por período (asignar un beneficio recurrente sigue siendo una línea por período, no una plantilla auto-aplicada) — simplificación deliberada de este incremento.
- No existe tope legal de anticipos configurable (nuevo_nomina tampoco lo tiene; no se inventa uno).
- `action_correct()` (corrección de un período reversado) no revierte las cuotas de anticipo ya aplicadas en el período original — es el comportamiento correcto para la mayoría de correcciones (no se debe deshacer un pago de cuota ya hecho), pero un caso donde la corrección SÍ deba anular esa cuota específica requeriría ajuste manual del libro; documentado, no resuelto.

## Verificación y cierre

Commits con `phase: ERPEC26-OP12` y `task: ERPEC26-OP12.<fase>`. Detalle en `docs/evidencias/ERPEC26-OP12-BENEFICIOS-ANTICIPOS-20260918.json`.
