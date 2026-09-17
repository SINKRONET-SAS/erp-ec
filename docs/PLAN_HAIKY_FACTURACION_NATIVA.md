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

## Segundo incremento — conformidad visual del RIDE (16/17-09-2026)

Con el clúster de PostgreSQL local ya confirmado en marcha, se retomó el único pendiente de OP09 que no dependía de la sesión concurrente ni de un certificado del titular: la conformidad visual del RIDE. Un agente en segundo plano descargó el PDF oficial vigente de la Ficha Técnica 2.34 (sri.gob.ec, 142 páginas) y renderizó como imagen la página 60 (Anexo 2, ejemplo de RIDE de FACTURA) para inspeccionarla campo por campo — hasta ahora esa imagen incrustada no se había podido verificar. El titular pidió además usar como referencia de consulta el renderizador RIDE real de `sinkroniq-mobile` (`backend/src/pdf/renderers/classicRideStrategy.js` + `baseRideRenderer.js`, PDFKit), que ya está en producción y coincide en arquitectura con el ejemplo oficial: recuadro de emisor a la izquierda, recuadro de comprobante/autorización a la derecha, caja de comprador, tabla con barra de encabezado, totales alineados a la derecha.

Se reescribió `addons/erpec_fiscal_sri/ride.py` (archivo propio, sin tocar sinkroniq-mobile ni copiar su código) reproduciendo esa arquitectura de dos columnas con reportlab, y se agregaron los campos que el ejemplo oficial exige y que antes faltaban: AMBIENTE (PRUEBAS/PRODUCCIÓN) y EMISIÓN (NORMAL/CONTINGENCIA), etiquetas oficiales "NÚMERO DE AUTORIZACIÓN"/"FECHA Y HORA DE AUTORIZACIÓN", clave de acceso impresa debajo del código de barras (no antes), nombre comercial/dirección de sucursal/contribuyente especial/agente de retención/RIMPE/obligado a llevar contabilidad en el recuadro emisor, placa/guía de remisión en la caja de comprador, código auxiliar del ítem junto al código principal, y desglose oficial de SUBTOTAL por tarifa. Cada nombre de campo XML citado se confirmó contra `addons/erpec_fiscal_native/xsd/factura_V2.1.0.xsd` (fuente primaria) antes de usarlo — no se inventó ningún campo; los impuestos con código distinto de IVA (p. ej. ICE/IRBPNR) se muestran genéricos por número, sin asumir su nombre oficial no confirmado en esta revisión.

No se implementó: logo (no hay activo de marca en este incremento), QR (no es un requisito confirmado en la ficha 2.34, solo el código de barras Code128, que sí y es opcional), ni las secciones de reembolso/nota de crédito/guía de remisión del renderizador de referencia (nuestro `engine.py` solo genera factura ordinaria en este incremento).

Verificación: 3 pruebas nuevas (24 en total en `erpec_fiscal_sri`, 0 fallos/errores) que extraen el texto real del PDF generado (PyPDF2, ya declarado en `requirements-windows.txt`) y confirman que AMBIENTE, EMISIÓN, las etiquetas oficiales, el código auxiliar, la placa y la guía de remisión aparecen literalmente. Reinstalado en la demo con respaldo previo (`fiscal-sri-install-20260916-231142`); vistas compilan; sin registros de negocio creados.

## Reconfirmación del pendiente de firma electrónica — 17-09-2026

Tras los commits de CF01 (divulgación del RUC del proveedor del sistema) y el endurecimiento de `verify-payphone.py`, el titular pidió reconfirmar explícitamente el pendiente de la firma electrónica real, lo que implicó repetir la verificación de emisión en el ambiente de pruebas del SRI (no solo revisar documentación). Se re-ejecutaron las 11 pruebas de `xades.py` y las 24 de `erpec_fiscal_sri` contra el HEAD actual (0 fallos, 0 errores en ambas) y se repitió el ensayo real, no mockeado, de punta a punta contra `celcer.sri.gob.ec` con un documento sintético nuevo (clave de acceso `17092026...`, distinta de la del primer ensayo): **RECIBIDA** en recepción, **NO AUTORIZADO** en autorización, exactamente por el mismo motivo que el primer ensayo — código 39, "FIRMA INVALIDA... no existe un certificado root registrado para la entidad certificadora". Resultado idéntico al del primer incremento: el canal generar→firmar→transmitir→consultar sigue funcionando de punta a punta sin regresión, y el pendiente no cambió — sigue haciendo falta un certificado real emitido por una entidad certificadora acreditada por el SRI. No se usó ninguna credencial ni certificado real; ninguna autorización real se obtuvo.

