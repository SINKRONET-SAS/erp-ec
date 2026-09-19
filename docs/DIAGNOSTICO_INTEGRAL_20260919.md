# Diagnóstico integral — ERP EC (19-09-2026)

Alcance: repositorio, código, pruebas, instancias en ejecución, seguridad, datos, higiene del entorno y gobierno. Método: inspección de solo lectura, una suite completa aislada de los 22 módulos (420 pruebas) y sondas en las instancias reales con reversión de transacción. Las correcciones aplicadas durante el diagnóstico se indican como tales.

## 1. Resumen ejecutivo
| Área | Estado |
|---|---|
| Repositorio | Rama `codex/erpec26-implementacion` sincronizada con el remoto al iniciar (78 commits). Las correcciones de este diagnóstico se registran en el commit OP20. Cadena de hashes del AuditLock válida. |
| Código | 22 módulos, 185 archivos Python y 49 XML sin errores de sintaxis; dependencias resolubles y sin ciclos. |
| Servicios | PostgreSQL, Fundador (8199), demo (8369), piloto A (8169) y B (8170) responden 200; 0 errores en el log del Fundador en 24 h. |
| Pruebas | Las suites por módulo pasan; **la suite completa integrada tenía 32 errores**, uno de ellos un **defecto de producto grave (corregido)**. Tras las correcciones: 1 error abierto y 5 pruebas omitidas de forma explícita. |
| Seguridad | Sin secretos versionados; secretos de aplicación cifrados y rotables. Hallazgos: respaldos antiguos, un certificado ajeno en claro, dependencias antiguas, servidor sin endurecer. |
| Gobierno | Cadena íntegra, pero los "pendientes" del AuditLock son una lista de ~86 entradas que solo crece y faltan los prompts de fase OP14–OP19. Abierto (sección 7). |

## 2. Defectos funcionales
### D1 — CRÍTICO, corregido: con `erpec_payroll` instalado no se podía crear una nota de crédito, una nota de débito ni duplicar una factura
- Causa: `PayrollMove.create` rechazaba cualquier creación cuyo diccionario **contuviera la clave** `erpec_payroll_id`, aunque valiera `False`, y `copy()` la incluye siempre porque el campo tenía `copy=True`.
- Impacto: demo y Fundador (ambos con nómina) no podían emitir notas de crédito/débito desde la pantalla; mis pruebas de esos flujos corrían sin nómina instalada y por eso no lo detectaron. La emisión al SRI de esas notas estaba bien; lo que fallaba era **crearlas**.
- Corrección: la guarda solo bloquea valores reales (`values.get(...)`) y los dos vínculos pasan a `copy=False`. Prueba de regresión `test_move_copy.py` (revertir y duplicar funcionan; el vínculo directo sigue protegido). Verificado en la demo real con reversión: la nota de crédito nativa se crea con tipo documental 04 y duplicar funciona. Instancias reiniciadas.
- Lección: falta una suite que instale **todos** los módulos juntos (ver D3).

### D2 — Pruebas acopladas al estado o a datos sembrados (corregido en su mayoría)
- 18 pruebas (`erpec_fiscal_connector`, `erpec_fiscal_documents`, `erpec_withholding_accounting`) presuponían que la empresa por defecto era de Ecuador. Corregido en sus fixtures.
- 5 pruebas de `erpec_treasury` dependen de datos que solo crea `scripts/seed-operational-demo.py`. Ahora se **omiten de forma explícita** en una base limpia (se ejecutan con la demo sembrada).
- 1 prueba de `erpec_fiscal_connector` (`test_company_isolation_and_secret_access`) sigue fallando en la instalación completa: `workspace.fiscal_scope` llega vacío. Abierto: acoplada al conjunto de módulos instalados, sin impacto funcional conocido.

### D3 — No existe una suite integrada ni CI
Cada módulo se probó aislado; la combinación completa nunca se ejecutaba. Recomendado: ejecutar `-i <todos los erpec_*>` con todas las pruebas antes de cada cierre de fase (el runner de este diagnóstico sirve de base).

## 3. Seguridad
| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| S1 | El Fundador no tenía `admin_passwd` (contraseña maestra de Odoo por defecto). | Alta | **Corregido**: clave aleatoria en `odoo.conf`; verificado que el valor por defecto ya no permite volcar la base. |
| S2 | 98 carpetas de respaldo (4.8 GB, 92 volcados, desde 09-09) anteriores al cifrado: pueden contener certificados y tokens en claro. | Alta | Abierto: purgar o cifrar los que no se necesiten. |
| S3 | `.cache/private/fiscal-pruebas` guarda el `.p12` y la contraseña (`clave.txt`) de **otra persona** en claro (fuera de git). | Media | Abierto: eliminar ahora que SINKRONET tiene certificado propio, o moverlo al almacén cifrado. |
| S4 | Dependencias de versión antigua (cryptography 42.0.8, Werkzeug 3.0.1, requests 2.31.0, urllib3 2.0.7, Jinja2 3.1.2, Pillow 10.2.0, lxml 5.2.1). Varias tienen avisos de seguridad publicados en versiones posteriores; **no se pasó un escáner** (sin `pip-audit`). | Media | Abierto: actualizar dentro de lo compatible con Odoo 18 y ejecutar `pip-audit` antes de producción. |
| S5 | Servidores en modo desarrollo (`workers=0`, sin HTTPS ni `proxy_mode`), solo escuchan en 127.0.0.1. `ERPEC_SECRET_KEY` sin definir en un despliegue real. | Media (producción) | Abierto: endurecimiento de despliegue. |
| S6 | Archivos versionados: ningún secreto, `.gitignore` cubre `.cache`, `.env`, `*.p12`, `*.key`. Columnas sensibles en las 4 instancias: solo valores cifrados. | — | Correcto. |

