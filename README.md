# ERP EC — suite empresarial Community

ERP sobre Odoo Community 18 con módulos propios de fiscalidad Ecuador, nómina, operaciones, contratación y aprovisionamiento. Existe implementación y evidencia de ejecución local; producción y aceptación externa siguen pendientes. El estado del plan maestro es 00–03 completadas y 04 parcial; los complementos locales no cierran automáticamente 05–08.

- [Plan maestro](docs/PLAN_HAIKY_ERPEC26.md).
- [Capacidades y límites vigentes](docs/MATRIZ_CAPACIDADES.md).
- [Arquitectura y autoridades](docs/ARQUITECTURA_Y_CONTRATOS.md).
- [Contexto de continuidad](.github/CODEX_CONTEXT.md).
- [Reglas](RULES.md).
- [Contraste del diagnóstico recibido](docs/DIAGNOSTICO_CONTRASTADO_DC02.md) y [Plan Haiky DC02](docs/PLAN_HAIKY_CONTRASTE_DIAGNOSTICO_DC02.md).
- [Localización del fundador y accesos](docs/FUNDADOR_LOCALIZACION_ECUADOR.md).
- [Evidencia histórica CM28](docs/evidencias/CM28/CM28-G-cierre.json).

La revisión Community aprobada consta en [upstream.json](upstream.json); su inventario está en [community-audit.json](docs/evidencias/community-audit.json). No se incorporan fuentes Enterprise. La licencia propia requiere decisión del titular; los manifiestos no autorizan redistribución de terceros.

Validación: node scripts/verify-governance.cjs y node scripts/verify-project-state.cjs. La integridad y coherencia documental no sustituyen pruebas funcionales ni acreditan homologación.

Repositorio privado: https://github.com/SINKRONET-SAS/erp-ec. Rama de trabajo: codex/erpec26-implementacion; base main.
