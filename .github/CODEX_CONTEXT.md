# Contexto ERPEC26

- Repositorio: C:/proyectos web/ERP/_EC.
- Solicitud: crear repositorio, plan integral, RULES consolidado, contexto, lock y prompts por fases.
- Decisión: Odoo Community; revisar localización Ecuador Enterprise como referencia de alcance, sin asumir permiso de reutilización propietaria.
- Productos: SKNOMINA y SINKRONET FACTURADOR; fuentes y hashes en docs/evidencias/fuentes.json.
- Fase completada: ERPEC26-03, catálogo versionado, contratos y vínculos autorizados.
- Próxima fase: ERPEC26-04, aprovisionamiento durable. Autoridad de cobro obligatoria por contrato; no hay cargo automático. Ejecución de todas las fases, commit y push autorizados por el usuario.
- Plan: docs/PLAN_HAIKY_ERPEC26.md; prompts ERPEC26-00 a ERPEC26-08.
- Verificación: node scripts/verify-governance.cjs.
- Alcance actual: dos pilotos Windows accesibles, interfaz en español, aislamiento y restauración verificados. Sin publicación en nube, pruebas SRI, pagos ni cambios a productos fuente.
- Plataforma: Windows nativo, Python 3.12 aislado y PostgreSQL 17.
- Mantener modelo API inicial y autoridad única por operación; traslado de lógica propia requiere análisis explícito.
- GitHub privado: https://github.com/SINKRONET-SAS/erp-ec.
- Publicación y rama propia autorizadas por el usuario. Base: main; rama de trabajo: codex/erpec26-implementacion.
