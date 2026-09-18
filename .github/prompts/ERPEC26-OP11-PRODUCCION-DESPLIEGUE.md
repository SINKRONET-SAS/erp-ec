# ERPEC26-OP11 — Producción, despliegue y anexo ATS completo

Leer AGENTS.md, RULES.md, el contexto histórico y docs/PLAN_HAIKY_PRODUCCION_DESPLIEGUE.md. Este complemento responde al diagnóstico integral compartido por el titular el 17-09-2026; su sección "Tareas Inmediatas" (OP10.A2-A4/B3) ya estaba completada antes de este plan — verificado contra el repositorio real antes de planificar, no se repite ese trabajo. Este plan cubre exclusivamente la sección "Requisitos Previos al Despliegue en Producción" del diagnóstico.

## Trabajo

Cuatro frentes con distinto grado de bloqueo externo: (B1) generación completa del ATS — clasificación de sustento tributario por línea de compra (ejecutable) y agregador XML compras/ventas validado contra `ats.xsd` (incremento siguiente, no improvisar una sola pasada); (B2) infraestructura cloud Render/Cloudflare — parcialmente ejecutable (adaptar el trabajador de aprovisionamiento, completar la imagen Linux), bloqueado en el despliegue real por falta de acceso a una cuenta/espacio de Render; (B3) producción fiscal SRI — bloqueado, requiere certificado `.p12` de producción real del titular; (B4) homologación bancaria real — bloqueado, requiere credenciales/especificaciones de prueba de los bancos objetivo.

No inventar códigos de sustento, formatos bancarios ni activar ningún endpoint de producción sin la fuente/credencial real correspondiente. No declarar un despliegue Render, una homologación bancaria o una autorización SRI de producción sin decirlo explícitamente — los frentes bloqueados (B2 en su parte real, B3, B4) se documentan, no se fabrican.

## Criterios de aceptación

Cada incremento debe: (1) probarse en base aislada y nueva antes de instalar en demo; (2) instalar solo con respaldo previo; (3) documentar exactamente qué fase completa y cuáles quedan pendientes, incluido el motivo del bloqueo si aplica. Un incremento que no pueda cumplir (1)-(2) se limita a documentación, sin código.

## Verificación y cierre

Añadir pruebas significativas y evidencia en docs/evidencias/. Commits con `phase: ERPEC26-OP11` y `task: ERPEC26-OP11.<fase>` (p. ej. `ERPEC26-OP11.B1a`). No cerrar la fase por un incremento: B1a, B1b, B2, B3 y B4 permanecen pendientes hasta completarse o hasta que el titular provea el recurso que las desbloquea.
