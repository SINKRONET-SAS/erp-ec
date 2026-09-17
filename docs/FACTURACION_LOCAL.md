# Facturación electrónica local — primer incremento

El titular autorizó aplicar a facturación el mismo criterio de trasladar lógica propia al ERP utilizado en nómina. Se conserva el producto Facturador y su API; no se modifica su repositorio ni se migra un emisor existente. La generación local evita arrancar el servicio Facturador para preparar un XML. La autorización tributaria sigue correspondiendo al SRI.

## Disponible en la demo

http://127.0.0.1:8369/odoo/action-581 → Facturación electrónica → Facturas — preparación local. Abrir una factura contabilizada y su pestaña Facturación local. La acción valida y descarga una vista previa XML sin firma, con clave de acceso, SHA256, detalle, descuentos por cantidad, IVA y total. Repetir con los mismos datos produce el mismo XML; no crea trabajo de envío ni reserva otro secuencial. El número proviene de la factura contable existente; esto no constituye todavía un administrador de secuencias para emisión electrónica.

La demo conserva RUC vacío. No se inventan RUC, establecimientos, certificados ni atributos fiscales. En Empresa → Facturación local se debe declarar, a partir del RUC real, la obligación contable y confirmar que el perfil es ordinario sin atributos especiales. La vista previa muestra los faltantes y rechaza perfiles sin revisar. Este incremento admite factura ordinaria USD con comprador identificado por RUC o cédula, IVA 0 o 15 por línea, sin impuestos incluidos ni compuestos. No determina automáticamente la tarifa legal del producto; toma y contrasta los impuestos configurados en la factura.

El estado es VISTA PREVIA SIN FIRMA. No transmite, firma, autoriza ni entrega documentos a terceros. Las vistas previas son transitorias y no sustituyen el archivo fiscal durable. Una factura ya asignada al Facturador no se prepara localmente.

## Evidencia ejecutada

14 pruebas Odoo en copia aislada: nueve del conector existente y cinco del nuevo módulo. Incluyen XML validado contra XSD 2.1.0, subtotal 180, descuento 20, IVA 27 y total 207; escape XML, repetición, acceso por empresa, rechazo de RUC ausente, perfil no revisado y tarifa incompatible; conservación de la asignación externa. El RUC y las operaciones de estos ensayos son ficticios y se revierten al terminar las pruebas, no se siembran en la demo.

258 casos de módulo 11 coinciden con la función pura del Facturador, con hash de la fuente conservado. Este contraste no acredita equivalencia integral de XML, redondeos, firma, estados o emisión. scripts/verify-fiscal-native.py reproduce los ensayos en la copia operativa existente; scripts/verify-fiscal-native-equivalence.cjs reproduce el contraste sin arrancar servicios externos.

Instalación con respaldo previo de base, filestore y complementos mediante scripts/install-fiscal-native-demo.py. La autenticación y compilación de formularios se verificaron; la aceptación visual no se completó porque el control del navegador agotó su espera tras login. Servicios 8369, 8169, 8170 y 8186 respondieron con versión Odoo 18.0. Evidencia: evidencias/ERPEC26-FISCAL-NATIVO.json.

## Fuente y procedencia

Consulta oficial: 11-09-2026. [SRI — Facturación electrónica](https://www.sri.gob.ec/facturacion-electronica) publica la ficha técnica 2.34, actualizada a julio 2026, y el paquete XML/XSD de factura. La estructura de clave de 49 dígitos y módulo 11 se contrastó con esa ficha. El XML de factura 2.1.0 se valida estructuralmente; no se anuncia cobertura completa de todos los requisitos de la ficha 2.34.

El esquema factura_V2.1.0.xsd procede del ZIP oficial https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/05546998-6f29-4870-be3b-62650f312a6c/XML%20y%20XSD%20Factura.zip. El esquema XMLDSig se toma de la copia pública W3C conservada en el Facturador; mantiene su copyright y referencia a W3C Software License. Los esquemas conservan su procedencia y licencias; la licencia del módulo propio no los relicencia. Se normalizaron saltos de línea a LF.

## Siguiente implementación obligatoria

1. Gestión durable de autoridad y secuencias por emisor, establecimiento, punto y ambiente; congelación/versionado del XML que se emita. La clave determinista actual solo sirve para vista previa.
2. Firma XAdES con certificado real protegido; validar certificado, titular, vigencia, cadena, algoritmo y equivalencia. No trasladar secretos desde otro producto sin un flujo explícito de configuración.
3. Outbox local, recepción/consulta SRI en pruebas, reintentos, reinicio, respuestas fuera de orden y conciliación; conservar XML enviado y respuesta original. Un XML válido o recibido no equivale a autorización.
4. RIDE y archivo durables vinculados a autorización verificada. Incluir perfiles especiales, documentos adicionales y revisión de tarifas antes de declararlos soportados.
5. Ensayo con emisor real autorizado para pruebas y corte controlado si elige migrar. La preparación no cierra ERPEC26-05 ni sustituye firma o validación externa.

## Revisión de producción — septiembre de 2026

La Resolución SRI NAC-DGERCGC26-00000027 exige que los proveedores de sistemas o servicios de facturación electrónica registren esa actividad y que el emisor que usa un proveedor tercero incluya el RUC del proveedor en la información adicional del comprobante, dentro de los plazos de la resolución. El XML local y el contrato del conector todavía no transportan ese dato; por ello la producción queda bloqueada aunque el XSD básico, la firma aislada o el transporte lleguen a funcionar. El pendiente se muestra también en la factura y en el centro de trabajo.

La impresión PDF nativa de Odoo sigue disponible como reporte contable, pero no es un RIDE vinculado a una autorización del SRI. No debe entregarse como comprobante electrónico autorizado.

## Reversión

No se migran facturas ni se cambian secuencias. El respaldo anterior está indicado en la evidencia de instalación. Antes de retirar módulos, detener la demo y conservar también su estado actual. Recuperar database.dump junto con filestore y addons del mismo respaldo en una base nueva con rol propio; validar y cambiar a esa copia de manera controlada. No sobrescribir una demo que haya recibido nuevas operaciones. La recuperación de este respaldo específico aún no se ha ensayado; no utilizar sin adaptar el verificador antiguo que supone ausencia de nómina.
