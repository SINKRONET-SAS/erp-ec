# Plan Haiky DI25 — Corrección y mejora integral ERP EC

Fecha: 20-09-2026 (Ecuador). Plan complementario al maestro ERPEC26; no renumera ni cierra sus fases.
Fuente: [Diagnóstico integral DI25](DIAGNOSTICO_INTEGRAL_DI25.md).
Estado vigente (24-09-2026): **DI25-05, DI25-06 y DI25-07 cerradas: los seis criterios de DI25-07 quedan comprobados, incluida la aceptación de negocio del titular ("DI25-07.6 se acepta, sin embargo, queda abierta la opción de mejora o cierre de las decisiones tomadas"); ver docs/evidencias/DI25/DI25-07-cierre.json y docs/DI25-07_ACEPTACION.md. Ninguna exclusión de la tabla de DI25-07.6 pasa a cumplida por esto; cada una queda abierta para un incremento futuro por instrucción explícita.** Estado previo (23-09-2026): **DI25-00–02 completadas en sus alcances. DI25-03 cerrada (parcial): los cuatro criterios numerados quedan comprobados con pruebas (docs/evidencias/DI25/DI25-03-cierre.json); pendiente externo (SRI, responsable tributario), no brecha de implementación. DI25-04 cerrada (parcial): DI25-04.1 y DI25-04.2 comprobados (catálogo ATS corregido; agregador ATS real construido en erpec_fiscal_ats, conciliando compras/ventas/anulados/retenciones con vista de faltantes); DI25-04.3 parcialmente comprobado (motor real del DIMM conectado y probado, ahora con un comprobante real posteado en la demo, validado sin errores contra el DIMM; talón/acuse y ventas siguen bloqueados por límites reales -- SWT de 32 bits, sin certificado de pruebas del SRI); DI25-04.4 comprobado (matriz aprobada el 24-09-2026 por instrucción expresa del titular; docs/evidencias/DI25/DI25-04-cierre.json); DI25-04 permanece cerrada parcial solo por DI25-04.3. DI25-05 cerrada (parcial): DI25-05.1 y DI25-05.2 comprobados (api_key migrado a erpec_secrets; exclusión comercial revisada, sin mecanismo de envío masivo que enforzar); DI25-05.3 (retención ejecutable) y DI25-05.4 (matriz legal completa) NO comprobados, registrados explícitamente (docs/evidencias/DI25/DI25-05-cierre.json). DI25-06 cerrada (parcial): DI25-06.1 y DI25-06.4 comprobados; DI25-06.2 y DI25-06.3 parcialmente comprobados con límites registrados (docs/evidencias/DI25/DI25-06-cierre.json); DI25-07 habilitada, no iniciada.**

DI25-01: cierre técnico en evidencias/DI25/DI25-01-cierre.json. La solicitud posterior autoriza implementar todos los prompts y publicar los cambios.

## Objetivo y alcance

Resolver los hallazgos comprobados y verificar los riesgos de UI/UX, duplicación, errores, operación y cumplimiento Ecuador sobre el producto existente. Mantener Odoo Community y una autoridad por cálculo, documento, asiento y cobro. La publicación inicial fue documental; los cierres posteriores acreditan únicamente las verificaciones registradas.

Respetar RULES.md y AGENTS.md. No alterar repositorios fuente, contratos vigentes, datos de la demo ni evidencias históricas como efecto secundario. No recrear funciones ya construidas en OP/TX/UIUX/CF. Actualizar estado vigente con evidencia nueva y conservar historia.

## Fases y dependencias

