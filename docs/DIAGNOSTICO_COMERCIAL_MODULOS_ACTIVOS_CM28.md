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
