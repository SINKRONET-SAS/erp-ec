# Alcance del autoservicio de altas (landing → plan → pago → aprovisionamiento)

Autorizado por el titular el 14-09-2026: "me gustaría que sea un autoservicio la creación de un nuevo cliente, debería hacerse desde una landing page en función a un plan contratado", con alcance confirmado como "flujo completo de punta a punta" (landing, pago real, aprovisionamiento automático sin clic de administrador entre el pago y la instancia lista).

## Decisiones confirmadas con el titular

1. **Vía de pago**: se reutiliza `erpec_payphone` quitando el tope de USD 100 y el rotulado de "ensayo, sin alta productiva", en vez de construir un camino paralelo. El campo interno `billing_owner='payphone_test'` no se renombra (evita romper evidencia/datos existentes); solo se corrigió su etiqueta visible.
2. **Instancia operadora**: `erpec_fundador` (la empresa real de SINKRONET S.A.S., creada el 14-09-2026 en `.cache/windows/fundador`, puerto 8199) — ahí vive el panel comercial (`erpec_suite`, `erpec_provision`, `erpec_payphone`) que vende suscripciones a otras empresas. Los pilotos sintéticos `erpec_a`/`erpec_b` dejan de ser la instancia operadora de referencia para este flujo; `scripts/provision-worker.py` se reapuntó a `erpec_fundador`.

## Lo que ya existía y se reutilizó sin cambios de mecánica

- `erpec_suite` (`erpec.plan`/`erpec.subscription`): catálogo de planes y contratos, con `action_activate()` idempotente y control de solapamiento.
- `erpec_payphone`: verificación **server-side** del pago (`V2/Confirm`, nunca el retorno del navegador), `_contract_digest()` anti-manipulación, `_lock()`, idempotencia de `_receive_return`, `_reconcile()` que ya encadenaba `action_activate()` → `erpec.provision._request()`. Probado antes con una transacción real de prueba por túnel (docs/PAYPHONE_LOCAL.md).
- `erpec_provision` (`erpec.provision`): cola `claim_next()`/`finish()` con lease y token de un solo uso.
- `scripts/provision-worker.py`: worker funcional (no un stub) que crea rol/base PostgreSQL, `odoo.conf`, instala módulos, arranca el proceso y verifica salud. Candado de un solo proceso por host; rango de puertos reservado 8181–8299 (`8180+job.id`).

**No se tocó** `_confirm`, `_reconcile`, `_contract_digest`, `_lock`, `_receive_return`, `action_prepare`, ni la lógica de `claim_next`/`finish`/`operate()` del worker.

## Lo que se agregó o modificó en este incremento

- `erpec_suite`: `erpec.plan.published` (booleano, `default=False`) y `erpec.plan.price`/`currency_id` (antes el plan solo tenía `terms` en texto libre — no existía un precio estructurado del que tomar el monto a cobrar). Un plan publicado exige `price > 0` (constraint). Ningún plan existente quedó publicado ni con precio por el solo hecho de instalar este incremento.
- `erpec_payphone`: tope de `_validate_amounts` subido de USD 100 a USD 100 000 (techo anti fat-finger, no de "modo prueba"); rotulado corregido en modelos, vistas, controlador y manifest. Ruta `/payment/payphone/checkout/<reference>` cambiada de `auth='user'` a `auth='public'` (con `.sudo()` en la búsqueda) — excepción acotada y verificada: la referencia es un UUID no adivinable, la página solo muestra el enlace de checkout ya generado por PayPhone, ningún dato privado.
- **Nuevo addon `erpec_selfservice`** (depende de `erpec_payphone`):
  - `erpec.selfservice.request`: registra la solicitud (empresa, RUC, régimen declarado, contacto, plan) y enlaza el contrato/pago generados. Solo `base.group_system` tiene acceso ORM — el visitante público nunca obtiene sesión ni permisos; toda escritura ocurre en el controlador bajo `with_user(base.user_admin).sudo()`.
  - `create_from_signup()`: crea la solicitud, el `erpec.subscription` (mismo `billing_owner` reutilizado, `authorization`/`billing_reference` autogenerados con la referencia de la solicitud) y el `erpec.payphone.payment`, llama `action_prepare()` y fuerza `_cron_process()` de inmediato (en vez de esperar el minuto del cron) para poder redirigir al checkout dentro de la misma solicitud HTTP.
  - Controlador público (`GET /autoservicio`, `POST /autoservicio/solicitar`): HTML plano vía `request.make_response()`, mismo patrón que `erpec_payphone` — sin depender de los módulos `website`/`portal` (no instalados en el proyecto). Formulario protegido con el token CSRF estándar de Odoo.
  - **Supuesto explícito no verificado contra ningún acuerdo comercial**: la suscripción de autoservicio dura un mes calendario desde la solicitud (`erpec.plan` no tiene hoy un campo de periodicidad). Ajustar si se decide otra periodicidad.
