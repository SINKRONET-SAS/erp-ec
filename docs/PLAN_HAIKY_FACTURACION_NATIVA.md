# Plan HAIKY — Facturación electrónica nativa: firma real + transmisión SOAP directa al SRI

Autorizado por el titular el 16-09-2026, en respuesta a la necesidad de que la facturación electrónica quede funcional y operativa según la legislación ecuatoriana. Se tomó como referencia `C:\proyectos web\sinkroniq-mobile` (backend real del Facturador) y `C:\proyectos web\nuevo_nomina` (RDEP/nómina) — investigación de solo lectura, sin modificar ninguno de esos dos proyectos.

## Decisión de arquitectura

El titular eligió explícitamente **construir transmisión SOAP nativa al SRI**, en vez de solo conectar la firma ya existente al conector externo, para no duplicar el costo de correr dos servicios en Render (el ERP y el Facturador externo). Esta es ahora una **segunda autoridad de emisión**, independiente de `erpec_fiscal_connector` (que delega en el Facturador externo), gobernada por la misma regla "una autoridad por comprobante" ya existente en el proyecto.

## Hallazgos previos a la implementación

- `addons/erpec_fiscal_native/xades.py` ya existía: una implementación real y correcta de firma XAdES-BES, pero **sin pruebas propias y sin estar conectada a ningún flujo** — código huérfano. Se le agregaron 11 pruebas (certificado sintético autofirmado, no uno real del SRI).
- `addons/erpec_fiscal_native/engine.py` ya calcula la clave de acceso de 49 dígitos con módulo 11 real; **confirmado exacto** contra la Ficha Técnica 2.34 oficial (ver abajo).
- `addons/erpec_fiscal_connector/connector.py` (en edición por una sesión concurrente durante este incremento): conector real hacia el Facturador externo. No se tocó.
- Nuestro RDEP ya está por delante de `nuevo_nomina` en los puntos revisados (campos reales de utilidades/salario digno/gastos desglosados donde esa referencia los deja en cero fijo; tope de gastos personales ya escalado por cargas familiares según NAC-COM-26-006, mientras esa referencia usa un tope plano desactualizado). **No se portó nada de nómina en este incremento.**

## Verificación contra la Ficha Técnica 2.34 del SRI (fuente primaria, PDF oficial leído)

Consultado el 16-09-2026 en sri.gob.ec, "Ficha Técnica de Comprobantes Electrónicos Esquema Off-line — Versión 2.34", actualizada julio 2026:

- **Clave de acceso (49 dígitos)**: composición y orden exactos confirmados contra la Tabla 1 de la ficha — coincide con lo ya implementado en `engine.py`.
- **Estructura de mensajes SOAP** (`identificador`/`mensaje`/`informacionAdicional`/`tipo`, valores `ERROR`/`ADVERTENCIA`): confirmada contra la Sección 11 (tablas de códigos de error y advertencia). Coincide con lo implementado en `sri_client.py`, y se confirmó además con una respuesta real del SRI (ver más abajo, código 39).
- **Código de barras del RIDE**: la ficha lo marca explícitamente como **opcional** ("podrá incorporar"), no obligatorio — se corrige la suposición inicial de que era requerido. Se mantiene en el generador porque es una mejora legítima, no un requisito.
- **Sin requisito de marca de agua "AMBIENTE DE PRUEBAS"** en el RIDE — no encontrado en el texto de la ficha. El mecanismo real para ambiente de pruebas es la advertencia código 60 en la respuesta SOAP y, opcionalmente, usar "PRUEBAS SERVICIO DE RENTAS INTERNAS" como razón social del receptor.
- **Sin verificar**: el layout completo del RIDE en la ficha es una imagen incrustada, no texto extraíble — no se pudo confirmar contra ella campo por campo. El RIDE construido incluye el contenido típicamente exigido (clave de acceso, emisor, comprador, detalle, impuestos, totales, forma de pago, autorización) pero no se declara conformidad visual con la ficha 2.34.

## Diseño implementado

- **`erpec.fiscal.certificate`** (nuevo modelo): certificado .p12 por empresa, protegido por `base.group_system` (mismo nivel que el token de PayPhone; sin cifrado adicional en reposo, documentado igual que PayPhone). Verificación reutiliza `xades.credentials()`, no la duplica.
- **`erpec.fiscal.emission`** (nuevo modelo): cola durable, mismo patrón que `erpec.fiscal.job` (bloqueo `FOR UPDATE`, `unlink()` bloqueado, `write()` restringido a acciones). Estados: `draft`→`signed`→`sent`→`waiting`→`authorized`/`rejected`/`returned`/`blocked`.
- **`addons/erpec_fiscal_sri/sri_client.py`** (nuevo): cliente `zeep` contra los WSDL reales de `celcer.sri.gob.ec` (pruebas). Ambiente de producción (`cel.sri.gob.ec`) deshabilitado explícitamente en el código (`AMBIENTES['2']['enabled'] = False`) hasta una activación separada.
- **`addons/erpec_fiscal_sri/ride.py`** (nuevo): RIDE con `reportlab`, a partir del XML ya autorizado por el SRI.
- Nuevo addon **`erpec_fiscal_sri`** (no se modificó `erpec_fiscal_native`/`erpec_fiscal_connector` más allá de agregar `tests/test_xades.py`), evitando el conflicto de archivos con la sesión concurrente.
- `_gather_native_data()` duplica intencionalmente una porción pequeña de la validación de líneas de `action_native_preview` (el archivo que la contiene está en edición concurrente); consolidar en un incremento posterior.

## Verificación de punta a punta

1. **32 pruebas unitarias** en bases aisladas y nuevas (11 de `xades.py`, 21 de `erpec_fiscal_sri`), todas con mocks para las llamadas SOAP — sin tocar la red real en la batería automática.
2. Instalado en la demo con respaldo previo (`fiscal-sri-install-20260916-210040`); ambas vistas compilan.
3. **Ensayo real, no mockeado, contra `celcer.sri.gob.ec`**: se generó una clave de acceso real, se firmó con un certificado sintético autofirmado, y se transmitió de verdad. El SRI **recibió** el documento (RECIBIDA) y, al consultar la autorización, lo **rechazó exactamente por la razón esperada**: código 39, "FIRMA INVALIDA... no existe un certificado root registrado para la entidad certificadora". Esto confirma que todo el canal (generar → firmar → transmitir → consultar) funciona correctamente contra la infraestructura real del SRI — lo único que falta es un certificado emitido por una entidad certificadora acreditada por el SRI.
4. Gobierno del proyecto: este plan, `CODEX_CONTEXT.md`, `AuditLock.json` y prompt de fase — commit y push solo de archivos propios, sin tocar `erpec_fiscal_connector`/`erpec_fiscal_native` más allá de la nueva prueba de `xades.py`.

## Pendiente explícito

- **Certificado de firma electrónica real**, emitido por una entidad certificadora acreditada por el SRI (Security Data, ANF AC, BCE u otra) — sin él no se puede obtener una autorización real, solo se demostró el canal completo hasta el rechazo esperado por confianza de certificado.
- Activar ambiente de producción (`cel.sri.gob.ec`) — deliberadamente deshabilitado en el código.
- Guarda recíproca en `erpec_fiscal_connector` (bloquear el conector externo si ya existe una emisión nativa) — pendiente de que la sesión concurrente libere ese archivo.
- Consolidar `_gather_native_data()` con la lógica de `action_native_preview` una vez que `erpec_fiscal_native/models.py` esté libre.
- Conformidad visual completa del RIDE contra la Ficha Técnica 2.34 (su layout es una imagen, no se pudo verificar campo por campo).
