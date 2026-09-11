# Tesorería local: nómina y proveedores

En la demo, abre **Inicio → Tesorería**.

- **Saldos de proveedores**: facturas y notas de crédito publicadas con saldo. La lista distingue el tipo de documento; aplica créditos y anticipos antes de decidir cuánto pagar. No sumar una nota de crédito como una factura adicional.
- **Pagos y anticipos**: consulta o registra pagos y anticipos con las funciones contables nativas. Incluye pagos cuyo tercero contable se clasifica como proveedor; los pagos de nómina se identifican por su referencia.
- **Conciliar movimientos**: relaciona un movimiento de extracto con un pago registrado de la misma empresa, banco, moneda, beneficiario, sentido e importe. Un pago parcial se coteja con su propio movimiento.
- **Personas y nómina → Pagos por empleado**: muestra el neto y saldo de la preparación por empleado. La demo incluye un empleado liquidado y otro con saldo de 624,40; el registro de pago usa el diario Banco de ensayo DEMO.

Registrar un pago no transfiere fondos. La exportación bancaria aún no está habilitada: se debe validar cada perfil de banco y servicio para nómina y proveedores. Véase VALIDACION_ARCHIVOS_BANCARIOS.md. No hay conexión bancaria externa en estos ensayos.

## Evidencia y alcance

Catorce pruebas automatizadas de compras y Tesorería en copia aislada: permisos, pagos parciales, nota de crédito, anticipo, conciliación exacta, reversión y repetición. Las operaciones de ensayo son ficticias. La semilla salarial utiliza la política real de 2026; esto no acredita equivalencia laboral integral.

El saneamiento compensó los dos documentos iniciales identificados y sus retenciones artificiales, conservando sus líneas originales. Los sustitutos suman 230 y 575 con IVA 15 %. No se auditó por esta vía cada operación histórica de la demo ni se emitieron comprobantes SRI.

Instalación con respaldo de base, archivos y módulos. Recuperación verificada del respaldo closeout-install-20260911-160059 en una base independiente: módulos/archivos coincidentes, dos empleados y saldos, documentos saneados. Ese respaldo precede a los accesos de proveedores y no acredita su recuperación.

La evidencia actualizada se conserva en evidencias/ERPEC26-TESORERIA-LOCAL.json. No declarar SP02 ni la puerta comercial cerrados: faltan homologación bancaria, emisión fiscal completa, equivalencia laboral y aceptación integral por perfiles.
