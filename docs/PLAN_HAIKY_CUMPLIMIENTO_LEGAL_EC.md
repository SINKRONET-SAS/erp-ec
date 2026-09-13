# Plan HAIKY — Cumplimiento legal Ecuador (Tributario, Facturación Electrónica, ATS, RDEP, Laboral, Protección de Datos, Envíos por email)

Autorizado por el titular el 13-09-2026, en respuesta a la necesidad de garantizar el cumplimiento legal del ERP en Ecuador. Complementa PLAN_HAIKY_ERPEC26.md y PLAN_AMPLIACION_OPERATIVA.md; no cierra ni sustituye sus fases. Este plan consolida y ordena seis dominios legales bajo un mismo gobierno; **no declara homologación ni cumplimiento legal alcanzado en ningún dominio** — es un mapa de lo ya construido, lo verificado contra fuente oficial y lo que falta, con su siguiente acción concreta.

## Principio del plan

Cada dominio se documenta con: qué exige la norma (con fuente oficial citada), qué cubre hoy el ERP, qué falta y cuál es el siguiente paso verificable. Donde ya existe documentación propia detallada (Facturación Electrónica, ATS, RDEP), este plan remite a ella en vez de duplicarla. No se inventan artículos, plazos, multas ni catálogos; lo no confirmado contra fuente oficial queda marcado explícitamente. Los envíos de correo, firmas y transmisiones reales al SRI permanecen desactivados salvo autorización expresa y ambiente de pruebas.

## Fases

| Fase | Dominio | Estado al abrir este plan | Dependencia |
|---|---|---|---|
| LEGAL-00 | Gobierno y alcance | Este documento, CODEX_CONTEXT, AuditLock y prompt. Documental. | Ninguna |
| LEGAL-01 | Tributario general (impuestos, retenciones, contabilidad) | Parcial: `erpec_withholding_accounting` (retenciones contables), balance de comprobación nativo | LEGAL-00 |
| LEGAL-02 | Facturación Electrónica (SRI) | Parcial: `erpec_fiscal_native` — vista previa XML sin firma; ver docs/FACTURACION_LOCAL.md | LEGAL-00 |
| LEGAL-03 | ATS (Anexo Transaccional Simplificado) | Catálogo oficial obtenido; generación de compras/ventas pendiente; ver docs/ALCANCE_ATS_RDEP.md | LEGAL-00 |
| LEGAL-04 | RDEP (Relación de Dependencia) | Agregador y vista previa XML validada contra esquema oficial; ver docs/ALCANCE_ATS_RDEP.md | LEGAL-00 |
| LEGAL-05 | Laboral (más allá de RDEP: IESS, liquidaciones, ausencias, otros regímenes) | Parcial: `erpec_payroll` — parámetros reales 2026, décimos, fondo de reserva, IESS, tope de gastos personales | LEGAL-00 |
| LEGAL-06 | Protección de Datos Personales (LOPDP) | No iniciado antes de este plan | LEGAL-00 |
| LEGAL-07 | Envíos por email (transaccionales y comerciales) | No iniciado antes de este plan; infraestructura nativa de correo presente pero desactivada | LEGAL-00 |

## LEGAL-01 — Tributario general

Cubierto hoy: `erpec_withholding_accounting` registra retenciones emitidas/recibidas como documentos contables independientes, con cuenta tributaria, tarifa verificada y asiento balanceado; balance de comprobación nativo agrupa apuntes contabilizados por empresa/período. No determina automáticamente tarifas legales por producto/proveedor, ni sustituye una declaración de impuestos. Ver docs/CONTABILIDAD_Y_DEMO.md.

Falta: validación normativa vigente de tarifas y catálogos tributarios generales (más allá de IVA/renta ya usados), régimen del contribuyente (general, RIMPE, contribuyente especial, agente de retención) aplicado de forma consistente entre facturación y retenciones, y declaraciones (formularios 103/104 u otros) — ninguna se genera hoy.

## LEGAL-02 — Facturación Electrónica (SRI)

Estado y brechas ya documentados en detalle en docs/FACTURACION_LOCAL.md; no se duplica aquí. Resumen: vista previa XML local sin firma, sin autoridad de secuencias durable, sin firma XAdES con certificado real, sin transmisión/consulta SRI, sin RIDE autorizado ni archivo fiscal durable. Facturador (SINKRONET) sigue disponible como alternativa API; no se ha migrado autoridad.

