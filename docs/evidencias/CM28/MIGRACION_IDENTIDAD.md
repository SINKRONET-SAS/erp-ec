# Migración de identidad CM28-A

Migración aditiva: contratos e instancias existentes mantienen customer_id nulo y su nombre/base/compañía. Ningún cliente histórico se infiere del correo/RUC. El índice parcial mantiene una instancia histórica por compañía; la nueva restricción mantiene una por cliente explícito. Las nuevas altas crean cliente propio dentro del operador.

Actualizar primero una copia; respaldar base, filestore y revisión del código. Reversión: restaurar el respaldo completo y el código anterior de forma conjunta, no eliminar columnas ni consolidar clientes por SQL. Tras admitir clientes nuevos no es seguro volver al índice único por compañía sin restaurar datos; no ejecutar downgrade destructivo. Los contratos históricos conservan derechos y su instancia; no constituyen altas comerciales nuevas.