## 4. Instancias y datos
- **Fundador** (SINKRONET S.A.S.): 20 módulos erpec, 25 crons al día, certificado verificado (vence en 903 días), régimen general, perfil ordinario confirmado, punto 001-004 en pruebas. **Ninguna emisión SRI registrada desde la aplicación**: todas las autorizaciones reales se hicieron con scripts externos y el certificado de otra persona. Falta el ensayo de extremo a extremo con el certificado propio dentro de la aplicación. 1 factura en borrador; el diario `INV` 001-001 por defecto queda sin uso (la auditoría lo señala).
- **Demo**: sana; los crons "atrasados" se debían a que el servidor estuvo detenido. Empresa 2 sin establecimiento ni dirección (auditoría lo señala).
- **Pilotos A y B**: responden; A tiene su token PayPhone cifrado.
- **Correo saliente**: sin servidor SMTP configurado; 7 correos en excepción en el Fundador y 2 en la demo.
- **Continuidad**: PostgreSQL y los servidores se detuvieron varias veces durante la jornada y hubo que levantarlos a mano; no hay supervisor (servicio de Windows o tarea programada).

## 5. Higiene del entorno
- 42 bases en el clúster local (2.5 GB): 4 instancias reales y 37 de pruebas residuales (`ec_recovery_*`, `ec_operational_*`, `erp_*`, `ec_withholding_accounting_*`, `ec_fiscal_documents_*`, `ec_fiscal_connector_*`, `restore_*`, otras) más el rol `erp_tenants`. `.cache` ocupa 9.3 GB (respaldos 4.8 GB). Disco: 286 GB libres.
- Se eliminaron antes las 6 bases `erpec_pp_test_*`. Las demás familias no se han tocado.

## 6. Cobertura fiscal (solo ambiente PRUEBAS)
Factura (incluye IVA no objeto/exento y reembolsos), nota de crédito, nota de débito, retención, guía de remisión y liquidación de compra: XML validado contra XSD, firmado XAdES y **autorizado en celcer**. Producción: endpoint disponible pero **nunca ejercitado**; habilitación solo por un responsable contable con certificado reconocido. RIDE sin contraste con un ejemplo oficial por tipo. Catálogo de tarifas de renta de fuente secundaria (Odoo); el SRI es la autoridad.

## 7. Gobierno y calidad
- AuditLock: cadena válida, pero `pendingChecks` acumula unas 86 entradas que solo crecen (varias ya resueltas) y `phaseCompleted` sigue en `ERPEC26-03`. Abierto: curar la lista contra la sección 8.
- Faltan los prompts de fase OP14–OP19 en `.github/prompts` (los planes y evidencias sí existen). Abierto.
- Versiones de manifiesto sin subir tras cambios recientes (`erpec_fiscal_native`, `erpec_fiscal_withholding_sri`, `erpec_fiscal_guide_sri`, `erpec_payroll`). Abierto.
- Cobertura de pruebas baja en `erpec_provision` (4), `erpec_operations` (5), y ninguna en `erpec_base` y `erpec_runtime`.

## 8. Pendientes vigentes, por prioridad
1. **Ensayo de extremo a extremo en la aplicación del Fundador** con el certificado propio (factura → firma → SRI pruebas → RIDE), antes de hablar de producción.
2. Purgar o cifrar respaldos anteriores al 19-09 (S2) y eliminar el certificado ajeno en claro (S3).
3. Definir `ERPEC_SECRET_KEY` en el despliegue, respaldar las claves aparte y retirar las anteriores tras un periodo de confianza.
4. Actualizar dependencias y pasar `pip-audit`; endurecer el despliegue (workers, HTTPS, proxy, supervisor de servicios).
5. Suite integrada con todos los módulos como paso obligatorio; resolver la prueba abierta del conector y sembrar los datos de tesorería.
6. Configurar el correo saliente (`EMAIL_*`).
7. Primer envío real a producción, supervisado por el cliente (runbook).
8. RIDE contra ejemplos oficiales; puntos de emisión permitidos por usuario; establecimiento de la empresa 2.
9. Limpieza de las 37 bases de prueba residuales y del rol `erp_tenants`.
10. Elevar la cobertura de pruebas en `erpec_provision`, `erpec_operations`, `erpec_base` y `erpec_runtime`.
