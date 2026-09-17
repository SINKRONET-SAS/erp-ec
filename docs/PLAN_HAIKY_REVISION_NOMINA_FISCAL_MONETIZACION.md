# Plan HAIKY — revisión de nómina, facturación electrónica y monetización

Autorizado por el titular el 14-09-2026. Este plan realiza una pasada transversal sobre el comportamiento ya implementado y sus puertas de pruebas y producción. No sustituye una homologación laboral, tributaria, bancaria o del proveedor de pagos.

## Objetivo

Determinar con evidencia reproducible qué cálculos, reportes y transiciones funcionan; corregir defectos comprobables dentro del alcance local; y separar con claridad los controles disponibles de los requisitos pendientes para producción.

## Fases

1. **CF01-A — Inventario y gobierno.** Validar la cadena vigente, conservar el lock anterior e identificar autoridades, ambientes, reportes y verificadores.
2. **CF01-B — Nómina.** Ejecutar regresión aislada; revisar entradas, redondeos, aportes, impuesto a la renta, provisiones, asiento, pago conciliado, corrección y RDEP. Contrastar parámetros vigentes con fuentes oficiales y registrar los casos laborales no cubiertos.
3. **CF01-C — Facturación electrónica.** Probar preparación local y conector; revisar identidad, ambiente, idempotencia, estados, XML, firma, envío, consulta, RIDE y archivo. Pruebas y producción se evalúan por separado.
4. **CF01-D — Monetización.** Ensayar planes versionados, contratos, cobro PayPhone y aprovisionamiento. Revisar tarifa, impuestos, moneda, renovación, cancelación, reembolso, mora, derechos y medición de consumo.
5. **CF01-E — Corrección y cierre.** Corregir fallos reproducibles que no requieran credenciales ni decisiones comerciales; repetir pruebas, registrar evidencia y actualizar el gobierno. Las brechas de producto quedan priorizadas, no declaradas como aprobadas.

## Criterios de salida

- Cada afirmación funcional se apoya en una prueba ejecutada o inspección directa identificable.
- Los cálculos monetarios usan precisión decimal y casos de frontera representativos.
- Ningún estado de prueba se presenta como producción ni una vista previa como documento autorizado.
- Un pago confirmado no concede derechos si contrato, importe, vigencia o aprovisionamiento no concilian.
- Los verificadores son repetibles sobre bases aisladas y no dependen de datos comerciales preexistentes.
- El informe final clasifica cada punto como aprobado localmente, limitado, fallido o bloqueado por validación externa.

## Límites

No se emitirán comprobantes al SRI, no se harán cargos o reembolsos reales, no se transmitirán archivos bancarios y no se activará nómina para empresas reales. Producción requiere credenciales segregadas, infraestructura, pruebas externas y responsables fiscal, laboral y comercial.
