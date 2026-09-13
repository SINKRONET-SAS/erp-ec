# SP02 — Experiencia coordinada y aceptación operativa

Revisión del 11-09-2026. Prioridad autorizada: que el ERP tenga una experiencia propia y coherente, conservando los procesos de Odoo Community. Esta revisión no cierra los requisitos fiscales, laborales ni bancarios.

## Hallazgos comprobados en pantalla

| Hallazgo | Impacto | Corrección |
|---|---|---|
| Acceso con logotipo genérico, textos en inglés y formulario inicialmente oculto | Dificulta reconocer el producto e ingresar | Identidad ERP EC / SINKRONET, formulario visible en español y autenticación nativa |
| Inicio del operario y supervisor solicita permiso de administración | Bloquea el primer acceso aunque el perfil puede leer el inicio | Autorizar la acción de lectura al grupo interno; conservar prohibición de escritura y acceso a áreas no concedidas |
| Identidad y menú cambian entre módulos | Desorienta al pasar de un proceso a otro | Botón de regreso persistente, menú Áreas filtrado por permisos y cabecera común |
| Pausa del operario sin correo falla al registrar la nota | Impide detener el trabajo | Nota interna sin notificaciones, con comprobación explícita de permiso de escritura |
| Después de pausar desaparece el control para continuar | La operación queda bloqueada desde la interfaz | Reanudación visible para la pausa propia, manteniendo el control nativo de bloqueos de mantenimiento |

La señal de pausa se calcula desde los intervalos existentes y el usuario actual. No es otro estado de fabricación. Reanudar cierra la pausa propia antes de llamar al inicio nativo; no levanta bloqueos ajenos ni omite dependencias entre operaciones.

## Escenarios y límites de la evidencia

Los recorridos utilizan una copia aislada de la demo, cinco perfiles con permisos nativos, dos etapas dependientes de fabricación y un expediente de importación con dos productos. Los movimientos, empleados, productos y precios son ficticios identificados como aceptación. No se ejecutan correos, transferencias bancarias ni emisiones al SRI.

La copia conserva los parámetros laborales reales de 2026. Para importación se preparó la referencia del Banco Central Europeo del 11-09-2026: 1 EUR = 1,1592 USD. Es referencia de demostración, no cotización bancaria ni tipo de cambio de una transacción real. Fuente: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.es.html.

Las tasas artificiales de las pruebas automatizadas se cambian únicamente dentro de transacciones con reversión. Los ensayos de Tesorería eligen un mes libre y no reescriben los cierres existentes. El script de preparación visual no confirma compras, fabrica, publica facturas ni distribuye gastos.

Los archivos privados de la copia y las capturas permanecen en `.cache/`; no contienen evidencia de aceptación fiscal ni homologación. La evidencia final de este incremento debe distinguir las transiciones realizadas en pantalla, las comprobaciones automatizadas y lo que permanece abierto.
