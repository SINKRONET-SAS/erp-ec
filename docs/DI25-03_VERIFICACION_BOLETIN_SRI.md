# Actualización: supuesto especial de 100 canastas

Referencia normativa constatada y corregida para 2026. Ver docs/DI25-03_SUPUESTO_ESPECIAL_100_CANASTAS.md. Se añaden seis ejemplos (20–25) al ensayo; validación integrada e instalación en curso. El pendiente de base normativa queda resuelto; la aceptación del experto y las exenciones de la base siguen separadas. Esta actualización prevalece sobre la exclusión histórica de 100 canastas indicada abajo. DI25-03 permanece parcial y no inicia DI25-04.

---

# Verificación documental externa — Boletín SRI NAC-COM-26-006

Fecha de revisión: 21-09-2026. Documento aportado por el titular: “BOLETÍN 006 - SRI HABILITA LA PROYECCIÓN DE GASTOS PERSONALES 2026 PARA REDUCIR EL IMPUESTO A LA RENTA.pdf”.

Se extrajeron e inspeccionaron visualmente sus dos páginas. La tabla de la primera página es imagen: se comprobó visualmente, no solo mediante extracción de texto.

## Procedencia comprobada

- Emisor y fecha impresos: Servicio de Rentas Internas; 6 de febrero de 2026.
- Tamaño del archivo aportado: 205.915 bytes.
- SHA256 del archivo aportado y de la descarga oficial: **82d0ac6abfd7602332c5bec223e580dfbdd195e322d4eedbcccb906b96692b44**.
- [Descarga oficial cotejada](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/ea002a89-17d8-4cdf-be42-affedbe3f8d8/BOLET%C3%8DN%20006%20-%20SRI%20HABILITA%20LA%20PROYECCI%C3%93N%20DE%20GASTOS%20PERSONALES%202026%20PARA%20REDUCIR%20EL%20IMPUESTO%20A%20LA%20RENTA.pdf).

La coincidencia de bytes prueba que se revisó el mismo archivo que publica esa URL; no equivale a firma de aprobación del experto sobre el software.

## Contraste con los ensayos

| Elemento | Documento externo | Implementación del ensayo |
|---|---|---|
| Canasta enero 2026 | USD 821,80 | Tope inicial 5.752,60 = 7 canastas |
| Rebaja | 18 % sobre el menor entre gastos y tope | Motor común usado por los ensayos |
| Cargas 0, 1, 2, 3, 4, 5 o más | 7, 9, 11, 14, 17, 20 canastas | Doce casos Continente/Galápagos |
| Ajuste insular | Factor 1,803 | Modifica el tope de gastos; la elegibilidad debe verificarse |
| Supuesto especial del titular o sus cargas | 100 canastas en las condiciones descritas | **No cubierto**: interfaz y guía excluyen esas condiciones; no aplicar un caso general |
| Validez de cargas y sustento de gastos | Condiciones y exclusión de doble registro | Entradas del ensayo; no comprobación documental automática |

Los topes ordinarios y el factor insular coinciden con la fuente. Los casos con USD 5.000 usan gastos ficticios suficientes para alcanzar el máximo; no afirman que todo trabajador tenga derecho al máximo.

## Alcance de esta verificación

El boletín permite contrastar gastos/cargas de 2026. No contiene la tabla general completa del impuesto, la tasa IESS, el detalle de la reliquidación por cambio de empleador ni toda la clasificación de ingresos exentos. Esos elementos tienen fuentes y supuestos separados en [la guía de ensayos](DI25-03_ENSAYOS_RENTA_DEMO.md).

La expresión “3 cargas o más” del texto previo se corrigió: existen topes distintos para 3, 4 y 5 o más. Tampoco se mezclan los antiguos topes de deducción mencionados para 2016 con esta rebaja de 2026.

**Resultado: verificación documental externa realizada para el alcance anterior.** No hay aprobación nominal del experto, validación de certificados personales ni homologación integral. DI25-03 sigue parcial. El supuesto de 100 canastas y las demás exenciones pendientes deben desarrollarse y revisarse antes de ampliar el alcance.
