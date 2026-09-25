# Diagnóstico integral ERP EC — DI26

Corte local: 25-09-2026, America/Guayaquil. Base de código: `ebef509` (DI25 cerrado completo el 24-09-2026).
Alcance pedido por el titular: UI/UX, funcionalidad, regresiones, duplicaciones, incoherencias, mojibake, homologación UTF-8, español de Ecuador y cumplimiento legal. Este diagnóstico no corrige código; sí corrigió dos desfases de esquema en instancias vivas que eran fallas latentes de cambios ya publicados (ver "Acciones operativas").

Evidencia: `docs/evidencias/DI26/` (`validacion.json`, `hallazgos.json`, `recorrido-menus-qa_admin.json`, `recorrido-roles-9.json`, `etiquetas-automaticas-ingles.json`).

## Dictamen

La base técnica está sana en lo que las pruebas miden: 647 pruebas sin fallos (local y CI), 143 menús recorridos sin errores de JavaScript ni diálogos de error, 9 roles sin regresiones visuales ni de accesibilidad frente a DI25-06, UTF-8 íntegro en el repositorio y en las bases.

Los problemas están en lo que las pruebas no miden: desfase de esquema en instancias que leen el repositorio en vivo, un sustento ATS que se sobrescribe solo, identificaciones alteradas en el archivo bancario, décimos sin flujo de pago legal, idioma por defecto en inglés para contactos y sitio público, y **afirmaciones falsas en las evidencias de cierre** (certificado propio, talón del DIMM, ausencia de envío masivo).

Se registran **16 hallazgos: 6 P1 y 10 P2**, más 7 observaciones P3. No se asigna P0.

## Método y límites

- Gobierno verificado antes de empezar (`verify-governance.cjs`: válido, 157 eslabones).
- **Codificación**: los 838 archivos de texto versionados, revisados por UTF-8 válido, BOM, mojibake y fin de línea (índice de git y copia de trabajo). En las bases demo y fundador se revisaron 14 campos de texto por mojibake, junto con idiomas, zonas horarias y valores por defecto.
- **Español**: análisis estático de etiquetas, vistas, ayudas y mensajes de los módulos propios (inglés, tildes), y consulta de las etiquetas efectivas de 1.049 campos propios en la base.
- **UI/UX**: recorrido automático de los 143 menús con acción como `qa_admin` en Chrome (errores JS, diálogos de error, mojibake en pantalla, encabezados en inglés); repetición de la batería de 9 roles de DI25-06 (anchos 360/768/1280, zoom 200 %, teclado, axe-core WCAG 2.x A/AA); sitio público como visitante anónimo. Los usuarios QA se reactivaron solo para la prueba.
- **Regresiones y esquema**: registro de Odoo cargado con el código actual contra cada base (fundador, demo, a, b) para listar campos sin columna; historial de versiones de los 25 módulos propios.
- **Reproducciones**: sustento ATS sobre una copia aislada y desechable de la demo; función de identificación bancaria real.
- **Legal**: contraste con fuentes primarias ya incorporadas al proyecto (LORTI Art. 9, catálogo RDEP, Reglamento de Comprobantes Art. 41) y fuentes oficiales nuevas para los décimos (Ministerio de Economía y Finanzas, Ministerio del Trabajo).
- **Límites**: sin pentest, carga ni lector de pantalla; el recorrido menú a menú fue con un rol. El artículo de la LOPDP sobre información al recoger datos no se verificó contra el texto primario. La aplicabilidad de NAC-DGERCGC26-00000027 al modelo SaaS no se dictaminó. No se enviaron comprobantes, correos, transferencias ni declaraciones, y no se modificaron repositorios fuente.

## Resultados sin hallazgo

