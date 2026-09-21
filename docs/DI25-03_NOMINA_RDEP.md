# DI25-03 — Nómina, correcciones y RDEP

Estado: implementación local parcial. DI25-03.3 requiere un oráculo de negocio aprobado y responsable tributario identificado. No iniciar DI25-04–07 sin ese cierre o cambio explícito de dependencias.

## Reproducción y corrección

La suite previa del módulo reportó 79 pruebas, 3 fallos, 0 errores, salida 1, en la base aislada ec_integrated_test_65d01857b0dd. Los fallos intencionales reprodujeron:

- Año salarial variable creado fuera de orden: el agregador copiaba la proyección del último registro. Con parámetros sintéticos y 11 salarios de 1000 más uno de 3000, el resultado obtenido fue 0 frente a 60 esperado.
- Corrección de nómina: desaparecía un beneficio de 125.
- Reversión de préstamo: el saldo seguía en 150 cuando debía volver a 250.

El consolidado aplica ahora la misma función de tarifa del motor a los acumulados efectivos. No copia proyecciones mensuales ni modifica retenciones contabilizadas. Compara impuesto anual después de rebaja con retenciones acumuladas; la diferencia es informativa y puede ser negativa. Los gastos efectivos declarados por categoría se distinguen de la proyección mensual. Los beneficios gravados ya incluidos en el resultado se incorporan al desglose del XML.

Una corrección copia importe, tipo y nota de cada beneficio; exige aprobar de nuevo las novedades. Cambiar el tratamiento de un tipo utilizado en un cálculo queda bloqueado: debe crearse otra versión. Las cuotas de períodos revertidos permanecen como historia, excluidas del saldo. Repetir reversión, corrección o cálculo no duplica sus efectos.

## Oráculos y límites

El caso aritmético sintético se calcula sin llamar al motor: ingresos 14000, IESS 1400, base 12600; exceso de 600 al 10 % = 60. Es una prueba de agregación, no una tabla legal.

Caso independiente con tabla 2026: base 12677; (12677 − 12208) × 5 % = 23,45. Con gastos efectivos de 100 y tasa de rebaja del 18 %, rebaja 18 y resultado 5,45. Fuentes consultadas el 21-09-2026 UTC:

- [Tabla oficial SRI de renta, 2026 y anteriores](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/58a7f4f6-ab51-48b6-b9ff-a8e97e1a28ef/Tablas%20de%20c%C3%A1lculo%20de%20Impuesto%20a%20la%20Renta.pdf): fracción 12208–15549 y tarifa 5 %.
- [Base imponible y exenciones, SRI](https://www.sri.gob.ec/impuesto-renta): distingue aportes del trabajador, tercera edad y discapacidad. Las fórmulas heredadas de dos/tres fracciones no se aceptan como vigentes; se bloquea su uso hasta revisión.
- [Anexos y guías oficiales](https://www.sri.gob.ec/formularios-e-instructivos1): referencia para validar separadamente esquema y contenido.
- [Actualización de gastos personales 2026, SRI](https://www.sri.gob.ec/detalle-noticias?idnoticia=1324&marquesina=1): la reliquidación de retenciones mensuales sigue pendiente; esta corrección del consolidado no la sustituye.

No hay aprobación del responsable tributario. No están resueltos integralmente otros empleadores, exenciones, rentas especiales/impuesto asumido, Galápagos, convenios/residencia extranjera, ausencias y bases diferenciadas de IESS/IR/beneficios. El XML se bloquea ante indicadores detectables de esos regímenes y ante varias políticas en el año. Nómina continúa restringida por el control preexistente a empresa DEMO sin RUC y empleados sintéticos. No se amplía a operaciones reales.

Doce períodos no prueban por sí solos integridad anual. Los valores de novedades anuales deben capturarse una sola vez como flujos; la validación de acumulados importados y de cobertura completa requiere el oráculo pendiente. Décimos mensualizados, reserva pagada y bases diferenciadas conservan limitaciones previas; no se declara aceptación del RDEP completo.

## Compatibilidad y exposición

Se conservan nombres y respuestas públicas de calculate, action_correct, action_reverse y action_generate_xml. Los consumidores revisados son nómina, RDEP, reportes y Tesorería. annual_income_tax extrae la tarifa común sin crear otra autoridad de cálculo. No se alteran contratos externos.

La ficha del agregador muestra política, método, acumulados, impuesto, retenciones, diferencia y revisión pendiente. El XML se invalida al reagrupar. Una huella de períodos, resultados, novedades y empleado impide generarlo si cambió su origen; los agregadores anteriores requieren reagruparse. Las descargas históricas conservan su condición de vista previa, no de declaración.

El préstamo muestra el estado del período junto a cada cuota y explica su efecto en el saldo. La prueba de esquema se mantiene separada de las expectativas económicas. Ver capturas y evidencia de esta fase para el recorrido realmente verificado.

## Migración y reversión

Versión del módulo 18.0.1.8.0. Campos del RDEP aditivos; no se reescriben resultados de períodos, asientos, cuotas ni XML histórico. Al actualizar se recalculan solamente balance/settled de anticipos. Antes de actualizar una instancia con datos, detener operaciones, respaldar base y filestore y exportar la vista previa privada de saldos.

En Odoo shell con el mismo alcance de empresa, cargar el helper balance_migration de esta versión en una copia aislada:

```python
from odoo.addons.erpec_payroll.balance_migration import preview, apply
snapshot = preview(env)  # exportar JSON fuera de Git antes de actualizar
apply(env, snapshot)    # recálculo de columnas derivadas
# Solo durante vuelta controlada a versión anterior y sin operaciones nuevas:
apply(env, snapshot, restore=True)
```

El helper valida base, acceso, registros y huella de cuotas/estados; rechaza una reversión si cambiaron. Guardar el JSON con UTF-8 sin BOM en almacenamiento privado y conservarlo con el respaldo. La vuelta de código a 35e8346 se realiza en checkout aislado; no operar con la versión antigua ni mezclar su saldo con cálculos nuevos. Una reversión real de nómina requiere compensación contable, nunca restaurar una base sobre operaciones posteriores.

Ensayos de esta pasada se hacen en bases nuevas y en una instancia UI ficticia, respaldada antes de instalar nómina. No se migra ni modifica la demo del usuario.
