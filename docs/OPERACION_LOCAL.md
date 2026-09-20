# Operación local y verificación (ERP EC)

Herramientas para mantener las instancias locales y comprobar que todo funciona junto. Todo se ejecuta desde la raíz del repositorio.

## Servicios: supervisor
`scripts/supervisor-windows.py` mantiene PostgreSQL y las cuatro instancias (Fundador 8199, demo 8369, pilotos A 8169 y B 8170). Cada 30 s comprueba el login HTTP; si una instancia cae, o no responde 3 veces seguidas, la reinicia. Solo toca los procesos cuyo `odoo.conf` es el de una instancia suya.

| Acción | Comando |
|---|---|
| Ver estado | `.venv\Scripts\python.exe scripts\supervisor-windows.py --status` |
| Revisar y reparar una vez | `... --once` |
| Instalar al iniciar sesión | `powershell -ExecutionPolicy Bypass -File scripts\install-supervisor.ps1` |
| Quitar | `powershell -ExecutionPolicy Bypass -File scripts\install-supervisor.ps1 -Remove` |

El registro queda en `.cache/windows/supervisor.log`. **Para actualizar módulos de una instancia**, ejecutar `-u ... --stop-after-init` en otro proceso y luego terminar el servidor: el supervisor lo levanta con el registro nuevo. Para detenerlo a propósito, quitar primero la tarea o detener el supervisor.

## Suite integrada (todos los módulos juntos)
Cada módulo se probaba aislado, y un defecto de combinación (nómina bloqueando notas de crédito) pasó inadvertido. Antes de cerrar una fase:

- Windows: `python scripts/test-integrated.py` (crea una base nueva y aislada, instala los 22 `erpec_*`, ejecuta todas las pruebas y la elimina). Admite módulos concretos: `python scripts/test-integrated.py erpec_fiscal_sri`.
- Linux (mismo Python y lock que producción): `bash deployment/linux/run-tests.sh`. Requiere Docker.
- Las 5 pruebas de sanitización de `erpec_treasury` necesitan la demo sembrada; se omiten en una base limpia y se ejecutan sobre una copia de la base de la demo (dump/restore a otra base y `-u erpec_treasury --test-tags /erpec_treasury`).
- GitHub Actions (`.github/workflows/tests.yml`) ejecuta la suite Linux y `pip-audit` sobre `deployment/linux/requirements-linux.lock` en cada push.

## Dependencias
Los locks `requirements-windows.txt` y `deployment/linux/requirements-linux.lock` mandan sobre los pines de Odoo (que siguen una distribución de referencia ya desactualizada). En Linux, `deployment/linux/prepare_requirements.py` combina ambos al construir la imagen. Para revisar vulnerabilidades: `pip-audit -r deployment/linux/requirements-linux.lock --no-deps --disable-pip`. Cualquier actualización se valida con la suite integrada en Windows y en Linux, y con una consulta real al SRI, antes de adoptarla.

## Limpieza de artefactos de prueba
- `scripts/purge-backups.py` (respaldos anteriores al cifrado) y `scripts/purge-test-databases.py` (bases y roles de PostgreSQL de ensayos, y sus carpetas). Ambos muestran primero lo que borrarían y solo actúan con `--ejecutar`. Nunca tocan las cuatro instancias reales ni los `claves-*` ni los `punto-restauracion-*`.

## Puntos de emisión permitidos por usuario
En la ficha del usuario (Administración > Usuarios > Facturación electrónica), `Puntos de emisión permitidos`. Vacío = sin restricción. Con puntos indicados, el usuario solo puede contabilizar y emitir comprobantes de venta de esos puntos; no puede ampliarlos él mismo.
