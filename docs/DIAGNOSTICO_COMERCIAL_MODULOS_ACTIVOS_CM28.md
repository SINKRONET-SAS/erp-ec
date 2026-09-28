# Diagnóstico CM28

Inspección de código y configuración real; no acredita correcciones. Gobierno inicial válido: 172 eslabones. Reproducción aislada ejecutada: 0 fallos y 0 errores; evidencia CM28-00-cierre.json.

- **CM28-01 (P1)** Dos clientes comparten compañía operadora y colisionan al activar contratos. Fuente: `addons/erpec_selfservice/models.py; addons/erpec_suite/models/commercial.py`. Estado: reproducido en base aislada.
- **CM28-02 (P1)** Aprovisionamiento único por compañía operadora. Fuente: `addons/erpec_provision/models/provision.py`. Estado: confirmado en código.
- **CM28-03 (P1)** Instalación fija sin módulos contratados ni aplicación de cuota de usuarios. Fuente: `scripts/provision-worker.py`. Estado: confirmado en código.
- **CM28-04 (P1)** Solicitud no deriva estados de pago e instancia. Fuente: `addons/erpec_selfservice/models.py`. Estado: reproducido en base aislada.
- **CM28-05 (P2)** Portada sin instalar y SS-DEMO publicado en fundador. Fuente: `consulta de solo lectura en erpec_fundador del diagnóstico previo`. Estado: confirmado en instancia.
- **CM28-06 (P1)** Sin capacidades internas, complementos, anualidad ni precio por usuario. Fuente: `addons/erpec_suite/models/commercial.py`. Estado: confirmado en código.
- **CM28-07 (P1)** Sin activos fijos propios ni en Community local. Fuente: `inventario de addons propios y upstream`. Estado: confirmado por inventario.
- **CM28-08 (P1)** Sin ciclo completo de renovación y entrega de acceso personal. Fuente: `addons/erpec_selfservice; scripts/provision-worker.py`. Estado: confirmado en código.

El diagnóstico visual y los ensayos de aislamiento/concurrencia se registrarán por separado. Nunca atribuir validación funcional al documento del plan.

## Respuesta comprobada tras CM28-F

Se conserva arriba el diagnóstico inicial. Los resultados siguientes provienen de ejecución y evidencias, no del plan.

| Hallazgo | Respuesta | Evidencia en docs/evidencias/CM28 |
|---|---|---|
| CM28-01 | Identidad persistente erpec.customer y contratos por cliente, independiente del operador. | CM28-A-cierre.json; regression.json |
| CM28-02 | Instancia única por cliente; compatibilidad con registros históricos sin cliente. | MIGRACION_IDENTIDAD.md; worker-isolation.json |
| CM28-03 | Lista técnica única, instalación por contratación y derechos/cuotas comprobados en servidor y RPC. | CM28-D-cierre.json; worker-isolation.json; regression.json |
| CM28-04 | Estado calculado desde pago y aprovisionamiento; reintentos en las colas existentes. | CM28-D-cierre.json; regression.json |
| CM28-05 | Landing instalada en fundador y demo; SS-DEMO retirado sin borrar contratos; tarifas reales sin publicar. | ui-results.json; local-verification.json |
| CM28-06 | Planes/versiones con incluidos, complementos y usuarios adicionales mensuales/anuales; importes en servidor. | CM28-B-cierre.json; regression.json |
| CM28-07 | erpec_assets propio con compra parcial, depreciación, asientos, reversión y cambios futuros de estimación. | CM28-C-cierre.json; regression.json |
| CM28-08 | Renovación por nuevo pago y misma instancia; activación personal de un uso con caducidad. | CM28-D-cierre.json; worker-isolation.json; regression.json |

La cantidad de usuarios internos activos es una variable comercial y un límite efectivo. El administrador humano cuenta; portal, público y la cuenta técnica protegida no. Se probó la carrera por el último cupo. Fabricación requiere Inventario contratado.

Acceso original: la captura inicial correspondía al piloto 8169, mientras fundador usa 8199 y su usuario fundador. El acceso se verificó con la credencial existente, sin restablecerla. La captura posterior de Aplicaciones ya muestra una sesión de fundador; ese catálogo técnico de Odoo no sustituye ERP EC → Planes y versiones.

Validación: 701 pruebas integradas; las tres omisiones se cubrieron en copia de demo (25 pruebas sin omisiones); 50 pruebas del último ajuste comercial. Restauración ensayada antes de actualizar; fundador, demo y pilotos sin desfase. Sin pagos reales, emisión fiscal real, correo real ni despliegue productivo. Las tarifas comerciales y el tratamiento tributario requieren configuración del responsable antes de publicar.
