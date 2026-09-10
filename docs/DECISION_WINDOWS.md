# Windows nativo

Decisión explícita del usuario: instalación nativa en Windows. Odoo se ejecutará con Python aislado y PostgreSQL independiente; no se requiere Docker. No se modificará ni reutilizará una base productiva existente.

El modo Windows de Odoo usa workers=0; el aislamiento será por proceso, rol PostgreSQL, base y directorio de archivos por organización. Puertos locales para validación; publicación en Internet requiere TLS y configuración revisada. No confundir multi-compañía en una base con aislamiento entre clientes.

La disponibilidad, carga concurrente, servicio automático, restauración y generación PDF deben validarse en Windows. No se declara equivalencia operacional con despliegues Linux sin estas pruebas. Docker fue iniciado durante el diagnóstico previo y no es dependencia del plan adaptado.

## Alcance actualizado

Windows se conserva exclusivamente para desarrollo y validación local. El usuario definió producción en Render (Linux/contenedores y PostgreSQL administrado). No se requiere un servidor Windows de producción. La adaptación y las pruebas pendientes se detallan en PRODUCCION_RENDER_CLOUDFLARE.md.
