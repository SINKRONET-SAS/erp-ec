# Contexto ERPEC26

- Repositorio: C:/proyectos web/ERP/_EC.
- Solicitud: crear repositorio, plan integral, RULES consolidado, contexto, lock y prompts por fases.
- Decisión: Odoo Community; revisar localización Ecuador Enterprise como referencia de alcance, sin asumir permiso de reutilización propietaria.
- Productos: SKNOMINA y SINKRONET FACTURADOR; fuentes y hashes en docs/evidencias/fuentes.json.
- Fase completada: ERPEC26-03, catálogo versionado, contratos y vínculos autorizados.
- Fase en curso: ERPEC26-04. Cola y aprovisionamiento Windows local verificados. Producción definida: Render (Linux/contenedores, PostgreSQL y servicios), Cloudflare para DNS/proxy del dominio futuro y PAYPHONE para pagos. Pendientes: adaptación del trabajador a Render, acceso al proyecto y aplicación PAYPHONE de prueba. HTTPS inicial con URL de Render; dominio propio posterior. Fases 05–08 pendientes por dependencia. Autoridad de cobro obligatoria por contrato; no hay cargo automático. Ejecución de todas las fases, commit y push autorizados por el usuario.
- Plan: docs/PLAN_HAIKY_ERPEC26.md; prompts ERPEC26-00 a ERPEC26-08.
- Verificación: node scripts/verify-governance.cjs.
- Alcance actual: catálogo/contratos y controlador local visibles; tercera instancia sintética aprovisionada, suspendida y reactivada conservando datos. Sin publicación en nube, pagos externos, pruebas SRI ni cambios a productos fuente.
- Desarrollo local: Windows nativo, Python 3.12 aislado y PostgreSQL 17. Producción: Render; no requiere Windows. Decisión y segunda pasada: docs/PRODUCCION_RENDER_CLOUDFLARE.md.
- Mantener modelo API inicial y autoridad única por operación; traslado de lógica propia requiere análisis explícito.
- GitHub privado: https://github.com/SINKRONET-SAS/erp-ec.
- Publicación y rama propia autorizadas por el usuario. Base: main; rama de trabajo: codex/erpec26-implementacion.
