# Actualización: supuesto especial de 100 canastas

Referencia normativa constatada y corregida para 2026. Ver docs/DI25-03_SUPUESTO_ESPECIAL_100_CANASTAS.md. Seis ejemplos nuevos (20–25) instalados y verificados en demo: 25 casos en total. Windows/Linux: 459 pruebas sin fallos/errores; Windows 5 omisiones. Evidencia: docs/evidencias/DI25/DI25-03-100-canastas.json. El pendiente de base normativa queda resuelto; la aceptación del experto y las exenciones de la base siguen separadas. Esta actualización prevalece sobre la exclusión histórica de 100 canastas indicada abajo. DI25-03 permanece parcial y no inicia DI25-04.

---

# Estado actualizado: demo y contraste externo verificados

Verificación del 21-09-2026: 19 casos instalados y visibles en Áreas → Nómina → Ensayos tributarios de renta. Edición, persistencia, rechazo de IESS inválido y restablecimiento comprobados en pantalla. Suite del motor: 457 pruebas Windows y 457 Linux, sin fallos ni errores; Windows reporta 5 omisiones de entorno. Ajustes posteriores solo de presentación XML verificados en demo; CI final 0623125 aprobado: 457 pruebas Linux sin fallos/errores, perfiles customer/controller, gobierno y dependencias aprobados. Boletín SRI aportado cotejado byte a byte con la descarga oficial: ver docs/DI25-03_VERIFICACION_BOLETIN_SRI.md. Esto acredita contraste documental y ensayos, no aceptación nominal del experto. DI25-03 permanece parcial; no iniciar DI25-04.

Evidencia: docs/evidencias/DI25/DI25-03-ensayos-renta.json. Esta actualización prevalece sobre los estados históricos inferiores.

---

# Ensayos visibles de renta con otro empleador — DI25-03.3

Solicitud del titular: preparar pruebas editables en la demo para revisión del experto tributario. Se mantiene DI25-03 parcial; esta herramienta no registra por sí misma aceptación externa.

## Acceso y uso

En la demo local: **Áreas → Nómina → Ensayos tributarios de renta**.

1. Abrir **02 · Ingreso anterior de USD 6.000**.
2. Revisar la política 2026 y los totales anuales del empleador actual.
3. Modificar **Ingreso gravado · otro empleador**, su **IESS personal** y, si corresponde, el **IR retenido**. Salir del campo para actualizar el resultado; guardar para conservar los cambios.
4. Contrastar base, impuesto de tabla, rebaja e impuesto anual. La comparación muestra también el IR sin otro empleador y cuánto aumenta al incorporarlo.
5. Registrar entradas probadas, resultado independiente y conclusión en **Observaciones del experto**. Estas observaciones no activan una homologación.
6. Para repetir un caso, seleccionar la referencia y pulsar **Restablecer caso de referencia**; la confirmación avisa que reemplaza importes y conserva observaciones.

La siembra crea diecinueve casos por empresa y conserva cualquier edición en ejecuciones posteriores. No carga datos personales reales ni modifica períodos, asientos o XML RDEP.

## Magnitudes y supuestos

- Año 2026; persona ficticia en régimen general, sin exenciones personales especiales. La región modifica solo el tope de gastos del ensayo.
- Empleador actual: total anual proyectado gravado; el IESS es aporte personal a cargo del trabajador. Las retenciones son las ya realizadas.
- Otro empleador: acumulados del comprobante anterior del mismo año. Se incorporan **una sola vez**; no se multiplican por doce ni se copian en cada mes.
- Gastos personales: total anual para la rebaja, no deducción de la base. Se aplica el tope según cargas de la política.
- Base imponible = ingresos gravados de ambos empleadores − IESS personal de ambos.
- IR anual después de rebaja = máximo entre cero e impuesto de tabla menos rebaja.
- Saldo pendiente = máximo entre cero e IR anual menos retenciones de ambos empleadores.
- Las retenciones superiores al IR se muestran por separado; no se genera devolución ni retención negativa.
- Cuotas orientativas: saldo dividido entre meses pendientes, redondeando hacia abajo a centavos en los meses previos al último; la última absorbe el resto. Con un mes se toma únicamente la última cuota. Es un reparto para discusión, no la reliquidación automática de la nómina.
- No cubre simultaneidad de empleadores, exenciones personales, enfermedades catastróficas, convenios, impuesto asumido por empleador ni otros regímenes. Galápagos tiene contraste aritmético del tope, pendiente de verificar elegibilidad.

