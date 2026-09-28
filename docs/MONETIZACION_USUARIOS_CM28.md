# Monetización por usuarios y renovación CM28

Cada oferta define usuarios internos incluidos, máximo contratable y precio del usuario adicional por mes y por año en USD. El total se calcula en servidor: plan + complementos + usuarios adicionales, aplicando los impuestos nativos configurados. Los precios enviados por navegador no se aceptan.

Se cuenta cada cuenta interna activa, incluido el administrador humano. No se cuentan usuarios del portal, públicos ni la cuenta técnica raíz protegida. No es una métrica de sesiones concurrentes. Crear, reactivar o convertir un usuario de portal a interno consume cupo; también se verifica la modificación desde grupos de permisos. La instancia muestra el cupo y los usuarios utilizados en Mi contratación.

La oferta y el contrato guardan cantidades distintas: incluidos en tarifa y total comprado. El contrato conserva su instantánea aunque se retire la oferta pública. Cada renovación requiere un nuevo pago confirmado; una renovación anticipada comienza después del periodo vigente. Una confirmación tardía inicia el periodo al conciliar el pago. No hay prorrateos ni débitos automáticos.

Una reducción de cupo inferior a las cuentas activas deja una incidencia de aprovisionamiento. El operador debe pedir al cliente que archive las cuentas excedentes y reintentar; no se desactivan usuarios automáticamente. Los módulos retirados conservan el historial de lectura, pero bloquean altas y modificaciones. Los nunca contratados rechazan también su consulta.

La activación usa el mecanismo nativo de Odoo con caducidad de cuatro horas e invalidación después del uso. El trabajador no imprime contraseñas ni enlaces; el operador conserva el enlace cifrado y el portal verifica al titular antes de entregar acceso.
