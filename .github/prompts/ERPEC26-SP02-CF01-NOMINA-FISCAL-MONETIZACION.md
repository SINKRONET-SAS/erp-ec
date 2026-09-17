# ERPEC26-SP02-CF01 — pasada funcional transversal

Leer AGENTS.md, RULES.md, `.github/CODEX_CONTEXT.md`, `docs/PLAN_HAIKY_ERPEC26.md` y `docs/PLAN_HAIKY_REVISION_NOMINA_FISCAL_MONETIZACION.md`. La solicitud del titular del 14-09-2026 autoriza ejecutar esta pasada y corregir defectos reproducibles dentro del repositorio ERP EC.

Ejecutar CF01-A a CF01-E en orden. Trabajar con copias aisladas, datos ficticios y parámetros contrastados; no llamar proveedores ni SRI. Separar pruebas locales, ambiente de pruebas externo y producción. No modificar SKNOMINA ni Facturador.

Reparar verificadores que mezclen datos de negocio con sus fixtures, añadir casos de frontera necesarios y repetir los ensayos de nómina, facturación y monetización. Documentar resultados, cálculos, reportes, ambientes y brechas con evidencia verificable. Actualizar contexto y AuditLock sin cerrar SP02 ni fases 04–08 salvo que todas sus puertas estén realmente satisfechas.

Commit requerido: `phase: ERPEC26-SP02 task: CF01 revision nomina fiscal monetizacion`.
