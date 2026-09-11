# ERPEC26-05 — Facturación desde Odoo

## Entrada y alcance
Leer RULES.md, .github/CODEX_CONTEXT.md, docs/PLAN_HAIKY_ERPEC26.md, matriz y arquitectura. Dependencia: 04. Validar el lock y los hashes antes de modificar. Ejecutar solamente con autorización vigente para esta fase; la creación de este prompt no acredita ejecución.

## Tareas
Aplicar la autorización del titular del 11-09-2026: trasladar lógica propia de facturación al ERP para operación local, conservando Facturador como alternativa API. Implementar generación/validación XML, autoridad y secuencias únicas, firma protegida, envío/consulta SRI y conciliación durable. Reutilizar la contabilidad Community y contrastar funciones con el producto fuente sin modificarlo. La autorización fiscal corresponde al SRI. Mantener el conector existente y no migrar emisores sin corte controlado.

## Criterios de aceptación
Venta sintética en pruebas, entrega duplicada, timeout, reinicio, eventos fuera de orden, rechazo y autorización; XML/RIDE vinculados. Ensayo real SRI requiere ambiente y credenciales autorizados.

## Verificación y cierre
Añadir pruebas significativas y evidencia en docs/evidencias/ERPEC26-05.md, distinguiendo simulación de servicio real. Revisar API, permisos, datos y UI afectada. Ejecutar verificaciones pertinentes de cada repositorio modificado. Definir reversión de código, datos y trabajos pendientes antes de cualquier migración. Preservar bytes del lock anterior, actualizar filesModified, validationChecks, fileHashes, firma y contexto solo al completar. Si falta una credencial, licencia o validación externa, documentar bloqueo y siguiente acción; no marcar aprobado. Commits con phase: ERPEC26-05 y task: ERPEC26-05.N; no publicar secretos ni trabajo ajeno.

## Continuidad local autorizada

El primer incremento prepara XML sin firma dentro del ERP y se instala en la demo; alcance y pendientes en docs/FACTURACION_LOCAL.md y evidencia ERPEC26-FISCAL-NATIVO.json. No cerrar la fase por este incremento. La demo usa configuración real cuando existe; RUC y certificado ausentes se muestran pendientes y no se inventan. Render aplazado no bloquea la preparación local independiente autorizada.
