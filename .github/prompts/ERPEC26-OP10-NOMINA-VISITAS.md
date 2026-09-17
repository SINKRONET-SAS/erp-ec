# ERPEC26-OP10 — Nómina segunda pasada y control de visitas de vendedores

Leer AGENTS.md, RULES.md, el contexto histórico y docs/PLAN_HAIKY_NOMINA_VISITAS.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Dos frentes planificados juntos, ejecutados por fases: (A) segunda pasada sobre `erpec_payroll` — parametrización versionada de beneficios legales, reportes de nómina, envío automático del rol de pago, carga de saldos iniciales; (B) una funcionalidad nueva — control de visitas/asistencia de vendedores por zona (geocerca, excepciones, reportes de cumplimiento), inspirada en patrones ya maduros de `C:\proyectos web\nuevo_nomina` y `C:\proyectos web\sinkroniq-mobile` (solo lectura, sin modificar esos proyectos ni conectar el ERP a ellos como sistemas vivos).

Orden acordado con el titular: A1 (parámetros legales) → B1-B2 (modelo y registro de visitas) → A2-A4 (reportes, envío, saldos) → B3 (reportes de visitas).

No inventar reglas laborales o de geolocalización sin base en el código de referencia o en fuente oficial ya citada en `parameters_ec2026.py`/`PLAN_HAIKY_NOMINA_VISITAS.md`. No declarar un envío de correo real, una carga de saldos aplicada a datos de negocio reales, o una marca de visita geolocalizada real sin decirlo explícitamente — todo se prueba primero con datos sintéticos en base aislada.

## Criterios de aceptación

Cada incremento debe: (1) probarse en base aislada y nueva antes de instalar en demo; (2) instalar solo con respaldo previo; (3) no activar envío real de correo sin credenciales SMTP provistas por el titular; (4) documentar exactamente qué fase de las siete completa y cuáles quedan pendientes. Un incremento que no pueda cumplir (1)-(2) se limita a documentación, sin código.

## Verificación y cierre

Añadir pruebas significativas y evidencia en docs/evidencias/. Commits con phase: ERPEC26-OP10 y task: ERPEC26-OP10.<fase> (p. ej. ERPEC26-OP10.A1). No cerrar la fase por un incremento: las siete fases (A1, B1, B2, A2, A3, A4, B3) permanecen pendientes hasta completarse todas y recibir cierre explícito del titular.
