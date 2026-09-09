# Contexto ERPEC26

- Repositorio: C:/proyectos web/ERP/_EC.
- Solicitud: crear repositorio, plan integral, RULES consolidado, contexto, lock y prompts por fases.
- Decisión: Odoo Community; revisar localización Ecuador Enterprise como referencia de alcance, sin asumir permiso de reutilización propietaria.
- Productos: SKNOMINA y SINKRONET FACTURADOR; fuentes y hashes en docs/evidencias/fuentes.json.
- Fase completada: ERPEC26-00, solo gobierno y análisis estático.
- Próxima fase: ERPEC26-01, pendiente de ejecución autorizada.
- Plan: docs/PLAN_HAIKY_ERPEC26.md; prompts ERPEC26-00 a ERPEC26-08.
- Verificación: node scripts/verify-governance.cjs.
- Alcance actual: no se han copiado módulos Odoo, probado SRI, cambiado datos, ejecutado pagos ni modificado productos fuente.
- Mantener modelo API inicial y autoridad única por operación; traslado de lógica propia requiere análisis explícito.
- GitHub privado: https://github.com/SINKRONET-SAS/erp-ec.
- Publicación y rama propia autorizadas por el usuario. Base: main; rama de trabajo: codex/erpec26-implementacion.
