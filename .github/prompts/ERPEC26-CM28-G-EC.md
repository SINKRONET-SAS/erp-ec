# CM28-G-EC — Localización Ecuador del fundador

Autorización: solicitud expresa del titular de que el fundador tenga las funcionalidades de localización Ecuador. Seguimiento de CM28-G y de su corrección CI; conservar autorización de commit/push local, sin producción ni envíos fiscales, correos o cobros.

Dependencia: gobierno válido de CM28-G-CI. Leer RULES.md, CODEX_CONTEXT.md y PLAN_HAIKY_ERPEC26.md. Diagnóstico confirmado por RPC: l10n_ec, inventario Ecuador, fiscal nativo, retenciones, guías y nómina instalados; agregador ATS sin instalar. País y plan contable Ecuador, USD e idioma es_EC ya configurados.

Tareas: respaldar y ensayar restauración; probar instalación ATS en copia aislada; instalar el faltante en fundador; verificar módulos, permisos, menús y vistas con su usuario real, conservando los movimientos contables. No cambiar tasas, certificado, credenciales o ambiente SRI.

Aceptación: ATS instalado y accesible junto al resto de funciones Ecuador; acceso fundador conservado, registros contables sin cambios, esquema sin desfase. Distinguir disponibilidad de funcionalidad de homologación o configuración fiscal para producción.

Hallazgo adicional en ensayo: el agregador ofrecía XML sin comprobar el XSD incorporado y las pruebas agregaban datos históricos ajenos a su caso. Corregir la validación previa a descarga, limpiar descargas antiguas al reconstruir y aislar la compañía de ensayo. No modificar signos, tasas o razón social para forzar la aceptación del esquema.

Pruebas: instalación y pruebas ATS aisladas, restauración real y recorrido de pantallas fundador. Evidencia en docs/evidencias/CM28/fundador-ecuador*.json. UTF-8 sin BOM, mojibake y gobierno antes del cierre.

Reversión: respaldo completo generado por update-instance.py; validar restore-cm28-instance.py --report con el reporte de actualización y usar --apply solo si es necesario. Preservar clave fuera de Git e historia del contexto y bytes del lock.

Cierre: documentar resultados reales, sellar CM28-G-EC, commit phase/task, push y revisar todas las ejecuciones CI del SHA publicado.
