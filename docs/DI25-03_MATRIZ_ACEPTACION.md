Actualización: exenciones personales integradas

Adulto mayor, discapacidad y sustituto implementados (LRTI art. 9 num. 12, codificación SRI 01-04-2026; Reglamento LRTI arts. 49-50; Reglamento LOD art. 6), con acreditación por año, controles y bloqueo de casos no cubiertos. Integrados en el cálculo mensual, el agregador RDEP (exoTerEd/exoDiscap) y los ensayos; el tope de 100 canastas también llega ya a nómina y RDEP. Ensayos 26–32 (32 casos en total). Windows: 478 pruebas, 0 fallos, 0 errores, 5 omisiones, salida 0 (módulo de nómina 113 sin fallos). Linux (CI 35645129313, commit c47359d): 478 pruebas, 0 fallos, 0 errores, y los cinco trabajos aprobados. Demo local actualizada con respaldo previo, 32 casos visibles y huellas económicas idénticas antes y después. Borrador de respuestas para el responsable en docs/DI25-03_BORRADOR_RESPUESTAS_RESPONSABLE.md. Ver docs/DI25-03_EXENCIONES_PERSONALES.md, docs/DI25-03_PAQUETE_ACEPTACION.md y docs/evidencias/DI25/DI25-03-exenciones-personales.json. No hay aceptación del responsable tributario: DI25-03 permanece parcial y no inicia DI25-04. Esta actualización prevalece sobre las exenciones «pendientes de implementar» de los estados inferiores.

---

# Actualización: supuesto especial de 100 canastas

Referencia normativa constatada y corregida para 2026. Ver docs/DI25-03_SUPUESTO_ESPECIAL_100_CANASTAS.md. Seis ejemplos nuevos (20–25) instalados y verificados en demo: 25 casos en total. Windows/Linux: 459 pruebas sin fallos/errores; Windows 5 omisiones. Evidencia: docs/evidencias/DI25/DI25-03-100-canastas.json. El pendiente de base normativa queda resuelto; la aceptación del experto y las exenciones de la base siguen separadas. Esta actualización prevalece sobre la exclusión histórica de 100 canastas indicada abajo. DI25-03 permanece parcial y no inicia DI25-04.

---

# Estado actualizado: demo y contraste externo verificados

Verificación del 21-09-2026: 19 casos instalados y visibles en Áreas → Nómina → Ensayos tributarios de renta. Edición, persistencia, rechazo de IESS inválido y restablecimiento comprobados en pantalla. Suite del motor: 457 pruebas Windows y 457 Linux, sin fallos ni errores; Windows reporta 5 omisiones de entorno. Ajustes posteriores solo de presentación XML verificados en demo; CI final 0623125 aprobado: 457 pruebas Linux sin fallos/errores, perfiles customer/controller, gobierno y dependencias aprobados. Boletín SRI aportado cotejado byte a byte con la descarga oficial: ver docs/DI25-03_VERIFICACION_BOLETIN_SRI.md. Esto acredita contraste documental y ensayos, no aceptación nominal del experto. DI25-03 permanece parcial; no iniciar DI25-04.

Evidencia: docs/evidencias/DI25/DI25-03-ensayos-renta.json. Esta actualización prevalece sobre los estados históricos inferiores.

---

# Casos de demo para revisión externa — ampliación autorizada

Paquete de 19 ejemplos implementado, en validación antes de actualizar la demo. Guía: [Ensayos de renta](DI25-03_ENSAYOS_RENTA_DEMO.md). Evidencia vigente del paquete: evidencias/DI25/DI25-03-ensayos-renta.json.

| Pendiente de la matriz | Ejemplos preparados | Límite que permanece |
|---|---|---|
| Otro empleador y acumulados | 01–03; acumulado sumado una vez, IESS y retenciones separados | Cotejo con comprobante y aceptación externa; XML sigue bloqueado |
| Cambio salarial y ausencias | 04–05; efecto anual de remuneración variable | Justificar descuento y cada base laboral; no calcula automáticamente días/contratos |
| Tarifa, gastos y cargas | 06–17; USD 5.000 mensuales, seis niveles de cargas, dos regiones | Sustento de gastos/cargas, elegibilidad insular y aceptación |
| Décimos y reserva | 18; total informado separado del gravado | Devengo, bases diferenciadas y mapeo integral RDEP |
| Cierre anual del impuesto | 19; impuesto y retenciones conciliados | Cierre completo del anexo y referencia aprobada |
| Exenciones personales y regímenes especiales | Conservan bloqueo previo; no se simula cobertura | Referencias de tercera edad/discapacidad, convenios e impuesto asumido |

