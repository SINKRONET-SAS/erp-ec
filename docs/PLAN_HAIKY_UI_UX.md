# Plan HAIKY UI/UX — ERP EC

Autorización: solicitud del titular del 13-09-2026 para planificar, ejecutar todos los prompts, corregir regresiones, cerrar gobierno y realizar commit y push. No requiere nuevas autorizaciones entre estas fases. Reglas: RULES.md. Contexto canónico: .github/CODEX_CONTEXT.md.

## Objetivo y alcance

Resolver los cuatro hallazgos de la revisión de inicio, ventas, cotización y Áreas en panel de 562 px. Conservar Odoo Community, permisos, reglas de negocio y diseño existente. La revisión inicial es evidencia de observación, no prueba de una causa: comprobar primero la confirmación de pedidos. No modificar fuentes externas, datos fiscales, nómina ni fases históricas 04–08.

| Fase | Dependencia | Entrega y aceptación |
|---|---|---|
| UIUX-00 | Gobierno anterior válido | Plan, cuatro prompts, contexto, diagnóstico y lock encadenado. No representa implementación. |
| UIUX-01 | UIUX-00 firmado | Confirmación encontrable; ventas adaptables sin perder cliente, importe ni estado; inicio compacto; Áreas agrupadas; etiquetas accesibles. Pruebas en copia aislada. |
| UIUX-02 | UIUX-01 firmado | Instalación con respaldo; verificación de accesos y regresión comercial; capturas estrechas y amplias; navegación y teclado. Corregir fallos y repetir comprobaciones afectadas. |
| UIUX-03 | UIUX-02 firmado | Evidencias, límites, contexto y plan cerrados; gobierno y diff verificados; commit y push confirmados. |

## Decisiones de implementación

- Confirmar dónde ubica Odoo las acciones de cabecera en ancho reducido. Reutilizar `action_confirm` y sus condiciones; no crear una segunda autoridad ni ampliar permisos.
- Preferir vistas nativas: tarjetas en pantalla pequeña y listado en escritorio, con filtros y apertura del mismo registro.
- Compactar solo el inicio; conservar identificación de empresa y advertencias operativas.
- Agrupar Áreas mediante componentes nativos navegables con teclado, usando el árbol de menús ya filtrado por permisos.
- Añadir nombres accesibles a los controles del recorrido que solo muestran iconos. No declarar conformidad WCAG a partir de capturas.

## Validación y reversión

Pruebas del centro y regresión de compras/ventas/Tesorería en copia aislada. Comprobar vistas, permisos de vendedor y perfil sin acceso, estados borrador/enviado/confirmado/cancelado y navegación comercial. Instalar únicamente el módulo afectado con el instalador existente, que verifica hashes y respalda base, archivos y módulos. Conservar ruta y hash de respaldo en evidencia. Para reversión: revertir el commit de UI y reinstalar el módulo anterior tras pruebas; recuperación de base solo si fuera necesaria, usando el procedimiento de recuperación aislada existente, nunca sustituyendo la demo sin comprobar el respaldo.

Evidencias por fase: `docs/evidencias/ERPEC26-UIUX-XX.json`. Capturas en `docs/evidencias/uiux/`. Cada cierre conserva bytes del lock anterior y firma SHA256(bytes anteriores + updatedAt). Los estados históricos se conservan por separado; este plan no cierra validaciones fiscales, laborales o bancarias.

Estado técnico: UIUX-00, UIUX-01, UIUX-02 y UIUX-03 cerradas en el alcance de este incremento. Publicación: commit y push se comprueban después del cierre del lock; la identidad Git se entrega en el mensaje final.

Resultado: 21/21 pruebas de regresión, 9/9 del módulo final; instalado erpec_workspace con respaldo workspace-install-20260913-152951. Diez áreas y enlaces comerciales comprobados. Capturas a 375/562/1280 px y teclado. Informe: evidencias/ERPEC26-UIUX-INFORME.md. Las correcciones visuales realizadas en UIUX-02 se probaron de nuevo antes de cada instalación.

Gobierno: uiUx.phaseCompleted registra las fases de este plan; phaseCompleted y phaseInProgress conservan el estado histórico del ERP. El lock de UI/UX contiene hashes del alcance propio y enlaza los bytes completos del predecesor; no acredita cambios concurrentes de otros planes. Los PNG se verifican por los hashes incluidos en ERPEC26-UIUX-02.json. No se declara restauración ni conformidad WCAG.