## Referencias aritméticas independientes

Comunes: empleador actual 18.000; IESS personal 1.701; IR retenido 50; gastos personales 1.000; cero cargas; tres meses pendientes. Rebaja: 1.000 × 18 % = 180.

| Caso | Ingreso anterior | IESS anterior | IR anterior | Base | IR causado | IR después de rebaja | Saldo |
|---|---:|---:|---:|---:|---:|---:|---:|
| 01 | 0 | 0 | 0 | 16.299 | 242,00 | 62,00 | 12,00 |
| 02 | 6.000 | 567 | 150 | 21.732 | 816,28 | 636,28 | 436,28 |
| 03 | 10.000 | 945 | 150 | 25.354 | 1.250,92 | 1.070,92 | 870,92 |

Caso 01: 167 + (16.299 − 15.549) × 10 % = 242.
Caso 02: 631 + (21.732 − 20.188) × 12 % = 816,28.
Caso 03: 631 + (25.354 − 20.188) × 12 % = 1.250,92.

En el caso 02, cuotas de 145,42; 145,42; 145,44 suman 436,28. En el caso 03, 290,30; 290,30; 290,32 suman 870,92.

Prueba de crédito: en el caso 02, cambiar únicamente IR retenido por otro empleador a 1.000 conserva base 21.732 e IR anual 636,28; saldo cero y retenciones superiores por 413,72. No es un derecho automático de devolución.

Prueba inválida: un IESS anterior mayor que el ingreso anterior, un importe negativo o meses fuera de 1–12 deben impedir guardar. Durante edición se muestra el motivo y se oculta el resultado.

La coincidencia de referencia compara constantes aritméticas contra el motor compartido. Si cambian entradas o parámetros tributarios, la UI deja de indicar coincidencia con ese caso de referencia.

## Fuentes y aceptación externa

Consultadas el 21-09-2026:

