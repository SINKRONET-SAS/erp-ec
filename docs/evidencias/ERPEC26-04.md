# ERPEC26-04 — Avance local, sin cierre de fase

Implementados cola durable, reservas, reintentos, estados visibles, trabajador Windows y ensayo real de creación/suspensión/reactivación. Siete pruebas transaccionales de contratos y cola aprobadas, más ejecución real por API y procesos separados. Resultado detallado: ERPEC26-04-validacion.json (passed-local; phaseComplete false).

La prueba real detectó respuestas vacías incompatibles con XML-RPC en suspensión/reactivación; se corrigieron para devolver True. Se añadieron comprobaciones de retorno en las pruebas y se repitió el ciclo real. El contacto sintético se conservó después de suspender y reactivar la misma instancia. La creación se realizó sin código Enterprise.

Se verificó la pantalla de instancia seleccionando explícitamente la compañía autorizada. Los secretos permanecen en .cache y no forman parte de Git. Captura local: .cache/windows/instancias.png.

No se acredita pago real, despliegue público, HTTPS ni validación fiscal. Los avisos del upstream sobre descripción reStructuredText y ausencia de wkhtmltopdf siguen identificados; no son fallos nuevos del módulo comercial y no se afirma soporte PDF. Los pendientes de cierre se explican en docs/APROVISIONAMIENTO_WINDOWS.md. No se ejecuta close-phase para aprobar una fase incompleta.

Revisión final: la configuración del cliente carga un directorio propio con erpec_base y excluye los módulos del operador. Se repitió la suspensión/reactivación tras ajustar esa ruta. PostgreSQL rechazó las conexiones cruzadas en ambos sentidos (operador → cliente y cliente → operador).