## Certificado real provisto — primera autorización real obtenida (17-09-2026)

El titular indicó que ya había colocado un certificado de firma electrónica real en `.cache/private/fiscal-pruebas/` (fuera de git, protegido por `.gitignore`), y pidió verificarlo — aclarando que eso implicaba probar la emisión en el ambiente de pruebas del SRI, no solo inspeccionar el archivo. El certificado es real: emitido por **SECURITY DATA S.A. 2** (entidad certificadora acreditada en Ecuador), titular **BETTY ROSMERY GUAMAN CORREA** (RUC/cédula 1709053506001, identificado por el titular como un founder/colaborador de confianza del proyecto), vigente 2025-03-05 a 2028-03-04.

Verificación en dos pasos:

1. **Local** (`xades.credentials()`, el mismo chequeo que usa `erpec.fiscal.certificate.action_verify()`): certificado abre con la contraseña provista, clave RSA ≥ 2048 bits, vigente por fechas, identificador del emisor coincide (caso de persona natural: RUC termina en `001` y los primeros 10 dígitos coinciden con la identidad del certificado), uso de clave de firma declarado correctamente. `xades.verify()` sobre el XML recién firmado también pasó.
2. **Real, contra `celcer.sri.gob.ec`**, con los datos reales de establecimiento del emisor (RUC 1709053506001, dirección "Los Cardenales Sn y Azulejos", establecimiento 001, punto de emisión 205) y un comprador sintético (para no usar el RUC de ningún tercero real como comprador): **RECIBIDA** en recepción y **AUTORIZADO** en autorización — número de autorización `1709202601170905350600110012050000010011928374610`, fecha `2026-09-17T07:13:54-05:00`. Hubo una advertencia no bloqueante (código 62, "identificación del receptor mal conformada" — el RUC/cédula sintético del comprador no pasa el dígito verificador), que el SRI aceptó como advertencia y autorizó igualmente.

**Esta es la primera autorización real (no simulada) obtenida de punta a punta en este proyecto**, en ambiente PRUEBAS. Confirma que el pendiente de "certificado real" ya no bloquea el canal técnico: firmar, transmitir y obtener una autorización real funcionan con un certificado genuino. Sigue siendo ambiente PRUEBAS, no producción — no tiene efecto tributario ni se declaró como tal ante ningún tercero.

Nunca se registró ni se registrará la clave del `.p12` en el repositorio ni en la evidencia; solo metadatos públicos del certificado (sujeto, emisor, vigencia, huella del archivo).

## Tercer incremento — autoservicio de carga del certificado .p12 para clientes (17-09-2026)

El titular pidió resolver el pendiente que él mismo señaló: hoy solo un administrador con `base.group_system` puede cargar el certificado (`erpec.fiscal.certificate`); en el modelo multi-tenant de OP08, cada cliente es dueño de su propia empresa/base y debe poder subir y reemplazar su propio certificado sin depender de soporte técnico. Pidió tomar como referencia `C:\proyectos web\sinkroniq-mobile` (`backend/src/services/certificados/certificateLifecycleService.js` + `certificadoController.js`, servicio real de carga de Firma Electrónica en producción) y adaptarlo a las especificaciones de Odoo y a lo que este proyecto requiere — investigación de solo lectura, sin modificar sinkroniq-mobile.

**Patrones adoptados de sinkroniq-mobile, adaptados a Odoo (sin copiar código ni depender de Redis/un servicio de firma aparte, que este proyecto no tiene):**

