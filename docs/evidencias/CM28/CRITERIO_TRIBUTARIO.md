# Tratamiento tributario de ofertas

Fuente primaria consultada el 28-09-2026: https://www.sri.gob.ec/impuesto-al-valor-agregado-iva . El SRI describe como base el precio de los bienes/servicios con los componentes y descuentos aplicables. No se fija una tarifa legal en código ni se asume tarifa cero por no tener configuración.

CM28 reutiliza account.tax.compute_all de Odoo para los impuestos configurados por el responsable del operador. La publicación comercial requiere revisar el tratamiento tributario. Las pruebas usan 7% explícitamente sintético, sin atribuirle vigencia normativa. La clasificación fiscal y la emisión de comprobantes no se sustituyen con la confirmación de un pago PayPhone.
