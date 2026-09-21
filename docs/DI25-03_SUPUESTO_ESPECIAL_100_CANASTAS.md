# Estado posterior al pronunciamiento técnico

Documento histórico de la versión 18.0.1.11.0 o anterior. El pronunciamiento devuelve DI25-03 para corrección y prevalece la respuesta en [Controles automáticos](DI25-03_CONTROLES_AUTOMATICOS.md). La referencia aislada ya no habilita sustitutos ni 100 canastas en la nómina operativa; los ensayos aritméticos permanecen separados. Las propuestas del borrador no constituyen decisiones aceptadas. DI25-03 sigue observado.

---

# DI25-03 · Supuesto especial del titular o sus cargas · 2026

## Constatación normativa

Revisión del 21-09-2026. Se cierra la falta de referencia normativa para la rebaja especial; la cobertura funcional se acredita por separado en evidencias/DI25/DI25-03-100-canastas.json. No constituye aceptación nominal del experto ni cierre integral de DI25-03.

- La publicación del Decreto Ley de Fortalecimiento de la Economía Familiar corresponde al [Suplemento RO 335, 20-06-2023](https://www.registroficial.gob.ec/suplemento-al-registro-oficial-no-335/), no al RO 329 del 19 de junio.
- La disposición específica está en el segundo artículo innumerado posterior al artículo 10 de la LRTI, literal c. La [consolidación publicada por SRI, página 32](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/be41e8fa-cd33-4a47-b661-26a01673426a/LEY_DE_REGIMEN_TRIBUTARIO_INTERNO_-_LRTI_REFORMA2024.pdf) recoge la sustitución por el artículo 7 de la reforma publicada en RO 461-S de 20-12-2023: incluye discapacidad y establece 100 canastas. El artículo 36 regula la tarifa general, no es la ubicación precisa de esta rebaja.
- La [circular NAC-DGECCGC24-00000001](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar?id=0309fca2-4b41-4b24-837f-e274b83a8b86&nombre=NAC-DGECCGC24-00000001.pdf), páginas 1–3, se refiere al ejercicio 2023 y reproduce 20 canastas. Ese antecedente no se aplica a los ensayos de 2026.
- El [SRI, publicación de 06-02-2026](https://www.sri.gob.ec/detalle-noticias?idnoticia=1261&marquesina=1), confirma 18 % sobre el menor entre gastos y 100 canastas cuando el contribuyente o una carga tiene discapacidad o enfermedad catastrófica, rara o huérfana. La canasta de enero es 821,80 y el factor insular es 1,803. El boletín aportado fue cotejado en DI25-03_VERIFICACION_BOLETIN_SRI.md.

## Fórmula y ejemplos independientes

Tope continental = 821,80 × 100 = **82.180,00**. Rebaja máxima calculada = **14.792,40**.
Tope Galápagos = 82.180 × 1,803 = **148.170,54**. Rebaja máxima calculada, redondeada a centavos = **26.670,70**.
Rebaja = 18 % × menor(gastos válidos, tope). IR después de rebaja = máximo(0, impuesto causado − rebaja). El exceso de rebaja sobre el impuesto no genera por sí mismo devolución. El tope especial sustituye al ordinario: no se suman ni multiplican canastas por número de cargas.

| Caso demo | Datos ficticios y cálculo independiente | IR anual esperado |
|---|---|---:|
| 20 · Titular | Ingreso 60.000; IESS supuesto 5.670; base 54.330; causado 6.903,75; gastos 30.000; rebaja 5.400 | 1.503,75 |
| 21 · Una carga | Mismos importes, supuesto especial en una carga familiar | 1.503,75 |
| 22 · Exceso de rebaja | Mismo causado; gastos 100.000; rebaja calculada 14.792,40; sin retenciones previas ni devolución automática | 0,00 |
| 23 · Tope continental | Ingreso 240.000; IESS supuesto 22.680; base 217.320; causado 24.572 + (217.320 − 109.956) × 37 % = 64.296,68; gastos 200.000; rebaja 14.792,40 | 49.504,28 |
| 24 · Tope insular | Mismo causado; gastos 200.000; rebaja 26.670,70; elegibilidad insular sujeta a revisión | 37.625,98 |
| 25 · Sin gastos | Causado 6.903,75; gastos cero; rebaja cero | 6.903,75 |

La tasa IESS 9,45 % es un supuesto privado general de los ejemplos; se ingresa el aporte por separado. Estos oráculos son constantes aritméticas independientes del motor. No son certificados de ingresos ni gastos reales.

## Exposición y límites

Áreas → Nómina → Ensayos tributarios de renta. Campo «Supuesto de rebaja»: general, titular ficticio o carga familiar ficticia. El último exige al menos una carga. Editar gastos, cargas, región e ingreso anterior debe recalcular; guardar conserva el ensayo; restablecer recupera la referencia sin borrar observaciones.

El motor común incorpora un argumento opcional explícito, falso por defecto. Las llamadas existentes de nómina y RDEP conservan el régimen previo: este incremento expone la condición en la demo, no declara integrada su acreditación en nómina productiva o XML. No se altera el contrato de salida ni se duplica la fórmula.

La rebaja especial no equivale a la exención de ingresos por discapacidad. No se calculan aquí grado, fecha efectiva, sustitución ni exención por tercera edad; tampoco se validan certificados sanitarios, parentesco, dependencia, gastos o residencia. La referencia de discapacidades de 2017 no se usa para fijar porcentajes o requisitos actuales. Conservar esos pendientes separados evita declarar cobertura no implementada.

## Compatibilidad y reversión

Campo nuevo con valor general por defecto en registros existentes; los 19 casos previos se conservan al repetir el seed. Antes de instalar se respalda base, filestore y módulo; las huellas económicas se comparan antes/después. Para volver al comportamiento previo en un ensayo basta elegir «General» o restablecer su referencia ordinaria. Una retirada de versión debe ensayarse en copia aislada con el respaldo, sin sobrescribir actividad posterior. No se acredita restauración solo por crear el respaldo.