## LEGAL-03 y LEGAL-04 — ATS y RDEP

Estado y brechas ya documentados en detalle en docs/ALCANCE_ATS_RDEP.md; no se duplica aquí. Resumen: catálogo ATS oficial obtenido y transcrito (`erpec_fiscal_native/ats_catalog.py`); generación de compras/ventas del ATS pendiente de un dato que hoy no existe en el ERP (clasificación de sustento tributario por documento). RDEP con motor de nómina ampliado y XML de vista previa validado contra el esquema oficial; dos campos (`intGrabGen`, y el efecto vigente exacto de `benGalpg` tras 2021) siguen sin fuente primaria narrativa confirmada. Ningún anexo se ha presentado ante el SRI.

## LEGAL-05 — Laboral (más allá de RDEP)

Cubierto hoy: motor de nómina nativo con parámetros reales 2026 (salario básico, IESS personal/patronal, fondo de reserva, décimo tercero/cuarto, tabla de impuesto a la renta, tope de gastos personales escalado por cargas familiares y Galápagos desde el incremento OP05.5). Cierre, asiento idempotente, reversión y corrección.

Falta (ya documentado en docs/OPERACIONES_LOCALES_DEMO.md y CODEX_CONTEXT.md): acumulados y retenciones previas de un empleado que cambia de empleador, bases independientes por novedad, ausencias, liquidaciones (indemnización, desahucio), cargas familiares y exenciones más allá de las ya usadas en RDEP, otros regímenes (tiempo parcial, artesanos, otros), y equivalencia laboral integral frente a SKNOMINA. No se declara equivalencia integral.

## LEGAL-06 — Protección de Datos Personales (LOPDP)

Investigación del 13-09-2026. No iniciado antes de este plan: el ERP no tiene hoy registro de actividades de tratamiento, base legal documentada por finalidad, mecanismo de derechos del titular ni procedimiento de notificación de incidentes.

**Identificación** (confianza alta, fuente primaria): Ley Orgánica de Protección de Datos Personales, Registro Oficial Suplemento N.° 459, 26-05-2021 (asambleanacional.gob.ec). El régimen sancionatorio entró en vigor el 26-05-2023 (dos años de transición, primera disposición transitoria).

**Regulador**: Superintendencia de Protección de Datos Personales (SPDP), spdp.gob.ec — operativa y emitiendo resoluciones vigentes en 2025-2026 (reglamento del Delegado de Protección de Datos, julio 2025; metodología de cálculo de multas; regla general de transferencias, enero 2026). No confirmado si aplica sanciones activamente a empresas privadas hoy o solo emite lineamientos.

**Obligaciones relevantes para un ERP** (confianza variable, ver notas):
- Base legal por finalidad (Art. 7): consentimiento, obligación legal, necesidad contractual/precontractual, interés vital, interés público, fuente pública o interés legítimo. Facturación y nómina pueden ampararse en necesidad contractual/obligación legal, no solo consentimiento.
- Consentimiento (Art. 8): libre, específico, informado, inequívoco y revocable; casillas premarcadas u opt-out son inválidas.
- Derechos del titular: información, acceso, rectificación/actualización, eliminación, oposición, portabilidad (formato estructurado e interoperable). Confianza media-alta en la lista; números de artículo no verificados contra el texto primario completo.
- Registro de Actividades de Tratamiento (RAT): inventario interno de tratamientos. Fuentes secundarias citan un umbral de 100 o más empleados para su obligatoriedad (Reglamento General, artículo no confirmado); **este umbral no está verificado contra fuente primaria** y no debe tomarse como definitivo.
- RNPD (registro público, administrado por la SPDP): las transferencias internacionales deben registrarse ahí específicamente.
- Delegado de Protección de Datos (DPD, Art. 49): obligatorio para entidades públicas, monitoreo sistemático a gran escala, tratamiento a gran escala de datos sensibles, y explícitamente para instituciones educativas con datos de menores, entidades financieras, aseguradoras y salud. Reglamento del DPD emitido 30-07-2025; plazo del sector privado para designar y registrar DPD: 31-12-2025. Una empresa sin tratamiento a gran escala ni datos sensibles probablemente no lo requiere; debe evaluarse caso por caso, no asumirse.
- Notificación de vulneraciones: fuentes secundarias (incluida una página de trámite de gob.ec) indican 5 días para que el responsable notifique a la SPDP y 2 días para que el encargado notifique al responsable; **no verificado contra el artículo estatutario primario**.
- Transferencias internacionales: requieren consentimiento libre/específico/informado/inequívoco u otro mecanismo lícito, y registro en el RNPD.
- Sanciones: leves 0,1-0,7%, graves 0,7-1%, muy graves 1-2% de la facturación del ejercicio anterior (sector privado); sector público en SBU.