Los ejemplos reducen la falta de material revisable; no convierten la coincidencia aritmética ni una observación guardada en aprobación tributaria.

---

# DI25-03 — Matriz para aceptación tributaria y laboral

Estado: pendiente. Esta matriz prepara la revisión; no constituye aprobación ni autoriza datos reales.

Responsable tributario/contable: pendiente de identificación por el titular. Fecha, identificación de revisión y evidencia de aprobación: pendientes.

| Caso | Entrada y resultado de referencia | Estado comprobado / aceptación necesaria |
|---|---|---|
| Año variable, orden distinto | Tabla sintética: 11 × 1000 + 3000; IESS 1400; base 12600; impuesto 60. Meses creados 12,3,1,9,2,7,11,5,6,4,10,8. | Automatizado y visible. Validar política aplicable a una empresa real. |
| Tarifa 2026 | Base 12677; fracción cero 12208; tarifa 5 %; impuesto 23,45. Gastos 100 y rebaja 18 % → 18; impuesto después de rebaja 5,45. | Oráculo aritmético independiente; falta aceptación del responsable. Fuente oficial enlazada en DI25-03_NOMINA_RDEP.md. |
| Beneficio corregido | Beneficio 125 con nota; reversión y corrección deben conservar tipo, monto y nota, y volver al mismo neto bajo la misma política. | Automatizado. Determinar bases legales separadas de IESS, IR, décimos, vacaciones y reserva por concepto. |
| Préstamo corregido | Total 250, cuota 100. Saldo 150 al calcular; 250 al revertir; 150 tras corrección. Dos filas históricas, una vigente. | Automatizado y visible; sin desembolso real. |
| Otros empleadores | Definir ingreso, IESS y retención certificados, período y si el importe es flujo o acumulado importado. | XML bloqueado. Se requiere caso de referencia con certificado y resultado anual aprobado, usando datos anonimizados. |
| Exenciones | Definir año, condición aplicable, grado y fecha efectiva, sustitución y prioridad/incompatibilidad de beneficios. | Implementado con acreditación por año y bloqueo de casos no cubiertos (ver DI25-03_EXENCIONES_PERSONALES.md); falta aceptación y las decisiones de criterio de DI25-03_PAQUETE_ACEPTACION.md. Otros regímenes siguen bloqueados. |
| Acumulados y gastos | Definir fuente de ingresos/retenciones anteriores y cómo se evita repetir acumulados en varios meses; gastos efectivos frente a proyección. | Agregación de flujos probada; falta caso certificado de importación y conciliación completa. |
| Cambios de sueldo y ausencias | Caso salarial variable cubierto; definir días, tipo de ausencia, efectos en cada base y retención acumulada. | Cambio salarial anual probado. Ausencias y reliquidación mensual pendientes de oráculo. |
| Décimos y reserva | Acordar montos pagados/acumulados y mapeo anual según política y régimen, incluyendo mensualización. | Cobertura integral no aceptada; no liberar RDEP productivo. |
| Cierre anual | Cuadrar ingresos, IESS, retenciones, impuesto, diferencias, décimos, reserva y XML contra referencia independiente. | XSD y casos económicos separados; pendiente referencia oficial/contable completa. |
| Galápagos, no residencia, convenio, impuesto asumido | Definir aplicabilidad y caso completo con bases y retenciones, además de la escala de gastos. | XML bloqueado; no inferir cobertura del régimen desde un parámetro aislado. |

La aceptación debe señalar expresamente qué filas y años/regímenes cubre, resultados esperados y evidencia revisada. Una confirmación genérica de continuar no se registra como homologación. La autorización para implementar y publicar ya existe y no se pide otra vez.

Según el plan, DI25-04 depende de cierre firmado de DI25-03. Hasta aprobar los casos faltantes y completar su implementación/validación, DI25-03 permanece parcial y DI25-04–07 no comienzan. Un cambio de este orden requiere una instrucción explícita del titular.
