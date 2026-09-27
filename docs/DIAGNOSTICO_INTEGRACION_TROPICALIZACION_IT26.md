# Diagnóstico Técnico Integral: Integración de la Tropicalización a Ecuador y Funcionalidad Nativa de Odoo

**Código de referencia:** IT26 (Integración y Tropicalización 2026)
**Fecha:** 26 de septiembre de 2026
**Repositorio:** `SINKRONET-SAS/erp-ec`
**Rama:** `codex/erpec26-implementacion`
**Base:** Odoo Community 18.0 oficial (commit fijado `b1fd3a9eee5d575848ac649d2f5103537d8de7a4`)

---

## 1. Resumen y Propósito del Diagnóstico

El ERP EC ha alcanzado hitos técnicos de alta complejidad: autorización real de facturas electrónicas ante el SRI (`celcer.sri.gob.ec`), motor de retenciones del catálogo ATS, nómina ecuatoriana 2026 con RDEP y décimos, exportación bancaria de nómina a 3 entidades y controles de protección de datos. Estos avances no acreditan cumplimiento integral de la LOPDP.

Sin embargo, desde la perspectiva de **experiencia de usuario (UI/UX), arquitectura de producto y comercialización directa**, el sistema adolece de una patología crítica: **la localización ecuatoriana se percibe como un «desagradable apéndice» superpuesto sobre Odoo, en lugar de una experiencia cohesiva, orgánica y profesional.**

Este diagnóstico desglosa los hallazgos en tres dimensiones clave:
1. **Interfase y UX:** Análisis de la fragmentación visual, doble navegación y mutilación de patrones nativos de Odoo.
2. **Referencias a Odoo Enterprise:** Identificación de advertencias, disculpas y textos que devalúan el producto e interfieren con la comercialización.
3. **Duplicaciones, Errores y Regresiones:** Inventario de modelos en pugna, alertas de laboratorio incrustadas en formularios y menús huérfanos.

---

## 2. Hallazgos: La Tropicalización como «Apéndice» vs. Sistema Coordinado

### Hallazgo IT26-01: Doble y Triple Navegación en la Barra Superior (NavBar)
- **Diagnóstico:** En la barra de navegación superior coexisten tres elementos en conflicto:
  1. El parche OWL (`erpec_workspace/static/src/product_shell.js` y `product_shell.xml`) que inserta un botón de marca `[ERP EC SINKRONET]` y un menú desplegable `[Áreas]`.
  2. El menú nativo de aplicaciones de Odoo (`web.NavBar.AppsMenu`, el icono de 9 puntos).
  3. Múltiples aplicaciones raíz independientes en la barra: `Contabilidad ERP EC`, `ERP EC` (`suite_root`), conviviendo con las aplicaciones nativas instaladas (`Ventas`, `Compras`, `Inventario`, `Facturación`, `Fabricación`, `Empleados`).
- **Impacto UX:** El usuario experimenta desorientación severa. Si abre `Áreas`, encuentra un subconjunto arbitrario de procesos que omite aplicaciones esenciales como `Contactos` y `Empleados`. Además, existen "paneles de inicio" estáticos (`erpec_operations.operation_form` y `erpec_withholding_accounting.accounting_form`) que consisten únicamente en rejillas de botones para abrir vistas nativas de Odoo, actuando como una barrera innecesaria entre el usuario y la aplicación.
- **Solución requerida:** Unificar la navegación. El lanzador de aplicaciones debe ser el único punto de entrada unificado, o bien `Áreas` debe cubrir el 100% de las áreas de negocio sin duplicar el menú de 9 puntos ni crear pantallas intermedias con botones redundantes.

### Hallazgo IT26-02: Mutilación de Formularios Nativos con «Cajas de Seguimiento»
- **Ubicación:** `addons/erpec_workspace/sale_views.xml` (Líneas 6-19) y `addons/erpec_workspace/purchase_views.xml` (Líneas 6-20).
- **Diagnóstico:** En los formularios de Pedido de Venta (`sale.order`) y Orden de Compra (`purchase.order`), se inyecta un bloque HTML intrusivo debajo del título:
  ```xml
  <div class="border rounded p-3 my-3">
    <h2>Seguimiento de la venta/compra</h2>
    <field name="erpec_sale_guide" nolabel="1" class="d-block mb-2"/>
    <div class="d-flex flex-wrap gap-2">
      <!-- Botones duplicados de confirmación, entregas y facturación -->
    </div>
  </div>
  ```
  En compras se oculta mediante `<xpath>` una variante de `action_create_invoice` del encabezado nativo. En ventas, `sale_views.xml` no oculta `action_confirm`: añade una segunda acción en el bloque de seguimiento.
