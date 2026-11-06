# Plan Haiky DI06: diagnóstico integral y respuesta

Fecha: 06-11-2026. Autorización: solicitud del titular para diagnosticar, corregir, ejecutar fases, verificar, commit y push. Alcance exclusivo de ERP/_EC; no modificar repositorios fuente ni operar pagos o declaraciones reales.

## Secuencia y condiciones

| Fase | Dependencia | Ejecución y aceptación |
|---|---|---|
| DI06-00 | Gobierno inicial válido | Revisar código, fuentes oficiales, capacidades y límites; publicar diagnóstico, matriz y prompts; sellar evidencia documental |
| DI06-A | 00 sellada | Reproducir y corregir defectos acotados; pruebas de cálculo, conservación de API y exposición en las pantallas existentes; registrar límites de validación |
| DI06-B | A sellada | Ejecutar regresión integrada, esquema, XML, codificación y gobierno; verificar recorridos en base aislada; registrar bloqueo si PostgreSQL no es accesible; no cerrar aceptación funcional sin ejecución |
| DI06-C | B ejecutada o bloqueo registrado | Revisar diff y secretos, commit/push de correcciones y diagnóstico; publicar estado parcial si B está bloqueada; verificar remoto por SHA cuando exista acceso |

La autorización cubre toda la secuencia. La publicación de trabajo parcial no acredita aceptación funcional ni cierre de las fases maestras 04-08. Los resultados anteriores no cuentan como pruebas nuevas.

## Respuesta por hallazgo

Ver [diagnóstico](DIAGNOSTICO_INTEGRAL_DI06.md). Prioridad inmediata: DI06-01 (regresión de años bisiestos), DI06-02 (referencia legal) y DI06-03 (creación de lotes por fuera del flujo). No cambiar porcentajes laborales por inferencia ni activar producción.

Las ampliaciones DI06-04 a DI06-11 requieren diseño y ensayo integral en base aislada: historial de remuneraciones y beneficios, contabilización del finiquito, estados financieros, conciliación tributaria, depreciación fiscal, controles de costos y aceptación bancaria. No se sustituyen con documentos ni con pantallas vacías. Permanecen abiertas hasta disponer de evidencia funcional y, donde corresponda, criterio legal o aceptación externa.

## Puertas de cierre pendientes

1. Infraestructura: permitir acceso del ejecutor a PostgreSQL local 127.0.0.1:55487. El intento de esta sesión devuelve Windows 10013 (permiso denegado), no un resultado de pruebas.
2. Desarrollo/QA: ejecutar `scripts/test-integrated.py` y casos nuevos en base desechable, sin modificar fundador/demo; comprobar vistas, seguridad multiempresa, duplicados, cierres y reversión.
3. Responsable contable: aprobar mapeos y amarre mayor/auxiliares/estados, clasificación de diferencias permanentes y temporarias, régimen NIIF aplicable y casos de importación.
4. Responsable laboral: validar aplicabilidad del criterio PGE, remuneración variable, beneficios históricos, vacaciones e indemnizaciones especiales.
5. Responsable fiscal/tesorería: aceptación SRI y bancos con expedientes y acuses; un XML o TXT generado no prueba autorización o pago.

## Reversión

Los cambios acotados no migran datos ni recalculan actas emitidas. Revertir el commit de implementación y reinstalar la versión anterior en copia aislada antes de cualquier retorno operativo. Los locks históricos se conservan; registrar un nuevo eslabón para una reversión, nunca reescribir evidencia antigua. Antes de desplegar: respaldo, restauración de ensayo y actualización del módulo con verificación de versiones.

## Segunda pasada autorizada — 06-11-2026

Se retoman A (revision de omisiones), B (regresion) y C (publicacion). Hallazgo DI06-13: la huella del finiquito anterior solo cubria entradas, permitiendo aprobar resultados de una version anterior del motor. Respuesta: sellar entradas, parametros y resultado; recalcular la huella al aprobar, comparar el resultado almacenado y volver a exigir politica activa DEMO. Las actas emitidas permanecen intactas; las calculadas con huella antigua requieren recalculo explicito. Aceptacion local mediante pruebas puras; casos ORM de huella antigua, resultado alterado y cambio de empresa DEMO pendientes del entorno. No sustituye DI06-04 a DI06-12.

## Avance de regresion confirmado

06-11-2026: 738 pruebas reportadas en la suite integral, cero fallos/errores y tres omisiones de saneamiento. Estas condiciones se cubren mediante copia sembrada de tesoreria con 25 pruebas y cero omisiones, segun salida del ejecutor aportada por el titular. Los casos ORM de las correcciones ya se ejecutaron. Quedan recorrido visual, despliegue y ampliaciones; esta evidencia no cierra cumplimiento integral. Ver evidencias/DI06/segunda/regresion-integral.json.
