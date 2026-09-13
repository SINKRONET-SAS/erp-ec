# ERPEC26-OP06 — Cumplimiento legal Ecuador (Tributario, Facturación Electrónica, ATS, RDEP, Laboral, Protección de Datos, Envíos por email)

Leer AGENTS.md, RULES.md, el contexto histórico, docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md, docs/ALCANCE_ATS_RDEP.md y docs/FACTURACION_LOCAL.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Consolidar bajo un mismo gobierno el estado real de seis dominios legales que afectan al ERP en Ecuador: Tributario general, Facturación Electrónica, ATS, RDEP, Laboral, Protección de Datos Personales (LOPDP) y envíos por email. Para los dominios que ya tienen documentación propia (Facturación Electrónica en docs/FACTURACION_LOCAL.md; ATS y RDEP en docs/ALCANCE_ATS_RDEP.md; Laboral en docs/OPERACIONES_LOCALES_DEMO.md y CODEX_CONTEXT.md), remitir a esa documentación en vez de duplicarla. Para los dominios nuevos (Protección de Datos, envíos por email), investigar contra fuente oficial antes de programar cualquier artefacto, citando la norma, el regulador y la fecha de la fuente consultada.

No inventar artículos, plazos, catálogos, multas ni umbrales legales. Lo no confirmado contra fuente primaria queda marcado explícitamente como tal, no como hecho. Ningún incremento de esta fase declara cumplimiento legal alcanzado, homologación, ni sustituye asesoría legal o contable profesional. No se activa envío real de correos, transmisión real al SRI, ni recolección real de datos personales de terceros fuera de los perfiles sintéticos ya usados en la demo.

## Criterios de aceptación

Cada incremento de esta fase debe: (1) citar su fuente (oficial cuando exista; secundaria marcada como tal cuando no) con fecha de consulta; (2) implementar solo lo que puede construirse sin inventar datos legales faltantes; (3) dejar explícitamente documentado qué sigue pendiente y por qué; (4) probarse en copia aislada antes de cualquier instalación. Un incremento que no pueda cumplir (1)-(3) para un dominio se limita a investigación y documentación de ese dominio, sin código.

## Verificación y cierre

Añadir pruebas significativas y evidencia en docs/evidencias/. Ejecutar verificaciones pertinentes de cada módulo nuevo o modificado; instalar en la demo solo cuando el estado de la demo lo permita con seguridad (registrar si se aplaza por actividad concurrente de otra sesión sobre el mismo repositorio, sin forzar la instalación). Commits con phase: ERPEC26-OP06 y task: ERPEC26-OP06.N. No cerrar la fase por añadir un documento o instalar un módulo; los siete dominios permanecen abiertos hasta que cada uno tenga su propio cierre verificable.

## Primer incremento autorizado — 13-09-2026

El titular pidió generar el plan, desplegarlo con su gobierno (CODEX_CONTEXT, AuditLock, este prompt) y ejecutar el resultado. Se entrega docs/PLAN_HAIKY_CUMPLIMIENTO_LEGAL_EC.md con el estado de los siete dominios (remitiendo a la documentación ya existente para Tributario/Facturación/ATS/RDEP/Laboral, e investigación de fuente oficial nueva para Protección de Datos y envíos por email). Como primer incremento de código, dominio LEGAL-06: módulo `erpec_data_protection` con un Registro de Actividades de Tratamiento (RAT) y un campo de exclusión de correo comercial en `res.partner` (apoyo a la Ley 67 de Comercio Electrónico), probado en copia aislada limpia. Los demás dominios quedan en el estado documentado en el plan, sin código nuevo en este incremento.