- Suite integrada: 647 pruebas, 0 fallos, 0 errores, 12 omisiones (local y CI [36078558267](https://github.com/SINKRONET-SAS/erp-ec/actions/runs/36078558267)).
- UTF-8: 838 de 838 archivos válidos. En el índice de git todo es LF, salvo 3 archivos oficiales conservados byte a byte a propósito. Bases en UTF8 sin mojibake.
- Ninguna cadena escrita en inglés en etiquetas, vistas o mensajes de error propios (el problema de inglés es de etiquetas automáticas, ver DI26-08).
- Menús: 143 recorridos, 0 errores de JavaScript, 0 diálogos de error, 0 mojibake en pantalla.
- Roles: 9 usuarios × 4 anchos sin desbordes, sin errores JS, 0 violaciones axe-core, foco visible, mismas áreas por rol que en DI25-06; el cambio de empresa funciona.
- Traducciones del núcleo de Odoo en es_EC presentes ("Ajustes", "Facturación", "Empleados", "Contactos"). Los menús propios están escritos en español como texto fuente.

## Acciones operativas de esta ejecución

| Instancia | Problema encontrado | Acción | Respaldo previo |
|---|---|---|---|
| fundador (8199) | El proceso arrancó hoy con el código nuevo, pero la base no tenía `res_partner_bank.erpec_bank_key/erpec_account_type`, las tablas de exportación bancaria ni la referencia RDEP: cualquier pantalla que lea cuentas bancarias iba a fallar como el RPC_ERROR del 23-09 | `-u erpec_treasury,erpec_payroll,erpec_data_protection`; recarga del registro por señalización | `fundador-sync-bancaria-rdep-20260925T152909Z` |
| b (piloto) | Faltaban `erpec.plan.published`, `currency_id` y `price` (`erpec_suite`) | `-u erpec_suite` | `tenant-b-drift-erpec-suite-20260925T165609Z` |
| demo (8369) | Copia atrasada del código (sin exportación bancaria ni referencia RDEP) | Sincronización completa y reinicio | `diag-sync-demo-20260925T153031Z` |

Tras las acciones, el desfase es 0 en las cuatro instancias. La causa raíz sigue abierta (DI26-01).

## Hallazgos

| ID | Prior. | Tema | Hallazgo |
|---|---|---|---|
| DI26-01 | P1 | Regresión / operación | Desfase de esquema recurrente en instancias que leen el repositorio en vivo |
| DI26-02 | P1 | Integridad fiscal | El sustento ATS corregido a mano se sobrescribe al leer un campo informativo |
| DI26-03 | P1 | Integridad de pagos | El archivo bancario borra las letras de los pasaportes y clasifica la identificación por longitud |
| DI26-04 | P1 | Legal / incoherencia | Email Marketing instalado en la demo sin conexión con la exclusión comercial; el cierre afirmaba que no existía |
| DI26-05 | P1 | Legal laboral | Décimo tercero y cuarto sin flujo de pago ni periodos legales por región |
| DI26-06 | P1 | Legal fiscal | RUC del proveedor del sistema en la información adicional (NAC-DGERCGC26-00000027) sigue sin implementarse |
| DI26-07 | P2 | Español de Ecuador | Contactos, empresas y sitio público en inglés por defecto; empresas sin zona horaria |
| DI26-08 | P2 | Español de Ecuador | 220 de 1.049 campos propios muestran etiquetas automáticas en inglés |
| DI26-09 | P2 | Incoherencia UI | Avisos falsos en pantalla: factura y RDEP contradicen lo que el sistema ya hace |
| DI26-10 | P2 | Incoherencia documental | Evidencias de cierre DI25 con afirmaciones falsas |
| DI26-11 | P2 | Duplicación | Datos y accesos duplicados (cuentas bancarias, banco, retenciones, ingresos no gravados, tipo de identificación) |
| DI26-12 | P2 | Integridad de datos de ensayo | La empresa ficticia de la demo usa el RUC real de SINKRONET |
| DI26-13 | P2 | Fiabilidad de validación | Pruebas y procedimientos críticos que nunca corren en CI ni viven en el repositorio |
| DI26-14 | P2 | Accesibilidad | Alertas sin `role` en vistas propias; sitio con `lang="en-US"` sobre contenido en español |
| DI26-15 | P2 | Legal privacidad | El formulario público de derechos no identifica al responsable ni la finalidad (probable) |
| DI26-16 | P2 | UX / superficie | La demo tiene 184 módulos (CRM, flota, chat, blog, foro, gamificación, email marketing) que no representan el producto |

### DI26-01 — Desfase de esquema recurrente (P1)

14 de los 25 módulos propios cambiaron modelos después de su última subida de versión. Por ejemplo, `erpec_treasury` sigue en 18.0.1.0.0 con tres modelos nuevos, y `erpec_payroll` sigue en 18.0.1.14.13 con un campo nuevo. Fundador, a y b leen `addons/` del repositorio en vivo, y `scripts/manage-odoo.py update()` solo actualiza `erpec_base`. Resultado: basta un reinicio para que el código espere columnas que la base no tiene. Ya pasó dos veces: el RPC_ERROR del 23-09 y el desfase de hoy en fundador y b, corregidos con respaldo. **Siguiente acción:** subir versión con cada cambio de modelos, actualizar todos los módulos instalados de cada instancia y comprobar el desfase automáticamente (el método de `validacion.json` sirve de base).

### DI26-02 — Sustento ATS sobrescrito (P1)

`addons/erpec_workspace/tax_intersection.py:202-223` calcula en un mismo método el sustento ATS almacenado y editable (`erpec_ats_sustento_code`) y dos avisos no almacenados. Odoo lo advierte en el registro: "inconsistent 'store' for computed fields, accessing erpec_tax_notice… may recompute and update". Reproducido en una copia de la demo: el sustento se fijó a mano en "01" y, con solo leer el aviso, volvió a "02" (el del plan) y quedó guardado. El método no revisa el estado del documento. No se pudo repetir sobre una factura contabilizada porque la demo no tiene una cuyo plan resuelva sustento. **Siguiente acción:** separar el cálculo del campo almacenado y no pisar un valor manual.

### DI26-03 — Identificación alterada en el archivo bancario (P1)

`erpec_treasury/bank_export.py::_split_identification` conserva solo dígitos y deduce el tipo por longitud. Probado con la función real: `PX39582` → `39582`, `A1234567` → `1234567`, y un pasaporte de 10 dígitos saldría como cédula. Además ignora el tipo de identificación que ya existe en el empleado. Un archivo con identificaciones alteradas lo rechaza el banco o, peor, no coincide con el titular. **Siguiente acción:** tomar el tipo declarado y conservar el pasaporte tal cual, rechazando lo que no cumpla la ficha de cada banco.

### DI26-04 — Envío masivo sin exclusión conectada (P1)

La demo tiene instalado `mass_mailing` (Email Marketing) y módulos relacionados. La exclusión propia `ec_marketing_email_opt_out` no está conectada con la lista negra de ese módulo (0 registros en `mail_blacklist`; ningún código propio la usa). DI25-05.2 y la tabla de DI25-07 afirmaban "no existe mecanismo de envío masivo". Hoy no se envía nada porque no hay servidor de correo configurado. Pero el primer inquilino que configure uno y use Email Marketing no respetará la exclusión (oposición, LOPDP; mensajes periódicos, Ley de Comercio Electrónico). **Siguiente acción:** sincronizar la exclusión con la lista negra o impedir Email Marketing, y corregir las evidencias.

### DI26-05 — Décimos sin pago ni periodos legales (P1)

El motor causa el décimo tercero y el cuarto cada mes (`engine.py:363-377`) y los lleva a pasivo, pero no existe flujo para pagarlos o liquidarlos, y la "Ficha de beneficios acumulados" agrupa por año calendario. Según fuentes oficiales (Ministerio de Economía y Finanzas, instructivos Sierra 2025 y Costa 2026; calculadora del Ministerio del Trabajo; Código del Trabajo arts. 111 y 113):
- **Décimo cuarto, Sierra y Amazonía:** periodo del 1 de agosto al 31 de julio, pago hasta el 15 de agosto.
- **Décimo cuarto, Costa e Insular:** periodo del 1 de marzo al fin de febrero, pago hasta el 15 de marzo.
- **Décimo tercero:** pago hasta el 24 de diciembre.

El ERP no registra el régimen regional ni el periodo del décimo tercero. **Siguiente acción:** régimen por empleado o establecimiento, cortes por periodo legal y preparación de pago análoga a `erpec.payroll.disbursement`.

### DI26-06 — RUC del proveedor del sistema (P1)

La propia UI lo declara pendiente en la vista previa y en el conector (`erpec_fiscal_native/models.py:34`, `erpec_fiscal_connector/connector.py:394`). Si SINKRONET, como SaaS, es proveedor del sistema de facturación de sus clientes, la resolución exigiría su RUC en la información adicional de cada comprobante. La aplicabilidad no se dictaminó. **Siguiente acción:** confirmar aplicabilidad con el responsable tributario e implementarlo en la emisión nativa.

### DI26-07 — Inglés por defecto y zona horaria (P2)

- **Contactos:** en demo y fundador, `ir_default` fija `res.partner.lang = en_US`; solo 10 de 45 contactos de la demo y 1 de 5 en fundador están en es_EC.
- **Empresas:** las tres revisadas están en inglés y sin zona horaria. El aprovisionamiento (`scripts/provision-worker.py:129-131`, `scripts/manage-odoo.py`) solo ajusta al administrador.
- **Sitio público de la demo:** el idioma por defecto es en_US. `/` y `/derechos-datos` muestran "Contact Us", "Home", "Shop" y "Sign in"; la página de derechos declara `lang="en-US"` con contenido en español.
- **Usuario de prueba:** `selfservice_test_2` sigue activo, en inglés y sin zona horaria.

### DI26-08 — Etiquetas automáticas en inglés (P2)

220 de 1.049 campos propios no tienen etiqueta en español y Odoo muestra la que deriva del nombre técnico, por ejemplo "Company", "Name", "Total Amount", "Result Tax" o "Accuracy Meters". Por módulo:

| Módulo | Campos |
|---|---|
| ATS | 55 |
| Rutas y visitas | 49 |
| Nómina | 30 |
| Tesorería (incluida la exportación bancaria de ayer) | 26 |
| Retenciones | 14 |
| SRI | 13 |
| Protección de datos | 11 |
| Otros | 22 |

El recorrido lo vio en 11 pantallas. Detalle en `etiquetas-automaticas-ingles.json`.

### DI26-09 — Avisos falsos en pantalla (P2)

- En la factura, la pestaña "Facturación local" dice "Falta implementar y validar firma XAdES, envío/consulta SRI, RIDE autorizado…". La pestaña contigua "Firma y transmisión SRI" firma y transmite, y fundador tiene 4 autorizaciones reales en el ambiente de pruebas.
- El agregador RDEP muestra "D5 · Compatibilidad RDEP 2026 pendiente: … ficha y catálogo visibles para 2025" (`annex_rdep.py:406`), aunque el catálogo 2026 está en el DIMM y el XML pasa su validador.

### DI26-10 — Evidencias de cierre con afirmaciones falsas (P2)

- **Certificado y ventas ATS:** DI25-07 y su aceptación dicen "sin certificado propio de la empresa emisora cargado" y "ventas ATS sin emisión autorizada". Pero fundador tiene el certificado de persona jurídica de SINKRONET S.A.S. (ANF, CA reconocida, firma probada, vigente hasta 2029-03-10) y 4 comprobantes autorizados en pruebas. Lo que falta para producción es la decisión del titular y habilitar el punto de emisión.
- **Talón y ventas en DI25-04:** `DI25-04-cierre.json`, `.github/CODEX_CONTEXT.md` y `estado-hallazgos.json` siguen diciendo que DI25-04.3 está bloqueado por el SWT de 32 bits y por falta de certificado. El titular ya generó el talón en el DIMM y los datos de ventas existen en fundador.
- **Envío masivo:** DI25-05.2 y DI25-07 afirman que no existe (ver DI26-04).

### DI26-11 — Duplicaciones (P2)

- **Cuentas de la empresa:** la exportación bancaria guarda la cuenta propia en `erpec.bank.company.account`, aparte de la cuenta ya ligada al diario bancario. `erpec_bank_key` repite lo que expresa `res.bank`.
- **Retenciones:** la misma acción está en dos aplicaciones raíz ("ERP EC › Retenciones contables" y "Contabilidad ERP EC › Retenciones").
- **Ingresos no gravados:** entran por dos vías, el campo directo de la línea y los beneficios marcados sin renta.
- **Tipo de identificación:** hay dos derivaciones, RDEP (C/P/E) y banco (C/R/P por longitud), que pueden contradecirse.

### DI26-12 — RUC real en datos de ensayo (P2)

"Empresa autoservicio ensayo" (demo) usa el RUC 1793235327001, que es el de SINKRONET S.A.S. en fundador. El XML ATS y el talón del DIMM de ensayo llevan ese RUC real con compras ficticias. Presentarlos por error sería una declaración falsa a nombre de SINKRONET. **Siguiente acción:** usar un RUC de ensayo inequívoco o bloquear la exportación desde la demo.

### DI26-13 — Validación fuera de CI y del repositorio (P2)

- **Pruebas omitidas:** las 12 omisiones del CI son siempre las mismas (Tesorería y exportación bancaria), así que esas rutas nunca se validan de forma continua; solo se ejecutaron sobre copias locales sembradas.
- **UI fuera de CI:** el recorrido de UI, axe-core y roles no corre en CI.
- **Scripts fuera del repositorio:** los scripts de sellado del AuditLock, de despliegue en demo y fundador y de las pruebas de UI viven en un directorio temporal, no en el repositorio, así que no son reproducibles por otra persona.

### DI26-14 — Accesibilidad (P2)

Al actualizar, Odoo advierte "An alert (class alert-*) must have an alert, alertdialog or status role" en vistas propias: ATS, conector, vista previa, nómina (2), suite y otras. El sitio declara `lang="en-US"` sobre contenido en español, así que un lector de pantalla lo pronunciaría en inglés.

### DI26-15 — Transparencia del formulario de derechos (P2, probable)

`/derechos-datos` recoge nombre, identificación y correo, pero no indica quién es el responsable del tratamiento (razón social, RUC, contacto), para qué se usan esos datos, su base legal ni cuánto se conservan. La política de privacidad del sitio ya estaba excluida en DI25-07. Queda pendiente verificar el artículo aplicable de la LOPDP contra el texto primario.

### DI26-16 — Superficie de la demo (P2)

La demo tiene 184 módulos instalados, entre ellos CRM, flota, chat en vivo, blog, foro, gamificación y Email Marketing. Un inquilino aprovisionado recibe `base, l10n_ec, erpec_base, erpec_payroll, erpec_field_routes` y fundador tiene 105 módulos. La demo muestra menús y capacidades que el producto no ofrece y agrega superficie legal (DI26-04).

## Observaciones P3

1. Mojibake en 5 mensajes de `scripts/install-fiscal.py` ("Ã¡" en lugar de "á") y en un comentario del XSD oficial de retención (tal como está en el archivo; no afecta la validación).
2. Sin tilde: nombre del PDF "Resumen de nomina" (`erpec_payroll/reports.xml`) y "convenio de debito" (`retention_reference_data.xml`).
3. 52 archivos con CRLF solo en la copia de trabajo de Windows; el repositorio está homologado.
4. `docs/evidencias/AuditLock.before-CF01.json` sin versionar y excluido a mano en cada commit.
5. 152 instantáneas completas del AuditLock (5,2 MB) y creciendo; el AuditLock ya pesa 97 KB.
6. El registro advierte que `account.move.line` tiene `compute_sudo` inconsistente en los mismos campos de DI26-02.
7. En la demo, entrar a "Website › Métodos de pago" mostró "Su sesión de Odoo expiró"; no se reprodujo en pantallas del ERP.

## Propuesta de fases (no desplegada)

| Fase | Hallazgos | Dependencia |
|---|---|---|
| DI26-A Operación y esquema | DI26-01, DI26-13 (scripts al repositorio y comprobación de desfase) | — |
| DI26-B Integridad fiscal y de pagos | DI26-02, DI26-03, DI26-12, DI26-11 (identificación y cuentas) | DI26-A |
| DI26-C Nómina: décimos | DI26-05 | DI26-A |
| DI26-D Legal y privacidad | DI26-04, DI26-06, DI26-15 | DI26-A |
| DI26-E Español de Ecuador, UI y accesibilidad | DI26-07, DI26-08, DI26-09, DI26-14, DI26-16, P3 | DI26-A |
| DI26-F Coherencia documental | DI26-10, DI26-11 (menús e ingresos) | DI26-B a E |

Desplegar el Plan Haiky y los prompts de estas fases requiere la autorización del titular.

## Relación con diagnósticos anteriores

DI25 queda cerrado y aceptado; este diagnóstico no lo reabre. DI26-09 y DI26-10 corrigen afirmaciones que el propio cierre de DI25 dejó escritas; varias las escribí yo durante la re-auditoría del 24-09 revisando solo la demo y no fundador. DI26-01 es la causa del RPC_ERROR reportado por el titular el 23-09.