- `scripts/provision-worker.py`: la conexión operadora hardcodeada (`erpec_a`/8169) se volvió configurable (`rpc(url, database, password, login)`) y se reapuntó por defecto a `erpec_fundador`/8199 con login `fundador`. `scripts/verify-provision.py` (harness de ensayo del piloto sintético) no se tocó — sigue probando `erpec_a` de forma independiente.

## Verificación realizada

- 34/34 pruebas en base aislada y nueva (`erpec_selfservice`, más las de `erpec_payphone`/`erpec_suite` afectadas por el rotulado/tope), 0 fallos, 0 errores.
- Instalado en `erpec_fundador` con respaldo previo (`fundador-selfservice-install-20260914-201956`); las seis vistas relevantes compilan (`erpec.plan`, `erpec.subscription`, `erpec.payphone.provider`, `erpec.payphone.payment`, `erpec.selfservice.request`, `erpec.provision`).
- **Rehearsal real por HTTP** (sin credenciales de producción de PayPhone, que el titular no ha entregado todavía): `GET /autoservicio` mostró el plan publicado con su precio; `POST /autoservicio/solicitar` con datos sintéticos completó todo el recorrido del lado del servidor (solicitud, contrato, pago) hasta llamar de verdad a la API de PayPhone, que rechazó el `Prepare` por credenciales placeholder inválidas (`PAYPHONE_CREDENTIALS`). Esto confirma la conexión real de punta a punta sin mover dinero ni requerir una cuenta válida. Quedaron en `erpec_fundador` un plan (`SS-DEMO`), un proveedor con credenciales placeholder y una solicitud/contrato/pago sintéticos de este rehearsal (no se pueden eliminar por diseño — `perm_unlink=0`, igual que el resto de `erpec_payphone`/`erpec_suite` — quedan documentados aquí explícitamente como no reales).

## Pendiente explícito

- Credenciales reales de producción de PayPhone (las debe proporcionar el titular).
- Registrar `provision-worker.py --watch` como servicio de arranque automático de Windows, o adaptarlo a Render (ver docs/APROVISIONAMIENTO_WINDOWS.md) — sigue siendo manual en este incremento.
- Diferenciar el conjunto de módulos instalados por tipo de plan (ERP completo vs. solo nómina/facturación); el worker sigue instalando el mismo conjunto completo que ya usa `erpec_fundador`.
- Verificar que ningún `job.id` futuro de `erpec_provision` colisione con el puerto 8199 (el propio `erpec_fundador`, que no es un cliente aprovisionado — ocurriría solo si se acumulan 19+ trabajos).
- Sin protección anti-abuso (límite de solicitudes, CAPTCHA) en las rutas públicas nuevas; razonable mientras el flujo corre solo en local, no para una exposición pública real a Internet.
- Textos legales/términos y condiciones del formulario de alta — no se inventan cláusulas.
