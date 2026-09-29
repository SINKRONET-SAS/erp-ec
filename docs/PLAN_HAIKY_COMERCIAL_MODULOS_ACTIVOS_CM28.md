# Plan Haiky CM28 — Landing, planes, monetización y activos fijos

Autorizado el 28-09-2026 por el titular: implementar el plan completo, revisar errores/duplicaciones/regresiones/mojibake, corregir, commit y push. Ampliación expresa: cantidad de usuarios como variable de monetización.

## Resultado y decisiones

Ampliar erpec.plan, erpec.subscription, PayPhone y la cola existente. Planes con capacidades incluidas y complementos opcionales; precios mensuales/anuales en USD configurables y sin publicar. Usuarios internos activos: incluidos en el plan más cantidad adicional a tarifa del periodo. Excluir portal, público y cuentas técnicas protegidas; contar al administrador humano. Cantidad e importe se validan en servidor. Cambios efectivos en próxima renovación, sin prorrateo ni débito automático.

Identidad estable del cliente independiente de compañía operadora; no asociar por correo/RUC. Una instancia por cliente. Instantáneas inmutables de periodo, módulos, usuarios, límites, impuestos e importe. Publicación independiente del contrato. Preservar contratos/datos históricos; baja de complemento conserva lectura y exportación autorizadas. Vencimiento total conserva suspensión. Derechos se verifican también por RPC, no solo por menús.

Landing en Odoo con marca ERP EC / SINKRONET, comparación desde el catálogo, acceso de clientes, contratación y seguimiento protegido. No duplicar tarifas en HTML ni sobrescribir contenido personalizado. Retirar SS-DEMO de publicación preservando sus contratos. No inventar tarifas comerciales, textos legales, tasas ni homologaciones.

Activos fijos: módulo propio erpec_assets; categorías/cuentas/diario, alta manual o compra contabilizada, capitalización parcial con bloqueo de duplicados, vida útil, residual, puesta en uso, depreciación lineal mensual, asientos idempotentes, bajas/venta, reversión y conciliación. Estimaciones solo futuras. Excluye custodios/transferencias, revaluación, deterioro y métodos acelerados. Depreciación contable no implica deducibilidad fiscal.

## Fases y gates

Secuencia 00 → A → B → C → D → E → F → G. Solo iniciar la siguiente con cierre firmado válido de la anterior.

|Fase|Entrega|Criterio|
|---|---|---|
|CM28-00|Diagnóstico y gobierno|Reproducir colisión entre dos clientes y solicitud no sincronizada en base aislada; registrar código, configuración y límites.|
|CM28-A|Identidad de clientes|Separar cliente de operador; contratos e instancias por cliente; migración reversible y dos clientes concurrentes.|
|CM28-B|Catálogo y tarifas|Capacidades autorizadas, planes versionados, complementos, mensual/anual y usuarios incluidos/adicionales; instantánea y precio calculado en servidor.|
|CM28-C|Activos fijos|Alta manual y compras, capitalización parcial, depreciación lineal mensual, baja/venta, reversión y reportes conciliables; permisos por compañía.|
|CM28-D|Monetización y aprovisionamiento|Renovación sin débito automático, cola idempotente, módulos y usuarios contratados, derechos en servidor, estados derivados y activación de acceso de un uso.|
|CM28-E|Landing y portal|Sitio Odoo conectado al catálogo, comparación, contratación, seguimiento y renovación; ofertas sin publicar por defecto; revisión móvil y escritorio.|
|CM28-F|Validación y actualización|Pruebas de regresión, aislamiento, cuotas, contabilidad, UTF-8/mojibake, versiones, respaldo/restauración y actualización local.|
|CM28-G|Cierre y publicación|Evidencias verificables, gobierno, commit phase/task, push de rama y comprobación de CI.|

## Validación y reversión

Reproducir primero en base aislada; pruebas focalizadas por fase y suite integrada ante cambios funcionales. Incluir dos clientes, concurrencia, acceso cruzado, cuotas, complementos retirados, pagos duplicados/tardíos/cancelados, importes manipulados, renovación, meses incompletos, redondeos, cierres contables, navegación y móvil. Distinguir simulación PayPhone de pago real. Registrar comandos, salida, fallos, omisiones y alcance. Respaldo/restauración antes de migraciones; no retirar derechos históricos silenciosamente.

Archivar bytes anteriores del AuditLock y sellar con scripts/seal-auditlock.cjs; validar con node scripts/verify-governance.cjs. Actualizar contexto conservando historia. Evidencias en docs/evidencias/CM28. UTF-8 sin BOM, LF y round-trip en escrituras. Cada commit incluye phase y task. No modificar repositorios fuente, hacer cobros/envíos reales ni desplegar producción.

## Interfaces

Conservar rutas de autoservicio y PayPhone. Extender contratos con cliente y detalle comercial; ampliar mensajes del trabajador con cliente, revisión, capacidades y cuotas. Versionar cambios y preservar clientes previos mediante migración explícita. Reutilizar account.move para activos, sin motor contable paralelo. Información de alta y derechos siempre derivada del contrato/pago/instancia autoritativos.

## Resultado ejecutado — 28-09-2026

Fases CM28-00 a CM28-G completadas en orden y selladas. La respuesta a cada hallazgo está al final del diagnóstico; los cierres y evidencias se conservan en docs/evidencias/CM28. Fundador y demo actualizados tras restauración ensayada. Implementación publicada en 5b61ec16475847223e19ff9229726622ee86e656; cinco trabajos de CI aprobados, con 702 pruebas integradas en Linux sin fallos/errores. Las tarifas reales permanecen sin publicar y no se realizaron pagos, envíos fiscales, correos reales ni despliegue de producción.

## Seguimiento autorizado CM28-G-EC — fundador con localización Ecuador

Se incorpora ATS en el fundador y se verifican las nueve pantallas de Ecuador y activos, conservando los datos contables y acceso. Prompt: `.github/prompts/ERPEC26-CM28-G-EC.md`; resultados y límites en `docs/FUNDADOR_LOCALIZACION_ECUADOR.md` y `docs/evidencias/CM28/fundador-ecuador*.json`. El control XSD impide descargas ATS inválidas; no resuelve por sí solo los pendientes tributarios de los datos existentes.
