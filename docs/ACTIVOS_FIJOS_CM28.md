# Activos fijos — operación contable

Acceso: Contabilidad > Activos fijos. El responsable contable configura categorías con cuentas y diario general. Crear manualmente o desde la acción Activo fijo de una línea de compra contabilizada. El costo se expresa en moneda de la empresa; una compra en moneda extranjera usa el balance contable ya convertido por Odoo.

La suma de capitalizaciones, incluidos borradores, no puede superar la línea de compra. Se serializa la reserva sobre la fila origen, provocando reintento transaccional ante concurrencia para evitar lecturas obsoletas. Confirmar reclasifica la compra a la cuenta del activo; si ya está contabilizada allí no duplica el costo. En alta manual se usa la contrapartida configurada.

Depreciación lineal mensual: (costo - residual) / meses. El primer mes incompleto se prorratea por días calendario incluidos desde la puesta en uso; la última cuota absorbe la fracción restante y el redondeo. Se genera una cuota final adicional si el inicio no es el primer día. Contabilizar cuotas vencidas es idempotente y respeta cierres contables. No hay depreciación fiscal automática ni afirmación de deducibilidad.

Cambiar estimación exige primer día de mes, cuotas anteriores contabilizadas y motivo. Solo reemplaza cuotas futuras sin asiento; conserva el historial y los asientos anteriores.

Baja sin venta reconoce el valor pendiente como pérdida. Venta requiere una línea de factura contabilizada de la misma empresa, sin reutilización; reclasifica su ingreso para reconocer la ganancia/pérdida neta del activo. La reversión genera contraasientos fechados, nunca borra asientos. No anula la factura de compra/venta: su corrección sigue el flujo nativo y se gestiona por separado tras revertir el activo.

El informe por empresa y categoría presenta costo, depreciación acumulada y valor en libros vigentes; exportación nativa de Odoo. Conciliar con las cuentas del mayor, revisando compras todavía no asignadas a activos. No sumar monedas de empresas diferentes como si fueran equivalentes.

Permisos: responsable contable opera; consulta contable lee. Los datos están separados por empresa. Costo y cuentas de activos en uso no se editan directamente. Revaluación, deterioro, métodos acelerados y gestión patrimonial de custodios quedan fuera de esta versión.