| Fase | Resultado | Depende | Hallazgos |
|---|---|---|---|
| DI25-00 — Diagnóstico y planificación | Informe, fuentes, reproducciones, capturas, plan y gobierno. Completada solo como diagnóstico/documentación; no corrige aplicación. | — | Todos |
| DI25-01 — Gobierno y validación confiable | Corregir ejecutores y aislamiento del ensayo; validar dependencias reales de imágenes; verificar cadena y prompts sin modificar evidencias históricas. | DI25-00 | DI25-11, DI25-12, DI25-13, DI25-18 |
| DI25-02 — Integridad fiscal y autoridad única | Cola justa y durable, exclusión bidireccional, inmutabilidad y adaptadores sin duplicación de reglas; estados y recuperación visibles. | DI25-01 | DI25-01, DI25-02, DI25-03, DI25-08, DI25-17 |
| DI25-03 — Nómina, correcciones y RDEP | Cálculo anual conciliado, beneficios conservados, cuotas reversibles y bases laborales justificadas; no reutilizar el mismo motor como único oráculo. | DI25-02 | DI25-04, DI25-05, DI25-06 |
| DI25-04 — Cobertura tributaria y ATS | Comparar catálogo vigente, completar ATS aplicable y conciliación; matriz de tipos, tarifas, regímenes, notas, retenciones y anexos por período. | DI25-03 | DI25-07 |
| DI25-05 — Privacidad, secretos y correo | Cifrar conector, integrar exclusión comercial, operacionalizar derechos/incidentes/retención y definir tratamientos de geolocalización y transferencias. | DI25-04 | DI25-09, DI25-10, DI25-19 |
| DI25-06 — UI/UX coherente y accesible | Inicio real por empresa, estados vacíos y errores accionables, menús claros y marca; recorridos por roles, teclado, foco y pantallas pequeñas. | DI25-05 | DI25-14, DI25-15, DI25-16 |
| DI25-07 — Aceptación operativa y salida controlada | Validar ciclos operativos y despliegue real empaquetado; recuperación, CI, SMTP, SRI y bancos según alcance contratado. Sin gates aprobados no hay cierre comercial. | DI25-06 | DI25-20 y regresión de todos |

Orden estricto DI25-00 → 01 → 02 → 03 → 04 → 05 → 06 → 07. No iniciar sucesora con lock de cierre faltante/inválido. Si una validación externa impide cerrar una fase, registrar bloqueo, terminar tareas independientes de esa misma fase y no simular cierre. Un cambio de orden requiere autorización explícita documentada; ninguna credencial externa es requisito para redactar este plan.

Cada prompt contiene alcance, tareas, pruebas, UI y reversión. El prompt de una fase autoriza esa fase cuando se invoque; no activa automáticamente todas las siguientes.

## Responsables y prioridad

- Responsable técnico: ejecutor del prompt autorizado; preserva cambios ajenos, APIs y evidencia.
- Responsable de aceptación de negocio: designado por el titular para cada rol/proceso; pendiente de identificar antes del cierre comercial.
- Responsable tributario/contable: valida reglas, período, régimen, anexos y emisión real; pendiente de confirmación para DI25-03/04/07.
- Responsable de privacidad: valida tratamientos y aplicabilidad de obligaciones; designación legal de DPD solo cuando proceda.
- Titular/operación: provee destinos y acceso de despliegue, SMTP, bancos y entorno productivo cuando corresponda. No pedir otra vez secretos ya recibidos; verificar su disponibilidad sin exponerlos.

P1 antes de salida del alcance afectado; P2 antes de aceptación comercial del recorrido correspondiente. Estimar esfuerzo después de reproducir cada riesgo, no inventar fechas ni costos.

## DI25-01 — Gobierno y validación confiable

Dependencia: DI25-00. Hallazgos: DI25-11, DI25-12, DI25-13, DI25-18.

Corregir ejecutores y aislamiento del ensayo; validar dependencias reales de imágenes; verificar cadena y prompts sin modificar evidencias históricas.

Tareas / aceptación:

1. **DI25-01.1** Ejecutor Windows rechaza nombres fuera del prefijo y bases/roles existentes antes de mutar; limpieza limitada a recursos creados en esta ejecución y filestore aislado.
2. **DI25-01.2** Linux falla si Docker falla aunque haya resumen verde, si no hay pruebas o si falta un módulo; imágenes controller/customer arrancan sin /extra.
3. **DI25-01.3** Gobierno recorre hasta génesis, rechaza eslabón roto/ciclo/ruta externa y verifica prompts del plan; se conserva compatibilidad histórica.

Entregables: corrección mínima compatible, pruebas pertinentes, evidencia `docs/evidencias/DI25/DI25-01-cierre.json`, contexto vigente y AuditLock encadenado. No crear el cierre hasta ejecutar las validaciones.

Reversión: Restituir versión anterior de ejecutores/empaquetado en rama aislada; no tocar snapshots. Ninguna prueba negativa ejecutará eliminación sobre bases existentes.

## DI25-02 — Integridad fiscal y autoridad única

Dependencia: DI25-01. Hallazgos: DI25-01, DI25-02, DI25-03, DI25-08, DI25-17.

Cola justa y durable, exclusión bidireccional, inmutabilidad y adaptadores sin duplicación de reglas; estados y recuperación visibles.

Tareas / aceptación:

1. **DI25-02.1** Una emisión firmada elegible avanza aunque existan diez bloqueadas recientes; errores de un trabajo no frenan todo el lote.
2. **DI25-02.2** Ningún comprobante adquiere dos autoridades en ninguno de los órdenes ni con dos transacciones concurrentes.
3. **DI25-02.3** Documento firmado/autorizado no admite cambios económicos silenciosos; nota/anulación sigue política fiscal; reintentos no duplican comprobantes.
4. **DI25-02.4** La UI muestra ambiente, autoridad, estado, último error, próxima acción y edad de la cola; medir latencia de despacho y registrar contingencias.

Entregables: corrección mínima compatible, pruebas pertinentes, evidencia `docs/evidencias/DI25/DI25-02-cierre.json`, contexto vigente y AuditLock encadenado. No crear el cierre hasta ejecutar las validaciones.

Reversión: Respaldar antes de migrar; vista previa y script inverso documentado. Preservar comprobantes, claves, XML, consecutivos y auditoría; corregir mediante estados/compensaciones legales.

## DI25-03 — Nómina, correcciones y RDEP

Dependencia: DI25-02. Hallazgos: DI25-04, DI25-05, DI25-06.

Cálculo anual conciliado, beneficios conservados, cuotas reversibles y bases laborales justificadas; no reutilizar el mismo motor como único oráculo.

Tareas / aceptación:

1. **DI25-03.1** Caso salarial variable reproduce la diferencia actual y queda conciliado contra cálculo independiente; creación fuera de orden no altera el año.
2. **DI25-03.2** Reversión/corrección conserva beneficios y saldo de préstamo; no duplica cuotas ni gastos; repetir acción es idempotente.
3. **DI25-03.3** Casos de otros empleadores, exenciones, acumulados, cambio de sueldo, ausencias y cierre anual tienen oráculo aprobado; bloquear regímenes no cubiertos.
4. **DI25-03.4** Frontend permite revisar bases, acumulados, ajustes y diferencias, con política/versionado; XSD RDEP y contenido económico se verifican por separado.

Entregables: corrección mínima compatible, pruebas pertinentes, evidencia `docs/evidencias/DI25/DI25-03-cierre.json`, contexto vigente y AuditLock encadenado. No crear el cierre hasta ejecutar las validaciones.

Reversión: Respaldar datos y política; migración con modo vista previa y tabla de equivalencias. Revertir cuotas/asientos mediante operaciones compensatorias; nunca reescribir asientos contabilizados.

## DI25-04 — Cobertura tributaria y ATS

Dependencia: DI25-03. Hallazgos: DI25-07.

Comparar catálogo vigente, completar ATS aplicable y conciliación; matriz de tipos, tarifas, regímenes, notas, retenciones y anexos por período.

Tareas / aceptación:

1. **DI25-04.1** Catálogo remoto y copia se comparan por contenido/hash y vigencia, preservando períodos antiguos; registrar las diferencias efectivas.
2. **DI25-04.2** ATS concilia compras/ventas/anulados/retenciones/reembolsos aplicables, parciales y notas; presentar vista previa de faltantes con documento origen.
3. **DI25-04.3** Validar estructura oficial y prueba independiente con herramienta/canal oficial aplicable; guardar acuse cuando corresponda, sin declarar presentación por generar XML.
4. **DI25-04.4** Matriz fiscal aprobada por responsable: tipo de contribuyente, obligación contable, IVA/IR/ICE/ISD y exclusiones; sin códigos ni reglas inventados.

Entregables: corrección mínima compatible, pruebas pertinentes, evidencia `docs/evidencias/DI25/DI25-04-cierre.json`, contexto vigente y AuditLock encadenado. No crear el cierre hasta ejecutar las validaciones.

Reversión: Respaldar antes de migrar; vista previa y script inverso documentado. Preservar comprobantes, claves, XML, consecutivos y auditoría; corregir mediante estados/compensaciones legales.

## DI25-05 — Privacidad, secretos y correo

Dependencia: DI25-04. Hallazgos: DI25-09, DI25-10, DI25-19.

Cifrar conector, integrar exclusión comercial, operacionalizar derechos/incidentes/retención y definir tratamientos de geolocalización y transferencias.

Tareas / aceptación:

1. **DI25-05.1** Migración de api_key a erpec_secrets sin valores privados en Git, logs o UI; lectura vacía, uso correcto y rotación/recuperación probadas.
2. **DI25-05.2** Contacto excluido no recibe campaña, incluso por caminos alternativos; rol de pago y comprobante transaccional se rigen por su finalidad.
3. **DI25-05.3** Solicitudes e incidentes se prueban con roles mínimos, fechas y evidencias; conservación ejecutable respeta obligaciones fiscales y bloqueo legal.
4. **DI25-05.4** Matriz legal de tratamientos, geolocalización, encargados/subencargados, transferencias y DPD tiene fundamento vigente y responsable; canales de derechos visibles.