- **Impacto UX:** Destruye el patrón de diseño estándar de Odoo. Los usuarios experimentan una pantalla pesada, no estándar, donde las acciones principales están duplicadas entre este cajón y los smart buttons superiores (`oe_button_box`).
- **Solución requerida:** Retirar las cajas de seguimiento. Restablecer los botones nativos en el `<header>` y canalizar la trazabilidad hacia los `oe_button_box` (smart buttons) de la esquina superior derecha con sus insignias numéricas nativas.

### Hallazgo IT26-03: Hiper-fragmentación en la Factura (`account.move`) — 6 Pestañas en Pugna
- **Ubicación:** `erpec_fiscal_connector/views.xml`, `erpec_fiscal_native/views.xml`, `erpec_fiscal_sri/views.xml`, `erpec_workspace/tax_intersection_views.xml`, `erpec_fiscal_documents/views.xml`, `erpec_withholding_accounting/views.xml`.
- **Diagnóstico:** Al abrir una factura de cliente o proveedor en Odoo, el `<notebook>` acumula hasta seis pestañas separadas añadidas por distintos módulos:
  1. `Facturador — Pruebas`
  2. `Facturación local`
  3. `Firma y transmisión SRI`
  4. `Retenciones del plan`
  5. `Ecuador`
  6. `Retenciones con efecto contable`
- **Impacto UX:** Ningún contador o facturador puede operar con fluidez teniendo la información tributaria y fiscal dispersa en 6 pestañas, con múltiples botones de acción («Preparar / abrir envío fiscal», «Validar y descargar XML», «Firmar y transmitir al SRI», «Gestionar retenciones»).
- **Solución requerida:** Consolidar en una **única pestaña limpia: `Comprobante Electrónico (SRI)`**. Trasladar el botón principal de emisión al `<header>` nativo (`[Firmar y transmitir SRI]`) visible cuando la factura está contabilizada (`posted`), y colocar un smart button en cabecera con el estado del SRI (`[SRI: Autorizado]`). Conectar las retenciones de compras mediante un smart button nativo `[Retención]`.

### Hallazgo IT26-04: Guías de Remisión Desconectadas de Inventario
- **Ubicación:** `addons/erpec_fiscal_guide_sri/views.xml` (Línea 12).
- **Diagnóstico:** El menú de Guías de Remisión está registrado bajo el menú `Fiscal · Pruebas` (`erpec_fiscal_connector.fiscal_root`), fuera del menú nativo de Inventario. La integración funcional con `stock.picking` sí existe: `views.xml` define `picking_guide_button`; `models.py` define `ec_guide_ids`, `picking_id` y `action_create_sri_guide`, que crea o abre la guía vinculada. El hallazgo se limita a ubicación de menú y ausencia de smart button, no a falta de integración.
- **Solución requerida:** Integrar el acceso a Guías de Remisión en el menú oficial de `Inventario -> Operaciones -> Guías de remisión SRI` y enriquecer `stock.picking` con un smart button que vincule directamente la guía emitida.

### Hallazgo IT26-05: Nómina y Ficha de Empleados Desarticuladas
- **Ubicación:** `addons/erpec_payroll/views.xml` y `addons/hr/`.
- **Diagnóstico:** La nómina ecuatoriana opera en un silo (`erpec_payroll`). En la ficha oficial del colaborador (`hr.employee`), la única presencia de la localización es una pestaña «Anexo RDEP» saturada de avisos legales en texto plano. No existen smart buttons en el empleado para consultar sus roles de pago, histórico de décimos, liquidaciones o saldos de préstamos/anticipos.
- **Solución requerida:** Integrar smart buttons nativos en `hr.employee` (`[Roles de Pago]`, `[Liquidaciones]`, `[Anticipos/Préstamos]`) y depurar los textos de la pestaña RDEP.

---

## 3. Hallazgos: Referencias a Odoo Enterprise y Alineación Comercial

### Hallazgo IT26-06: Banners Explícitos Descalificativos en Vistas de Usuario
- **Ubicación:** `addons/erpec_operations/views.xml` (Línea 19):
  ```xml
  <p>La emisión electrónica sigue pendiente de integración. Las funciones de Enterprise no forman parte de este producto.</p>
  ```
- **Diagnóstico:** La interfaz muestra directamente al usuario un texto apologético que menciona "Enterprise", dando la impresión de que el ERP es una versión incompleta o degradada.
- **Solución requerida:** Erradicar cualquier mención a Odoo Enterprise en todas las vistas de usuario (`*.xml`), cadenas de traducción, descripciones de menús y mensajes de interfaz. El sistema debe presentarse con orgullo comercial como **ERP EC**, una solución empresarial completa y localizada para Ecuador.

