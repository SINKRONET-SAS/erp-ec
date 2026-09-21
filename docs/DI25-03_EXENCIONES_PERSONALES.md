# Estado posterior al pronunciamiento técnico

Documento histórico de la versión 18.0.1.11.0 o anterior. El pronunciamiento devuelve DI25-03 para corrección y prevalece la respuesta en [Controles automáticos](DI25-03_CONTROLES_AUTOMATICOS.md). La referencia aislada ya no habilita sustitutos ni 100 canastas en la nómina operativa; los ensayos aritméticos permanecen separados. Las propuestas del borrador no constituyen decisiones aceptadas. DI25-03 sigue observado.

---

# DI25-03 · Exenciones personales de la base · 2026

Estado: implementado y ensayado en nómina mensual, anexo RDEP y ensayos de renta. No constituye aceptación del responsable tributario ni cierre de DI25-03. Es distinto del tope de 100 canastas de gastos personales (DI25-03_SUPUESTO_ESPECIAL_100_CANASTAS.md); ambos pueden coexistir.

## Constatación normativa

Revisión del 21-09-2026 sobre fuentes publicadas por el SRI.

- [LRTI, codificación con última reforma 01-04-2026](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/12c884d5-c8d9-4171-becc-1513b990b87a/LEY_DE_REGIMEN_TRIBUTARIO_INTERNO_LRTI.pdf), art. 9, numeral 12: están exentos los ingresos de personas mayores de sesenta y cinco años, por una fracción básica gravada con tarifa cero; los de personas con discapacidad debidamente calificadas, hasta el doble de esa fracción; el sustituto único acreditado puede beneficiarse hasta el mismo monto, en la proporción que fije el reglamento y si el titular no ejerce el derecho. Las exoneraciones de este numeral no se aplican simultáneamente: rige la más beneficiosa.
- [Extracto SRI: art. 9 num. 12, arts. 49 y 50 del Reglamento LRTI y art. 6 del Reglamento LOD](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/c766ad17-157b-47dd-a17d-cdd3ed3a3d54/Art.+49+y+50+Base+imponible+tercera+edad+y+personas+con+discapacidad.pdf): la exención se deduce del total de ingresos; el documento se entrega al empleador hasta el 15 de enero; el sustituto ejerce el beneficio en la proporción del titular y, si es reemplazado en el año, de forma proporcional al tiempo; un sustituto de varias personas aplica el beneficio por una sola. El art. 6 del Reglamento LOD limita el beneficio a discapacidad de 30 % o más y lo aplica proporcionalmente: 30-49 % → 60; 50-74 % → 70; 75-84 % → 80; 85-100 % → 100.
- [SRI, Impuesto a la Renta](https://www.sri.gob.ec/impuesto-renta): confirma una fracción para adultos mayores y dos para personas con discapacidad o sustitutos, con los porcentajes de la escala anterior.
- Fracción básica 2026: 12.208 ([tabla oficial SRI](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/58a7f4f6-ab51-48b6-b9ff-a8e97e1a28ef/Tablas%20de%20c%C3%A1lculo%20de%20Impuesto%20a%20la%20Renta.pdf)).

Se lee siempre del primer tramo de la política vigente; no hay una constante duplicada.

## Regla implementada

`erpec_payroll/engine.py` es la única implementación:

- Adulto mayor = 12.208. Titular con discapacidad = 2 × 12.208 × porcentaje de la escala. Sustituto = igual, × meses de ejercicio / 12.
- Se aplica la más beneficiosa, nunca la suma. El monto se limita a la base disponible (ingresos − IESS personal).
- La base gravable es base − exención. Después rigen la tarifa, la rebaja por gastos y, si corresponde, el tope de 100 canastas.
- La exención se reporta en `exoTerEd` (adulto mayor) o `exoDiscap` (discapacidad o sustituto); `basImp` es la base ya reducida.

## Acreditación y controles

Datos del empleado (solo referencias; no se registran diagnósticos ni copias de documentos), visibles solo para el responsable de nómina:

| Campo | Uso |
|---|---|
| Año de la acreditación | Debe coincidir con el año del cálculo; una acreditación vieja no se aplica. |
| Referencia del documento | Obligatoria. |
| Fecha de entrega | Hasta el 15 de enero. Una entrega posterior bloquea el anexo hasta criterio del responsable. |
| Meses como sustituto | Solo para el tipo 02. |
| Tope de gastos personales | General, 100 canastas titular o 100 canastas carga; exige documento del año y, para la carga, al menos una carga declarada. |

Sin acreditación vigente, la condición detectada por edad o discapacidad **no se aplica** y el agregador muestra un aviso; no se convierte en exención silenciosa. Si la acreditación existe pero es incompleta o cae en un caso no cubierto, no se aplica y el XML queda bloqueado con el motivo por empleado:

- discapacidad menor de 30 %, o tipo 00 (sin descripción en el esquema oficial), o acreditación sin condición registrada;
- sustituto sin identificar a la persona sustituida o con meses fuera de 1–12;
- entrega posterior al 15 de enero;
- persona que cumple 65 años durante el ejercicio: solo se cubre el año completo (65 cumplidos al 1 de enero).

## Ejemplos independientes

Base común de los ensayos 26–32: 30.000 − 2.835 = 27.165. Sin exención el impuesto sería 1.481,75.

| Caso demo | Cálculo a mano | IR anual |
|---|---|---:|
| 26 · Adulto mayor | 27.165 − 12.208 = 14.957; 2.749 × 5 % | 137,45 |
| 27 · Discapacidad 40 % | 24.416 × 60 % = 14.649,60; base 12.515,40; 307,40 × 5 % | 15,37 |
| 28 · Discapacidad 50 % | 24.416 × 70 % = 17.091,20; base 10.073,80 | 0,00 |
| 29 · Discapacidad 100 % | 24.416; base 2.749 | 0,00 |
| 30 · Sustituto 80 %, 6 meses | 24.416 × 80 % × 6/12 = 9.766,40; base 17.398,60; 167 + 1.849,60 × 10 % | 351,96 |
| 31 · Limitada por la base | Base 9.055 < 12.208: exención aplicada 9.055 | 0,00 |
| 32 · Discapacidad 100 % + 100 canastas | Base 29.914; 1.412 + 3.214 × 15 % = 1.894,10; rebaja 8.000 × 18 % = 1.440 | 454,10 |

Integración con la política sintética de pruebas (fracción 12.000, tarifa 10 %, IESS 10 %): sueldo 3.000 → retención mensual 170 sin exención; discapacidad 50 % acreditada 30; adulto mayor con discapacidad 40 % acreditada 50 (rige 14.400, no 26.400); sustituto 100 % por 6 meses 70; tope de 100 canastas con gastos 6.000: 80 frente a 95. RDEP con sueldo 40.000: adulto mayor `exoTerEd` 12.000, `basImp` 24.000, impuesto 1.200; discapacidad 50 % `exoDiscap` 16.800, `basImp` 19.200, impuesto 720.

## Exposición

- Áreas → Nómina → Ensayos tributarios de renta: sección «3 bis. Exención personal de la base», con los casos 26–32.
- Empleado → pestaña «Anexo RDEP»: grupos «Acreditación de exención personal» y «Tope de gastos personales».
- Agregador RDEP: columnas y conciliación con tipo y monto de exención aplicados; avisos y bloqueos en «Revisión pendiente».

## Límites que permanecen

- No se valida la calificación por la autoridad sanitaria, el parentesco, la sustitución ante la autoridad de inclusión ni la conexión del SRI con esas bases.
- No hay reliquidación retroactiva de retenciones mensuales por entregas tardías ni por cambios de condición dentro del año.
- Un mismo sustituto de varias personas y un reemplazo de sustituto dentro del año se representan solo con un caso y sus meses; los demás requieren criterio del responsable.
- La edad se toma por año de nacimiento y fecha de cumpleaños al 1 de enero; el texto legal dice «mayores de sesenta y cinco años». Este criterio es una decisión de implementación que el responsable debe confirmar.
- El tipo 03 del esquema (carga con discapacidad) no genera exención de la base; solo el tope de 100 canastas si se declara y acredita.
- No se toca ningún resultado de períodos contabilizados: el cambio solo afecta cálculos posteriores y la agregación anual.

## Compatibilidad y reversión

Versión 18.0.1.11.0 del módulo. Campos aditivos con valores por defecto (sin exención, tope general). Sin datos de acreditación el comportamiento coincide con el anterior; los resultados de períodos ya cerrados no se recalculan. El resultado mensual añade la clave `personal_exemption`. Antes de instalar en una instancia con datos: respaldar base y filestore, y comparar las huellas de asientos y resultados antes y después. Volver a la versión anterior en copia aislada; las columnas nuevas pueden permanecer inactivas. No se acredita una restauración por el mero respaldo.