Entregables: corrección mínima compatible, pruebas pertinentes, evidencia `docs/evidencias/DI25/DI25-05-cierre.json`, contexto vigente y AuditLock encadenado. No crear el cierre hasta ejecutar las validaciones.

Reversión: Respaldo cifrado y claves fuera de Git, probados en copia. Revertir referencias/versiones sin volver a almacenar secretos en claro ni reactivar contactos excluidos.

## DI25-06 — UI/UX coherente y accesible

Dependencia: DI25-05. Hallazgos: DI25-14, DI25-15, DI25-16.

Inicio real por empresa, estados vacíos y errores accionables, menús claros y marca; recorridos por roles, teclado, foco y pantallas pequeñas.

Tareas / aceptación:

1. **DI25-06.1** Los cinco pasos capturados se repiten con evidencia nueva y sin contradicciones; no aparece Nuevo si no existe creación permitida.
2. **DI25-06.2** Inicio presenta capacidad instalada y preparación por empresa/ambiente; enlaces útiles, navegación de regreso y errores en español.
3. **DI25-06.3** Pruebas por rol y empresa con anchuras 360/768/1280, teclado, foco, zoom 200 %, contraste medido y lector de pantalla donde disponible; registrar cualquier límite.
4. **DI25-06.4** No retirar acciones públicas sin inventario de consumidores; marca y textos no esconden bloqueos fiscales/laborales reales.

Entregables: corrección mínima compatible, pruebas pertinentes, evidencia `docs/evidencias/DI25/DI25-06-cierre.json`, contexto vigente y AuditLock encadenado. No crear el cierre hasta ejecutar las validaciones.

Reversión: Restaurar vistas/assets y menús previos; verificar ids y navegación. No borrar acciones referenciadas.

## DI25-07 — Aceptación operativa y salida controlada

Dependencia: DI25-06. Hallazgos: DI25-20 y regresión de todos.

Validar ciclos operativos y despliegue real empaquetado; recuperación, CI, SMTP, SRI y bancos según alcance contratado. Sin gates aprobados no hay cierre comercial.

Tareas / aceptación:

1. **DI25-07.1** Ventas→entrega parcial→factura→nota→cobro; compras→recepción parcial→factura→retención→pago→devolución; producción→faltantes→parcial→desperdicio→valoración.
2. **DI25-07.2** Importación multiproducto/divisa/costos; nómina→novedades→beneficios→anticipo→asiento→pago→reversión; visitas planificadas/omitidas/excepciones; plan SaaS→cobro→aprovisionamiento sin duplicar.
3. **DI25-07.3** Roles vendedor/comprador/bodega/operario/supervisor/nómina/contador/administrador: permisos, multiempresa, errores, vacíos, reintentos y doble acción concurrente.
4. **DI25-07.4** Imagen final sin montajes, CI remoto del commit final, respaldo DB+filestore+clave separada y restauración aislada con RPO/RTO medidos.
5. **DI25-07.5** SRI producción supervisada por responsable, SMTP con destinatario autorizado y homologación por banco/servicio solo con autorización específica; cada externo tiene acuse o bloqueo explícito.
6. **DI25-07.6** Salida por alcance: cero P1 abiertos en funciones liberadas, regresión aprobada, aceptación de negocio y evidencia legal/operativa. Una función bloqueada queda deshabilitada/claramente excluida, nunca marcada como cumplida.

Entregables: corrección mínima compatible, pruebas pertinentes, evidencia `docs/evidencias/DI25/DI25-07-cierre.json`, contexto vigente y AuditLock encadenado. No crear el cierre hasta ejecutar las validaciones.

Reversión: Procedimiento de vuelta al despliegue anterior con respaldos comprobados; documentos autorizados y pagos reales no se deshacen con rollback técnico.


## Contrato transversal de cada cierre