### Hallazgo IT26-07: Separación Estricta entre Cumplimiento de Licencias y Copywriting de Producto
- **Diagnóstico:** En la documentación técnica y de auditoría (`docs/`) es correcto y necesario dejar constancia de que no se incorporan módulos propietarios (`OEEL-1`/`OPL-1`) para garantizar la legalidad de la comercialización de Odoo Community bajo LGPL-3.0. Sin embargo, esta distinción técnica se filtró indebidamente hacia los títulos de acciones y formularios (ej. «Operación Community», «Aplicaciones ERP EC · Community»).
- **Solución requerida:** Limpiar los títulos de menús y vistas, retirando la palabra "Community" o "Enterprise" de la experiencia de usuario.

---

## 4. Hallazgos: Errores, Duplicaciones y Alertas de Laboratorio

### Hallazgo IT26-08: Invasión de Alertas de Depuración Interna en Formularios de Negocio
- **Ubicación:** `addons/erpec_payroll/views.xml` (Líneas 18, 21, 23, 25, 35, 46, 50).
- **Diagnóstico:** Los formularios de nómina, períodos, políticas y empleados contienen múltiples bloques `<div class="alert alert-*">` con anotaciones de desarrollo interno:
  - *"Caso 8 (DI25-03): enfermedad (con certificado IESS)..."*
  - *"Ver docs/ALCANCE_ATS_RDEP.md"*
  - *"la migración productiva desde SKNOMINA sigue pendiente"*
  - *"Datos de demostración con parámetros laborales reales..."*
- **Impacto UX:** Estos textos transmiten inmadurez técnica y confunden al usuario final en una empresa real.
- **Solución requerida:** Reemplazar estos bloques de alerta por atributos nativos de campo `help="..."`, textos discretos con clase `text-muted` donde sea estrictamente necesario, o ayuda contextual de Odoo.

### Hallazgo IT26-09: Triplicación del Modelo de Retenciones
- **Diagnóstico:** Coexisten tres estructuras de retención:
  1. `ec_withholding_ids` (preparación preliminar sin asiento en `erpec_fiscal_documents`).
  2. `erpec_retention_ids` (retenciones del plan e intersección en `erpec_workspace`).
  3. `ec_accounting_withholding_ids` (retenciones con efecto contable y emisión SRI en `erpec_withholding_accounting` y `erpec_fiscal_withholding_sri`).
- **Solución requerida:** Consolidar la experiencia para que el cálculo preliminar se transforme fluidamente en el comprobante de retención contable y electrónico oficial, eliminando tablas y vistas intermedias duplicadas.

### Hallazgo IT26-10: Mensajes Hardcodeados de "Ambiente PRUEBAS" en Diálogos de Emisión
- **Ubicación:** `addons/erpec_fiscal_withholding_sri/views.xml` (Línea 3):
  ```xml
  confirm="Se firmará la retención con el certificado de la empresa y se transmitirá al SRI (ambiente PRUEBAS)."
  ```
- **Diagnóstico:** El mensaje de confirmación indica de forma estática `(ambiente PRUEBAS)`, lo cual es falso y confuso si la empresa opera en producción.
- **Solución requerida:** Dinamizar el mensaje en el método Python o retirar la mención estática de ambiente.

---

## 5. Matriz de Priorización del Plan Haiky IT26

| Código | Fase | Enfoque | Criticidad |
|---|---|---|---|
| **IT26-00** | Diagnóstico y Planificación | Despliegue de plan, prompts, contexto y AuditLock | Bloqueante de gobierno |
| **IT26-A** | Desparasitación Comercial | Erradicación de textos Enterprise, tickets y alertas internas en XML | Inmediata (P1) |
| **IT26-B** | Shell Web y Navegación Unificada | Resolución de doble barra (`Áreas` vs `AppsMenu`), eliminación de paneles estáticos | Alta (P1) |
| **IT26-C** | Limpieza de Ventas y Compras | Retiro de cajas de seguimiento; restitución de botones nativos y smart buttons | Alta (P1) |
| **IT26-D** | Consolidación de Factura SRI | Fusión de las 6 pestañas de `account.move` en un único flujo de facturación electrónica | Muy Alta (P1) |
| **IT26-E** | Nómina y Empleados Integrados | Smart buttons en `hr.employee`, limpieza de pestañas RDEP y períodos | Media (P2) |
| **IT26-F** | Guías e Inventario Integrados | Ubicación de guías de remisión en Inventario y vinculación con `stock.picking` | Media (P2) |
| **IT26-G** | Verificación Integral y Aceptación | Suite completa de pruebas (>660 tests), accesibilidad y validación sin regresiones | Cierre técnico |
