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
| Exenciones | Definir año, condición aplicable, grado y fecha efectiva, sustitución y prioridad/incompatibilidad de beneficios. | XML bloqueado. Validar la norma vigente; se retiró la aplicación automática de fórmulas heredadas no justificadas. |
| Acumulados y gastos | Definir fuente de ingresos/retenciones anteriores y cómo se evita repetir acumulados en varios meses; gastos efectivos frente a proyección. | Agregación de flujos probada; falta caso certificado de importación y conciliación completa. |
| Cambios de sueldo y ausencias | Caso salarial variable cubierto; definir días, tipo de ausencia, efectos en cada base y retención acumulada. | Cambio salarial anual probado. Ausencias y reliquidación mensual pendientes de oráculo. |
| Décimos y reserva | Acordar montos pagados/acumulados y mapeo anual según política y régimen, incluyendo mensualización. | Cobertura integral no aceptada; no liberar RDEP productivo. |
| Cierre anual | Cuadrar ingresos, IESS, retenciones, impuesto, diferencias, décimos, reserva y XML contra referencia independiente. | XSD y casos económicos separados; pendiente referencia oficial/contable completa. |
| Galápagos, no residencia, convenio, impuesto asumido | Definir aplicabilidad y caso completo con bases y retenciones, además de la escala de gastos. | XML bloqueado; no inferir cobertura del régimen desde un parámetro aislado. |

La aceptación debe señalar expresamente qué filas y años/regímenes cubre, resultados esperados y evidencia revisada. Una confirmación genérica de continuar no se registra como homologación. La autorización para implementar y publicar ya existe y no se pide otra vez.

Según el plan, DI25-04 depende de cierre firmado de DI25-03. Hasta aprobar los casos faltantes y completar su implementación/validación, DI25-03 permanece parcial y DI25-04–07 no comienzan. Un cambio de este orden requiere una instrucción explícita del titular.
