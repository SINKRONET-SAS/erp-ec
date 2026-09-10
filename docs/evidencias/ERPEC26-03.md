# ERPEC26-03 — Catálogo y contratos

Implementado erpec_suite con tres pantallas administrativas: planes versionados, contratos/derechos y vínculos explícitos a productos. Los planes usados no se alteran y las migraciones requieren suspender el contrato anterior antes de autorizar el sustituto. La autoridad de cobro se exige por contrato; no se ejecutan cargos.

- Cinco pruebas transaccionales Odoo aprobadas en cada una de las dos bases: cero fallos y cero errores
- Alta repetida, suspensión, reactivación, vencimiento, vigencia futura y cuotas verificadas
- Versiones inmutables, sustitución explícita y rechazo de contratos superpuestos verificados
- Lectura y acciones de organización ajena rechazadas con usuario sin privilegios
- Navegación real y formulario de planes en español sin errores JavaScript capturados

Ejecución: scripts/install-suite.py instala/actualiza y prueba ambos pilotos. Logs locales .cache/windows/a/odoo.log y b/odoo.log registran el último resultado 0 failed, 0 errors of 5 tests. Los ensayos se revierten transaccionalmente; no crean contratos comerciales reales. Se corrigió el nombre del CSV de permisos y se limitó el contexto de empresa de las pruebas, deshabilitando notificaciones de alta.

Captura visual revisada en .cache/windows/planes.png. La pantalla separa productos de API y muestra cuotas cuando corresponde. Los vínculos permanecen pendientes de verificación externa. No se declara SSO ni aplicación de cuotas en los otros productos.

Por instrucción expresa, el contexto vigente se movió a .github/CODEX_CONTEXT.md. Los nueve prompts, AGENTS y RULES usan ese nombre. Los locks históricos mantienen sus bytes originales, incluyendo la referencia que existía al cerrar cada fase.

Reversión comercial y límites de implementación: docs/CONTRATOS_SUITE.md. Para código/datos, restaurar el respaldo en un destino nuevo y validar antes de sustituir; no desinstalar para borrar contratos ni editar contratos autorizados.
