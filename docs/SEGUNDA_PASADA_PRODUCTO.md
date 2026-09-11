# Segunda pasada de producto — ERP EC

Autorizada por la solicitud de estabilización y UI/UX del 11 de septiembre de 2026. Esta prioridad sustituye temporalmente la ampliación aislada de módulos. No cierra fases fiscales, laborales ni de nube del plan ERPEC26.

## Objetivo y criterio de entrega

Una sola experiencia de trabajo por empresa y perfil, con procesos verificables de principio a fin, mensajes comprensibles, recuperación probada y límites funcionales visibles. Una pantalla nueva o una prueba de cálculo aislada no acredita que el ERP sea comercializable.

Se conserva Odoo Community y sus formularios. El módulo erpec_workspace coordina la navegación y presentación de los incrementos existentes. No duplica cálculos, asientos, pagos ni estados fiscales. Los repositorios fuente permanecen intactos.

## Auditoría inicial y respuesta

Evidencia visual local: .cache/segunda-pasada/antes-inicio.png y antes-facturas.png. Capturadas e inspeccionadas durante esta revisión, con sesión real de la demo.

| Recorrido | Hallazgo observado | Prioridad | Respuesta |
|---|---|---|---|
| Ingreso → inicio | Ficha «Nuevo» con guardar/descartar; cuatro accesos y lenguaje de infraestructura | Alta | Centro de trabajo de solo lectura sobre una ficha persistida por empresa |
| Inicio → áreas | Producción, importaciones y nómina no aparecen entre los accesos principales | Alta | Cuatro áreas de trabajo y menú ERP EC común, conservando permisos |
| Inicio → fiscal | El aviso dirige a integración externa sin explicar la preparación local existente | Alta | Alcance local explícito; conector externo sigue disponible como pruebas |
| Navegación tras inicio | En la primera revisión del cambio, el contexto de solo lectura ocultaba crear en las áreas | Alta | Contexto operativo conservado; solo la vista de inicio es de lectura |
| Recarga del inicio | Una acción sin identificador estable podía volver a la vista técnica | Alta | Acción de ventana explícita para conservar la vista al recargar |
| Nómina e importaciones | «Company», años con separador de miles y tablas densas | Media | Etiquetas en español, año sin agrupación, columnas opcionales y estados con texto |
| Facturas a 752 px | Números, nombres y estados se truncan en la tabla | Media, abierta | La navegación mejora; queda pendiente la revisión específica de listas financieras en móvil |

La revisión visual inicial cubre la sesión administradora y el ancho disponible del panel. No acredita accesibilidad WCAG, uso por lector de pantalla, navegación integral por teclado ni todos los dispositivos.

## Orden de trabajo y puertas de salida

### SP01 — Coordinación y navegación

Implementación del centro de trabajo, acceso por perfiles, empresa activa, vista persistente, textos de alcance y ajustes de nómina/importaciones. Validar:
- Iniciar y recargar sin ficha nueva ni controles de guardar.
- Abrir áreas y volver sin perder botones de creación o permisos.
- Usuario interno sin privilegios: consulta del inicio, sin escritura ni acceso a nómina.
- Portal bloqueado; cambio de empresa devuelve la ficha correspondiente.
- Respaldar antes de instalar y recuperar una copia aislada con los mismos archivos.

La evidencia de ejecución se registra por separado en ERPEC26-SEGUNDA-PASADA.json. La existencia de esta sección no acredita que los puntos hayan pasado.

### SP02 — Aceptación transversal por perfil

Pendiente. Recorrer y corregir con datos ficticios identificables y parámetros reales:
1. Comercial y contabilidad: cotizar → confirmar → entregar → facturar → cobrar → conciliar; devolución y saldo parcial.
2. Compras y bodega: comprar → recepción parcial → factura proveedor → pago y devolución.
3. Producción: disponibilidad → orden → operación → pausa con motivo → parcial → cierre → venta y valoración.
4. Importaciones: dos productos, moneda extranjera, recepciones y gastos clasificados → distribución → asiento → reversión.
5. Nómina: dos empleados y centros → novedades → revisión → cálculo → aprobación → asiento → pago conciliado → corrección.
6. Fiscal: preparar → firmar → enviar → consultar → autorizado/rechazado → RIDE; reintento y prevención de duplicados.

Registrar documento origen, resultado, asiento, permiso, mensaje y evidencia de cada transición. Los puntos 5 y 6 requieren completar funciones pendientes antes de declararlos aprobados.

### SP03 — Operación y calidad de servicio

Pendiente de cierre integral. Arranque reproducible bajo el propietario de las sesiones; recuperación después de cada clase de migración; aislamiento entre empresas; permisos por rol; trazabilidad de errores; observación de tiempos con carga representativa; estados vacíos, errores y recuperación por teclado y móvil. La recuperación aislada de SP01 es una primera evidencia, no una garantía general de continuidad.

### SP04 — Puerta comercial

No ofrecer como ERP productivo completo hasta:
- Completar emisión fiscal real (secuencias, autoridad, firma, SRI y RIDE), con pruebas y normativa aplicable.
- Completar equivalencia laboral, pago conciliado y corte de autoridad por empresa. SKNOMINA tiene API; sigue siendo alternativa.
- Aprobar los recorridos SP02 y la operación SP03.
- Definir alcance contractual, soporte, licencias, respaldo, protección de datos, infraestructura y límites del servicio.
- Aprobar un piloto con usuarios de los perfiles reales.

Render sigue pospuesto; la prueba previa de PAYPHONE por túnel no se repite ni se desconoce. La demo conserva sus credenciales y no se incorpora un RUC ficticio para habilitar emisión.

## Verificación y recuperación del incremento

Pruebas del centro: `.venv/Scripts/python.exe scripts/verify-workspace.py`.
Instalación en demo: `.venv/Scripts/python.exe scripts/install-fiscal-native-demo.py --workspace`, con el propietario Windows de las sesiones. El instalador exige resultados y hashes coincidentes; respalda base, filestore y módulos antes de detenerse en la actualización; conserva el inicio anterior en el respaldo.

Ensayo de recuperación de un respaldo que ya contiene el centro: `.venv/Scripts/python.exe scripts/restore-operational-demo.py --backup RUTA_ABSOLUTA --expect-workspace`. Crea base, usuario y carpetas nuevos; no reemplaza la demo. Verifica archivos, carga del registro, acceso al centro y presencia de asientos.

Para retirar una actualización fallida se debe recuperar su respaldo completo y comprobarlo antes de cambiar el servicio. Desinstalar solamente erpec_workspace no basta para restaurar menús que fueron reorganizados. No ejecutar el ensayo histórico de recuperación sin --expect-workspace sobre respaldos recientes; ese ensayo espera la ausencia de nómina.

## Incremento SP02 de compras

Seguimiento implementado y recorrido automatizado por perfiles documentados en SP02_COMPRAS.md. Hallazgo prioritario SP02-D01: sanear los documentos de la semilla inicial que contienen retenciones ficticias y clasificación contable inadecuada para el servicio mostrado. Se advierte en pantalla; no se aceptan como parámetros reales. SP02 y la puerta comercial permanecen abiertos.
