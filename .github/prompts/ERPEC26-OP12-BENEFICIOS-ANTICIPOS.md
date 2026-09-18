# ERPEC26-OP12 — Beneficios propios configurables por empresa y libro de anticipos/préstamos

Leer AGENTS.md, RULES.md, el contexto histórico y docs/PLAN_HAIKY_BENEFICIOS_ANTICIPOS.md. El titular pidió explícitamente que la parametrización de nómina deje de ser solo legal/nacional y permita que cada cliente configure sus propios beneficios, usando `nuevo_nomina` como referencia (solo lectura, sin copiar código ni conectar el ERP a ese proyecto como sistema vivo), y el mismo tratamiento para anticipos/préstamos.

## Trabajo

`erpec.payroll.benefit.type`/`erpec.payroll.benefit.line`: catálogo de beneficios por empresa (no un parámetro legal), con una sola bandera honesta (`taxable`) que el motor de cálculo puede honrar de verdad — no se ofrecen banderas independientes (IESS/renta/décimos/vacaciones por separado) que `engine.py` no pueda aplicar. `erpec.payroll.advance`/`erpec.payroll.advance.deduction`: libro de anticipos/préstamos con cuota fija, saldo siempre derivado (nunca escrito a mano), cuotas generadas solo al calcular el período.

No inventar reglas legales sobre anticipos (topes, plazos) que ninguna fuente (ni nuevo_nomina, ni la ley) confirme. No declarar un beneficio "grava X" si el motor de cálculo no puede aplicarlo de verdad para ese X específico.

## Criterios de aceptación

Probar en base aislada y nueva antes de instalar en demo; instalar solo con respaldo previo; ensayo real (no simulado) contra la demo; documentar exactamente qué queda pendiente (ver plan).

## Verificación y cierre

Pruebas significativas y evidencia en docs/evidencias/. Commits con `phase: ERPEC26-OP12` y `task: ERPEC26-OP12.<fase>`.