**Sin confirmar / pendiente**: números de artículo exactos de derechos, notificación de brechas y umbral del RAT (provienen de blogs jurídicos, no del texto primario, que resistió la extracción directa); si la SPDP ya sanciona activamente a privados o solo orienta.

**Siguiente paso concreto**: leer el texto primario completo de la LOPDP y su Reglamento General (no solo resúmenes) antes de modelar el RAT u otro artefacto de cumplimiento, para no fijar umbrales o plazos con un número de artículo no verificado.

## LEGAL-07 — Envíos por email

Investigación del 13-09-2026. La infraestructura nativa de correo de Odoo (`ir.mail_server`) existe pero está deliberadamente desactivada en la demo (`seed-ui-acceptance.py` la desactiva explícitamente); no hay módulo propio de envío.

**Entrega de comprobantes electrónicos por email** (SRI): el Reglamento de Comprobantes de Venta, Retención y Documentos Complementarios y la Ficha Técnica de Comprobantes Electrónicos rigen la facturación electrónica; el RIDE es la representación impresa/visual (PDF/JPG/PNG/papel) de un comprobante autorizado por el SRI. Fuentes secundarias (no verificadas contra el texto primario del Reglamento, que no se pudo extraer directamente) indican que el sistema envía el XML autorizado más el RIDE en PDF al correo del cliente, y que la entrega física solo es obligatoria si el cliente no tiene correo, falla el envío, pide papel expresamente, o la transacción es presencial.

**No se encontró un plazo específico de "debe entregarse al cliente en X horas"**. El único plazo confirmado es de **transmisión al SRI** (no al cliente): ampliado recientemente de 24 a **72 horas** desde la generación del documento, según una resolución del SRI de 2025. No debe confundirse con el plazo de entrega al cliente, que no está acreditado.

**Consentimiento LOPDP para correos comerciales**: un correo transaccional (enviar la factura de una venta ya realizada) se ampara en la base legal de necesidad contractual (Art. 7 LOPDP), no en consentimiento de mercadeo. Un correo de mercadeo/promocional sí requeriría consentimiento conforme a la LOPDP.

**Ley antispam**: la Ley de Comercio Electrónico, Firmas Electrónicas y Mensajes de Datos (Ley 67, 2002) exige que quien envíe mensajes periódicos/masivos provea un mecanismo sencillo de exclusión (unsubscribe); seguir enviando tras una solicitud de exclusión es sancionable.

**No se encontró** un requisito legal de registro SPF/DKIM ni de registro de remitentes comerciales; se trata como no confirmado/probablemente inexistente como mandato legal (es práctica de entregabilidad técnica, no ley).

**Siguiente paso concreto**: antes de activar cualquier envío real, confirmar contra el texto primario del Reglamento de Comprobantes Electrónicos si existe un plazo de entrega al cliente distinto del plazo de transmisión al SRI, y decidir el mecanismo de exclusión exigido por la Ley 67 si se van a enviar comunicaciones periódicas.

## Decisiones pendientes

- Orden de ejecución entre LEGAL-06/07 (dominios nuevos) y profundizar LEGAL-01/03/05 (dominios con brecha ya identificada): este plan no decide cuál se implementa primero; cada incremento requiere autorización específica de alcance, igual que las fases anteriores.
- Ninguna fase de este plan autoriza envío real de correos, transmisión al SRI, ni recolección real de datos personales de terceros fuera de los perfiles sintéticos ya usados en la demo.
