# ERPEC26-OP04 — Nómina Ecuador

Leer AGENTS.md, RULES.md, el contexto histórico y docs/PLAN_AMPLIACION_OPERATIVA.md. Este complemento tiene autorización expresa del titular; no acredita implementación. Conservar evidencia y locks anteriores.

## Trabajo

Completar el alcance local autorizado de ERPEC26-06 con cálculo nativo, mapeos versionados y asiento Odoo. Usar parámetros reales del ejercicio y personas ficticias. SKNOMINA sí tiene API y se conserva como alternativa de integración. Ensayar cierre, repetición, aislamiento, pagos y reversión; para la alternativa externa, validar además contrato de cierre, timeout y tenant ajeno. Mantener una sola autoridad por organización y mostrar errores y acciones de corrección.

Todos los requisitos, casos negativos y criterios del apartado OP04 del plan complementario son obligatorios. Empezar por inspeccionar el estado actual y licencias; aprovechar el código Community ya disponible. No modificar productos fuente como efecto secundario. Los cambios de integración requieren sus reglas y commits separados.

## Entrega verificable

Preparar respaldo y trabajar primero en copia aislada. Implementar configuración, modelos, permisos y navegación necesarios; probar el ciclo completo con datos sintéticos, sin emisiones ni pagos reales. Instalar en la demo solamente después de aprobar los controles. Mantener su RUC vacío y separar credenciales del emisor Founder.

Registrar evidencia real, resultado de pruebas, límites y guía de demostración. Las carencias de credenciales o validación externa deben indicar acción concreta; no retirar requisitos ni declararlos aprobados. Verificar UTF-8, gobierno y diferencias de Git. Commit: phase: ERPEC26-06 task: ERPEC26-OP04. No cerrar fases por añadir un documento o instalar un módulo.

## Modificación de alcance autorizada por el usuario

El 11-09-2026 el titular pidió implementar directamente en el ERP la lógica basada en SKNOMINA para reducir recursos, y confirmó que SKNOMINA sí tiene API. Para la demo se autoriza cálculo nativo con una sola autoridad; se conserva la API como alternativa de integración y como referencia de contraste. No se exige desplegar otro servicio para el cálculo local. La demo debe usar parámetros reales del ejercicio, verificados en fuentes oficiales; empleados y movimientos pueden ser ficticios.

El traslado requiere equivalencia documentada, versiones, migración y retirada controlada de la autoridad anterior antes de empresas reales. Se mantienen los requisitos contables, pagos, idempotencia, permisos, aislamiento y reversión. No se declara equivalencia integral por contrastar unas funciones auxiliares.