- [SRI: base imponible de ingresos del trabajo](https://www.sri.gob.ec/impuesto-renta): ingreso gravado menos aporte personal, con la excepción del aporte pagado por el empleador.
- [SRI: tabla del impuesto a la renta 2026](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/58a7f4f6-ab51-48b6-b9ff-a8e97e1a28ef/Tablas%20de%20c%C3%A1lculo%20de%20Impuesto%20a%20la%20Renta.pdf).
- [SRI: rebaja por gastos personales 2026](https://www.sri.gob.ec/detalle-noticias?idnoticia=1261&marquesina=1).
- [Reglamento publicado por SRI, art. 96, página 99 del PDF](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/ee775a90-0ba9-48fe-85cb-9a52673c4c61/REGLAMENTO_PARA_APLICACION_LEY_DE_REGIMEN_TRIBUTARIO_INTERNO_LRTI.pdf): uso del comprobante previo al reiniciar con otro empleador. Verificar con el responsable la versión consolidada aplicable y el caso concreto.

La fórmula del ensayo es una implementación para contraste bajo los supuestos declarados. El responsable debe revisar comprobantes, período, base aplicable, gastos, cargas y mecanismo de ajuste antes de aceptar. Registrar identidad, fecha, entradas y política exactas, referencia independiente, diferencias y alcance aceptado en la matriz DI25-03. No se levanta el bloqueo existente de XML RDEP para otros empleadores.

## Compatibilidad, datos y reversión

Se añade un modelo de ensayo con permiso de responsable de nómina y regla por empresa. Reutiliza annual_income_tax; no cambia el contrato del motor de nómina ni la agregación RDEP. Los resultados se recalculan desde las entradas; no hay estados de aprobación paralelos.

La actualización instala erpec_payroll 18.0.1.9.0 y crea los casos mediante scripts/seed-tax-review-demo.py, ejecutado en Odoo shell dentro de la demo. El script exige empresa DEMO sin RUC y política sintética 2026. Repetirlo conserva las ediciones existentes.

Antes de actualizar: detener únicamente la instancia demo identificada por su configuración, respaldar base, filestore y copia anterior del módulo. Conservar el respaldo privado fuera de Git. Comprobar las huellas de asientos, apuntes y períodos/líneas de nómina antes/después; no restaurar sobre actividad posterior sin revisar sus efectos.

Reversión del incremento: retirar el acceso nuevo y volver a la copia anterior del módulo en una copia aislada; las tablas nuevas pueden conservarse inactivas. Para restauración completa, reconstruir una instancia aislada con el respaldo de base/filestore/módulo, verificarla y acordar el corte. No usar restauración como anulación fiscal ni sobrescribir la demo activa automáticamente. No se atribuye una restauración ensayada al mero respaldo.

## Ampliación solicitada: casos de la matriz y sueldo de USD 5.000

Se preparan 19 casos: tres de otro empleador; cambio salarial; ausencia con remuneración reducida; doce combinaciones de región/cargas para USD 5.000 mensuales; décimos/reserva separados; cierre anual del impuesto.

Los casos 04 y 05 parten de acumulados ya determinados. Sirven para contrastar el efecto anual del cambio salarial o ausencia, pero no certifican todavía el cálculo laboral de días, descuentos ni bases diferenciadas. El caso 19 concilia impuesto y retenciones, sin cerrar la validación integral del RDEP.

El ejemplo de USD 5.000 usa ingreso anual 60.000 y aporte personal supuesto 9,45 % = 5.670. Base 54.330; impuesto causado = 4.965 + (54.330 − 46.575) × 25 % = 6.903,75. No se aplica automáticamente 9,45 % a cualquier régimen: los aportes se ingresan por separado.

| Cargas | Canastas | IR anual continental con rebaja máxima | IR anual Galápagos con rebaja máxima |
|---|---:|---:|---:|
| 0 | 7 | 5.868,28 | 5.036,80 |
| 1 | 9 | 5.572,43 | 4.503,39 |
| 2 | 11 | 5.276,59 | 3.969,97 |
| 3 | 14 | 4.832,81 | 3.169,85 |
| 4 | 17 | 4.389,04 | 2.369,73 |
| 5 o más | 20 | 3.945,27 | 1.569,61 |

Los casos cargan gastos ficticios de 30.000 para alcanzar los topes. La rebaja máxima no corresponde automáticamente por recibir ese sueldo: requiere gastos sustentados y cargas válidas. La cuota mensual es orientativa y depende de retenciones previas y meses restantes; el ensayo ajusta los centavos en la última cuota.

La tabla general de IR es común; Galápagos ajusta el tope de gastos por 1,803 en este ensayo. No se trasladan a 2026 los antiguos topes de deducción del 50 %, 1,3 o 0,325 mencionados para 2016. La elegibilidad insular queda por verificar, no se presume de una selección de pantalla.

Los décimos y el fondo de reserva se ingresan aparte para comprobar que no se sumen al ingreso gravado únicamente por estar mensualizados. El caso 18 informa 10.482 de esos conceptos: el total informado asciende a 70.482, mientras la base de IR permanece en 54.330. No calcula su devengo ni completa su mapeo RDEP.

Fuentes adicionales: [Boletín SRI NAC-COM-26-006](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/ea002a89-17d8-4cdf-be42-affedbe3f8d8/BOLET%C3%8DN%20006%20-%20SRI%20HABILITA%20LA%20PROYECCI%C3%93N%20DE%20GASTOS%20PERSONALES%202026%20PARA%20REDUCIR%20EL%20IMPUESTO%20A%20LA%20RENTA.pdf); [LRTI publicada por SRI, art. 9: décimos exentos](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/ba4df78b-a7ad-47b0-b667-c99632913bf3/3.%20LEY%20DEL%20REGIMEN%20TRIBUTARIO%20INTERNO.pdf); [guía SRI: rentas exentas, incluyendo fondos de reserva](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/60488d6c-fb96-4ef7-b86d-645d1a21f814/Gu%C3%ADa%20Impuesto%20a%20la%20Renta%202019.pdf). La última guía es histórica y se usa solo como referencia de clasificación, no como tabla ni régimen de gastos 2026.