- **Permiso ampliado**: `erpec.fiscal.certificate` y sus campos `p12_file`/`p12_password` (antes `groups='base.group_system'`) ahora también son accesibles para `account.group_account_user` — el usuario contable de la propia empresa del cliente. Cambio de postura deliberado y documentado, igual que ya se documenta para PayPhone (sin cifrado adicional en reposo, protegido solo por permisos). El aislamiento por empresa (`ir.rule` ya existente) sigue vigente: un cliente no puede ver ni tocar el certificado de otra empresa.
- **Vista previa sin persistir** (equivalente a `validarPreview`/`validateCertificatePreview` de sinkroniq, que allá es un endpoint HTTP aparte): en Odoo se resuelve con `@api.onchange('p12_file', 'p12_password')`, que valida en memoria contra `xades.credentials()` y muestra el resultado en el campo `notice` antes de guardar, sin tocar la base de datos.
- **Catálogo de entidades certificadoras reconocidas** (`TRUSTED_CA_PATTERNS`, adaptado de `SRI_AUTHORIZED_CA_PATTERNS`): Security Data, BCE, ANF AC, Uanataca, Datil, Consejo de la Judicatura. No bloquea si la CA no coincide (podría haber CAs legítimas no catalogadas) — solo agrega una advertencia visible en `notice` y el nuevo campo `issuer_trusted`. Verificado con datos reales: el certificado real provisto por el titular (Security Data) sí es reconocido.
- **Prueba de firma real** (`action_test_signature`, equivalente a `probarFirma`/`probeCertificateSignature`): firma un XML sintético mínimo (no un comprobante real, no se transmite al SRI) para confirmar que el certificado puede completar `xades.sign()` de verdad, no solo que `credentials()` abre el archivo — detecta problemas que solo aparecen al firmar un documento completo.
- **Límite de tamaño de archivo** (`MAX_P12_BYTES`, 256 KB, mismo valor que sinkroniq): `@api.constrains('p12_file')`.
- **Límite de intentos de verificación** (antiabuso; sinkroniq usa Redis, este proyecto no lo tiene, así que se guarda en el propio registro, mismo patrón de "intentos" ya usado en `erpec.fiscal.emission`): 5 intentos por ventana de 15 minutos.

**No se portó** el cifrado en reposo del `.p12` (`EncryptionService` de sinkroniq) ni el descifrado/almacenamiento de la clave privada aparte — mantener el mismo nivel de protección ya documentado y aceptado para PayPhone (permisos, no cifrado) en vez de implementar una capa de cifrado parcial que generaría falsa confianza sin un diseño de gestión de claves completo. Tampoco se portó el mapeo de mensajes de error técnico→amigable de sinkroniq: los mensajes que ya produce `xades.py` (p. ej. "El certificado está fuera de vigencia") son suficientemente claros sin necesitar una capa de traducción adicional.

**Verificación**: 9 pruebas nuevas (33 en total en `erpec_fiscal_sri`, 0 fallos/errores) que cubren autoservicio sin `sudo()`, aislamiento por empresa, catálogo de CA confiable/no confiable, límite de tamaño, vista previa sin persistir (`odoo.tests.Form`), límite de intentos, y la prueba de firma. Reinstalado en la demo con respaldo previo (`fiscal-sri-install-20260917-082325`).

**Ensayo real de punta a punta contra la demo ya corriendo (XML-RPC, no solo pruebas aisladas)**: se creó una empresa y un usuario limitado a `account.group_account_user` (sin `base.group_system`), y ese usuario — sin privilegios de administrador — creó, verificó y probó la firma de su propio certificado (sintético, no el certificado real del titular) exclusivamente por su cuenta. Confirma el autoservicio de verdad, no solo en la batería automática. **Quedaron en la demo** una empresa ("Empresa autoservicio ensayo"), un usuario y un certificado sintéticos de este ensayo — no se pueden eliminar por diseño (`perm_unlink=0` en `erpec.fiscal.certificate`, que a su vez bloquea borrar la empresa por `ondelete='restrict'`), documentados aquí como tales, sin efecto de negocio real.

## Pendiente explícito (actualizado)

- ~~Certificado de firma electrónica real~~ — **resuelto en ambiente PRUEBAS el 17-09-2026**: se obtuvo una autorización real con un certificado genuino de Security Data.
- ~~Esquema de carga del .p12 para clientes~~ — **resuelto el 17-09-2026**: autoservicio real (`account.group_account_user`, sin `base.group_system`) verificado contra la demo corriendo.
- Activar ambiente de producción (`cel.sri.gob.ec`) — deliberadamente deshabilitado en el código; ahora hay evidencia de que el canal funciona de punta a punta en pruebas, pero activar producción es una decisión separada que requiere el RUC/certificado real de la empresa emisora en producción, no de un colaborador de pruebas.
- Guarda recíproca en `erpec_fiscal_connector` (bloquear el conector externo si ya existe una emisión nativa) — pendiente de que la sesión concurrente libere ese archivo.
- Consolidar `_gather_native_data()` con la lógica de `action_native_preview` una vez que `erpec_fiscal_native/models.py` esté libre.
- RIDE: sin logo ni QR; sin las secciones de reembolso/nota de crédito/guía de remisión (fuera de alcance de `engine.py` hoy); layout no es pixel-perfect contra la imagen oficial (posiciones aproximadas, no medidas al milímetro desde el PDF).
- Certificado sin cifrado adicional en reposo (mismo nivel que PayPhone, documentado, no resuelto); catálogo de CAs confiables es una lista local, no una verificación de cadena de confianza real contra el repositorio oficial del SRI.
