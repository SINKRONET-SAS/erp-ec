# ERPEC26-OP04 — Nómina Ecuador

Leer AGENTS.md, RULES.md, el contexto histórico y docs/PLAN_AMPLIACION_OPERATIVA.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Completar ERPEC26-06: inspeccionar y probar contrato de cierre SKNOMINA, mapeos versionados y asiento Odoo. Ensayar cierre, repetición, timeout, tenant ajeno, pagos y reversión. SKNOMINA conserva cálculo; Odoo conserva asiento. Mostrar errores y acciones de corrección.

Todos los requisitos, casos negativos y criterios del apartado OP04 del plan complementario son obligatorios. Empezar por inspeccionar el estado actual y licencias; aprovechar el código Community ya disponible. No modificar productos fuente como efecto secundario. Los cambios de integración requieren sus reglas y commits separados.

## Entrega verificable

Preparar respaldo y trabajar primero en copia aislada. Implementar configuración, modelos, permisos y navegación necesarios; probar el ciclo completo con datos sintéticos, sin emisiones ni pagos reales. Instalar en la demo solamente después de aprobar los controles. Mantener su RUC vacío y separar credenciales del emisor Founder.

Registrar evidencia real, resultado de pruebas, límites y guía de demostración. Las carencias de credenciales o validación externa deben indicar acción concreta; no retirar requisitos ni declararlos aprobados. Verificar UTF-8, gobierno y diferencias de Git. Commit: phase: ERPEC26-06 task: ERPEC26-OP04. No cerrar fases por añadir un documento o instalar un módulo.
