# ERPEC26-TX01 — Plan de impuestos
Leer RULES.md, CODEX_CONTEXT.md y docs/PLAN_HAIKY_IMPUESTOS.md. Autorizado por la solicitud del titular sobre catálogo, cuentas, artículos, proveedores y módulos.

Ejecutar TX00 documental antes de TX01. Construir escenarios de consulta con relaciones nativas, sin calcular un tributo nuevo ni modificar tasas existentes. Añadir navegación y consulta de cuentas de repartición, facturas/devoluciones y posición fiscal del tercero. Restringir por empresa/perfil. Verificar transformaciones, impuestos agrupados, ausencia de configuración, acceso negativo y cambios de empresa.

Después de aprobar pruebas, ejecutar TX02: respaldo e instalación, aceptación visual y evidencia de alcance real. Actualizar contexto/lock conservando los estados históricos, verificar gobierno, commit y push. Continuar simultáneamente el cierre del ensayo SP02 de importaciones y valoración; no declarar cerrado SP02 global.
