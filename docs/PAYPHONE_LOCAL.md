# PayPhone: incremento local ERPEC26-04

## Estado y alcance

Continuación solicitada el 10 de septiembre de 2026. La instrucción vigente del usuario es validar localmente antes de desplegar o contratar recursos en Render. Aplicación SK_ERP creada en PayPhone en modo Prueba, probador aceptado y subdominio conectado por Cloudflare Tunnel. Estos pasos se observaron en la sesión; no acreditan una transacción externa completada.

El módulo propio `erpec_payphone` amplía la fase 04. La fase sigue abierta y el AuditLock de la fase 03 permanece intacto. No se han ejecutado las fases 05–08 ni se ha declarado compatible con Render el trabajador Windows.

## Acceso

- Operador: http://127.0.0.1:8169 (piloto A). Piloto B: http://127.0.0.1:8170.
- Acceso de pruebas: https://pruebas.sinkronet.com.ec.
- Retorno registrado: https://pruebas.sinkronet.com.ec/payment/payphone/return.
- Menús ERP EC: **Configurar PayPhone** y **Pagos de prueba**, solo para administración.

En Configurar PayPhone introducir Token y StoreID directamente en Odoo y confirmar que la aplicación está en Prueba en el panel de PayPhone. No introducir secretos en Git, tickets o capturas. El Token se conserva en la base local, con campo protegido por permisos de administración y entrada oculta en el formulario; no se afirma cifrado adicional en reposo. Los respaldos de esta base también requieren protección. El modo de PayPhone depende de la aplicación externa: la casilla local registra la comprobación del operador, no cambia ni verifica automáticamente el ambiente remoto.

Existe un contrato y pago en borrador de ensayo por USD 1 sin impuesto, exclusivamente sintético; no es una tarifa comercial ni una determinación tributaria. Puede revisarse antes del envío. No se realiza un cargo por instalar el módulo ni por guardar credenciales.

## Flujo

1. Guardar la configuración privada en la organización operadora.
2. Abrir el pago en borrador y revisar importe y contrato. Se admiten solo ensayos USD de 0,01 a 100.
3. Pulsar **Preparar pago de prueba**. Una cola durable prepara la transacción; actualizar la pantalla en un minuto.
4. Pulsar **Abrir pago en PayPhone** desde el dominio autorizado e iniciar el pago en la página del proveedor. No se embebe su formulario ni se recogen tarjetas en Odoo.
5. El retorno recibe `id` y `clientTransactionId`, consulta `V2/Confirm` desde el servidor y verifica ID, referencia, importe y moneda. El navegador no acredita pagos.
6. La cola concilia el pago aprobado con el contrato y solicita una sola instancia local. No activa un contrato cambiado, vencido o solapado; conserva el error para revisión. El trabajador de aprovisionamiento Windows sigue siendo el responsable de materializar la instancia.

## Recuperación y límites

- Prepare se reserva y confirma en base antes de contactar al proveedor. Un timeout o caída deja revisión pendiente; no se reenvía automáticamente un cobro incierto.
- Una denegación de credenciales HTTP 401/403 durante Prepare vuelve a borrador para corregir la configuración.
- Confirm se reintenta hasta tres veces con los mismos identificadores. El administrador puede solicitar otra conciliación tras revisar el panel. Un aprobado queda conservado aunque la activación falle y puede volver a conciliarse.
- Se impide cambiar credenciales de operaciones abiertas e importes enviados. Hay un pago por contrato para evitar duplicados en este incremento. Una preparación incierta, un enlace expirado o un pago cancelado requieren revisión del operador; no hay renovación automática de enlaces ni cierre/reembolso remoto implementados.
- La conciliación verifica las condiciones del contrato guardadas antes del envío. Las instancias y derechos son locales de ensayo; no se conceden derechos en los productos externos.
- El retorno necesita que la computadora, Odoo y el túnel estén activos. PayPhone documenta confirmación dentro de cinco minutos; una cola local no garantiza disponibilidad si se apaga la computadora.

## Verificación y reversión

Ejecutar `.venv/Scripts/python.exe scripts/verify-payphone.py` desde la raíz. Crea respaldo y copia aislada con filestore, ejecuta pruebas simuladas y conserva reporte privado en `.cache/windows/payphone-test-result.json`. No llama PayPhone. `scripts/install-payphone.py` exige pruebas aprobadas y hashes coincidentes antes de respaldar e instalar en el piloto A. Reinicia únicamente el proceso identificado de ese piloto.

Antes de retirar o actualizar la integración: detener nuevos ensayos, revisar pagos pendientes en PayPhone y conservar base y registros. Se puede desactivar la tarea **SK ERP: confirmar y conciliar pagos de prueba** después de resolver los pendientes. No borrar ni sobrescribir contratos, pagos, bases o filestore para revertir código. Restaurar el respaldo en un destino nuevo y verificar antes de sustituir una instalación. La retirada del módulo se bloquea si existen contratos de ensayo para evitar eliminar su evidencia.

## Pendiente para cerrar fase 04

- Credenciales cargadas privadamente y ensayo externo completo: preparación, pago por el probador, retorno, confirmación y conciliación de instancia.
- Recuperación de un ensayo externo y contraste de duplicados con PayPhone; las pruebas automatizadas son simuladas.
- Adaptador y validación Render, persistencia y permisos administrados cuando el usuario autorice pasar del piloto local; no se contrataron recursos.
- Actualizar el cierre firmado solo con evidencias completas. La dependencia de fase 05 continúa pendiente.

## Fuentes técnicas

Consultadas el 10 de septiembre de 2026:
- https://docs.payphone.app/boton-de-pago
- https://docs.payphone.app/configuracion-de-ambiente-y-credenciales
- https://developers.cloudflare.com/tunnel/routing/