1. Leer reglas, contexto vigente, plan y prompt; ejecutar `node scripts/verify-governance.cjs` antes de modificar.
2. Reproducir defecto o confirmar límite con datos ficticios/copia aislada; registrar resultado previo. No ejecutar repros destructivas ni contactar autoridades para demostrar riesgos.
3. Verificar usos antes de cambiar función pública; evitar contratos o estados paralelos. Migraciones reversibles y compatibilidad explícita.
4. Implementar frontend junto al comportamiento: rutas, permisos, navegación, vacío, carga, error y bloqueo externo con siguiente acción. Un arreglo oculto solo en backend no cierra fase.
5. Validar código afectado y suite integrada cuando corresponda. Registrar fallos/omisiones y commit probado. No atribuir resultados históricos al cambio nuevo ni usar planificación como prueba.
6. Guardar bytes exactos del lock vigente en snapshot único; SHA256 del predecesor; firma SHA256(bytes anteriores + updatedAt UTF-8). Hashes de entregables excluyen el propio lock.
7. Guardar UTF-8 sin BOM, comprobando `Buffer.from(text, 'utf8').toString('utf8') === text` en cada escritura. Imágenes/PDF se inventarían en un manifiesto binario con hashes, no se pasan como texto al verificador heredado.
8. En DI25 usar objeto complementario del lock, preservando `phaseCompleted=ERPEC26-03` y la fase histórica 04 parcial hasta que su gate propio cambie. No falsificar cierre maestro.
9. Ejecutar gobierno al cerrar y registrar comandos, resultados y límites. Commits cuando estén autorizados: `phase: DI25-XX task: DI25-XX.Y`. No publicar secretos ni modificar repositorios fuente.
10. Pasar a la fase siguiente solo con dependencia cerrada y autorización correspondiente.

## Matriz de verificación

| Área | Caso positivo | Caso negativo / control | Evidencia |
|---|---|---|---|
| Fiscal | Firmar, despachar, consultar y conciliar | Doble autoridad, timeout, fuera de orden, devolución, bloqueo, concurrencia, edición posterior | XML/hash, estados, trazas sin secretos, pruebas y captura |
| Nómina/RDEP | Año variable y corrección completa | Otros empleadores, beneficios diferenciados, anticipo parcialmente consumido, períodos creados fuera de orden | Oráculo independiente, asientos, saldos y XML |
| UI/UX | Usuario completa tarea desde inicio | Sin permisos, vacío, error y bloqueo externo; teclado/móvil | Capturas nuevas por rol/paso y hallazgos cerrados |
| Privacidad/correo | Derechos y transaccionales pertinentes | Campaña excluida, acceso entre empresas, retención vencida y conservación legal | Pruebas, matriz de tratamiento y evidencias operativas |
| Operación | Flujos comerciales enlazados | Parciales, devoluciones, reversión, sin existencias y reintentos | Conciliación contra fuente nativa y aceptación por rol |
| Despliegue | Imagen final y recuperación | Dependencia ausente, resumen verde con exit fallido, nombre de base ajena, clave ausente | CI, arranque sin fuentes montadas, restauración aislada |

## Registro de pendientes externos

Conservar pendientes del AuditLock anterior: permisos para seis carpetas de recuperación, producción fiscal supervisada, SMTP, ERPEC_SECRET_KEY en plataforma, CI remoto/despliegue Render y retiro controlado de claves anteriores. La purga no es requisito de correcciones de código ni se ejecuta en este diagnóstico. Añadir homologación bancaria y aceptación de roles cuando aplique al alcance.

No afirmar que el certificado propio falta: contexto OP17 y ensayos posteriores documentan su existencia. Verificar vigencia, entorno y disponibilidad privada cuando vaya a utilizarse. No usar certificado o comprobantes reales en las pruebas de regresión ordinarias.

## Criterio de finalización

Diagnóstico y plan se consideran entregados al existir informe, evidencia, ocho prompts, contexto actualizado y lock válido. Producto corregido/comercializable requiere DI25-01–07 ejecutadas, aceptación del alcance liberado y gates históricos/externos pertinentes; son hitos diferentes.

## DI25-03 — pronunciamiento y validaciones automáticas

El pronunciamiento técnico recibido observa y devuelve la versión 18.0.1.11.0. El incremento 18.0.1.12.0 corrige edad y rebaja aplicada, añade bloqueos en servidor y huellas de datos revisados, y automatiza la auditoría de los 32 ejemplos con salida verificable. Alcance, fuentes y desarrollo aún pendiente: [Controles automáticos DI25-03](DI25-03_CONTROLES_AUTOMATICOS.md). Resultados ejecutados: [Evidencia](evidencias/DI25/DI25-03-controles-automaticos.json). No cierra DI25-03 ni habilita DI25-04. No sustituye importación versionada, reliquidación acumulada, expediente acreditado ni conciliación integral por una marca manual.
