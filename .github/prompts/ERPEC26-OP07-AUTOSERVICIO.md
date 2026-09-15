# ERPEC26-OP07 — Autoservicio de altas (landing → plan → pago → aprovisionamiento)

Leer AGENTS.md, RULES.md, el contexto histórico, docs/CONTRATOS_SUITE.md, docs/PAYPHONE_LOCAL.md y docs/ALCANCE_AUTOSERVICIO.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Convertir el alta de nuevos clientes en autoservicio: una landing pública donde el visitante elige un plan publicado, paga por PayPhone, y el sistema activa el contrato y encola el aprovisionamiento sin intervención de un administrador entre el pago y la instancia lista. Reutilizar la maquinaria ya probada (`erpec_suite`, `erpec_payphone`, `erpec_provision`, `scripts/provision-worker.py`) sin duplicarla; el visitante público nunca obtiene sesión ni permisos Odoo — toda escritura privilegiada ocurre en el controlador bajo el usuario administrador (sudo), igual que ya hacía `/payment/payphone/return`.

No inventar precios, periodicidades ni condiciones comerciales sin marcarlas explícitamente como supuesto propio del incremento (por ejemplo, la duración de un mes calendario de la suscripción de autoservicio). No se activan credenciales reales de producción de PayPhone sin que el titular las entregue; mientras tanto, cualquier rehearsal usa credenciales placeholder y documenta que PayPhone las rechaza, sin mover dinero.

## Criterios de aceptación

Cada incremento de esta fase debe: (1) no tocar la mecánica de seguridad ya probada (`_confirm`, `_reconcile`, `_contract_digest`, `_lock`, `claim_next`/`finish`) salvo excepción explícita, justificada y acotada; (2) mantener el modelo de acceso — ningún grupo público obtiene permisos ORM directos; (3) probarse en base aislada nueva antes de cualquier instalación; (4) dejar documentado qué sigue pendiente (credenciales reales, servicio automático del worker, anti-abuso) y por qué. Un incremento que no pueda cumplir (1)-(3) se limita a documentación, sin código.

## Verificación y cierre

Añadir pruebas significativas y evidencia en docs/evidencias/. Instalar en `erpec_fundador` (instancia operadora real) solo con respaldo previo. Commits con phase: ERPEC26-OP07 y task: ERPEC26-OP07.N. No cerrar la fase por un incremento: el registro automático del worker como servicio, la adaptación a Render y las credenciales de producción de PayPhone permanecen pendientes hasta autorización y entrega explícitas.

## Primer incremento autorizado — 14-09-2026

El titular pidió el flujo completo de punta a punta, corriendo en local. Se entrega: `erpec.plan.published`/`price` en `erpec_suite`; tope de `erpec_payphone` subido de USD 100 a USD 100 000 y rotulado de "ensayo" corregido (misma mecánica, sin cambios); ruta `/payment/payphone/checkout/<reference>` abierta a público (excepción acotada, sin datos privados); nuevo addon `erpec_selfservice` (landing pública, formulario de alta, orquestación hasta el pago preparado); `scripts/provision-worker.py` reapuntado a `erpec_fundador` como instancia operadora. 34/34 pruebas en base aislada; instalado en `erpec_fundador` con respaldo; rehearsal real por HTTP hasta el rechazo esperado de PayPhone por credenciales placeholder (sin mover dinero). Detalle completo en docs/ALCANCE_AUTOSERVICIO.md.
