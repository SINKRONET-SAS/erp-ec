# Matriz de capacidades y dependencias

Corte documental: 02-10-2026. Sustituye las decisiones iniciales como descripción del estado actual; la historia permanece en Git. Base Community fijada en [upstream.json](../upstream.json), auditada en [community-audit.json](evidencias/community-audit.json). El inventario de [referencia Enterprise](evidencias/localizacion-ecuador.json) no es el origen de distribución.

| ID | Capacidad | Implementación y evidencia | Límite vigente |
|---|---|---|---|
| EC01 | Localización contable Ecuador | Community l10n_ec; [fase 01](evidencias/ERPEC26-01.md) y [fundador](FUNDADOR_LOCALIZACION_ECUADOR.md) | Configuración por empresa y revisión fiscal; no homologación global |
| EC02 | Inventario Ecuador | l10n_ec_stock Community en auditoría del pin | Aceptación de cada operación/empresa |
| EC03 | Comercio electrónico Ecuador | l10n_ec_website_sale presente en auditoría | Disponibilidad del módulo no acredita un comercio publicado |
| EC04 | XML, firma, RIDE, notas y retenciones | Motores propios erpec_fiscal_native, erpec_fiscal_sri y erpec_fiscal_withholding_sri; [OP13/14](PLAN_HAIKY_COMPROBANTES_FIRMADOS.md) | Evidencia SRI histórica en pruebas; primer envío productivo supervisado pendiente |
| EC05 | Guía de remisión | erpec_fiscal_guide_sri enlazado a inventario; OP13-E | No depende de una API externa de guías; aceptación productiva separada |
| EC06 | POS electrónico | No se acredita integración fiscal POS en este contraste | Diseñar/validar su contrato antes de ofrecerlo |
| EC07 | Reportes contables | erpec_withholding_accounting/accounting.py y vistas propias | Cobertura propia, no equivalencia total con reportes Enterprise |
| EC08 | ATS | erpec_fiscal_ats, validación XSD antes de descarga; [fundador](FUNDADOR_LOCALIZACION_ECUADOR.md) | Datos fiscales y aceptación del anexo pendientes; XSD no equivale a declaración aceptada |
| EC09 | Nómina y contabilidad | erpec_payroll: cálculo, cierre/asiento, reversión, RDEP y beneficios; salida, rol proporcional y acta de finiquito ([NM27](NOMINA_SALIDA_FINIQUITO_NM27.md)); [matriz](DI25-03_MATRIZ_ACEPTACION.md) | No equivalencia integral certificada con SKNOMINA ni aceptación legal global |
| EC10 | API Facturador | erpec_fiscal_connector con CUSTOM, contrato 1.0 e idempotencia | No asumir otros documentos admitidos; autoridad única por comprobante |
| EC11 | Facturación de suscripciones SKNOMINA | Contrato fuente separado de documentos de clientes; fase 01 | No se modifica ni se acredita ejecución actual de ese producto |
| EC12 | Planes, derechos, usuarios y provisión | erpec_entitlements, erpec_selfservice y worker; [CM28](PLAN_HAIKY_COMERCIAL_MODULOS_ACTIVOS_CM28.md) | Tarifas/operación productiva y correspondencias externas requieren validación |

Los módulos Enterprise OPL-1/OEEL-1 del diagnóstico solo son referencias de capacidad, no dependencias autorizadas del producto propio. No atribuir a una auditoría de manifiestos la validación de bibliotecas, normas o servicios externos.

[Contraste DC02](DIAGNOSTICO_CONTRASTADO_DC02.md): separa falsos positivos, brechas de documentación y pendientes conservados. Las pruebas nuevas se registran al cierre de DC02; las referencias anteriores son evidencia histórica.
