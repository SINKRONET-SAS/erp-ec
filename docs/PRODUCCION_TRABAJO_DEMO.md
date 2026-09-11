# Producción y órdenes de trabajo — primer incremento local

La demo disponible en http://127.0.0.1:8369/odoo/action-524 incorpora `erpec_manufacturing`, sobre `mrp` y `mrp_account` Community del checkout fijado. Se comprobó LGPL-3 en los manifiestos oficiales y ausencia de módulos OEEL-1/OPL-1 instalados. El módulo propio conserva la declaración de licencia del código propio existente; no cambia licencias ajenas.

## Qué se puede demostrar

En ERP EC → Producción y trabajo están las órdenes, operaciones y tiempos, carga de centros y listas de materiales. Los usuarios de fabricación también conservan las pantallas nativas de Fabricación y sus permisos Community.

1. Abrir WH/MO/00001: un Estante fabricado DEMO terminado. Sus dos componentes cuestan 10 USD y las dos operaciones sintéticas de diez minutos, a 60 USD/hora, aportan 20 USD. La valoración AVCO total comprobada es 30 USD. Los tiempos son ejemplos preparados, no mediciones de trabajo humano.
2. Abrir WH/MO/00002: dos unidades pendientes. En las operaciones, iniciar Preparación, abrir su formulario, indicar el motivo de pausa, pausar, reanudar y finalizar; después iniciar y terminar Montaje. La segunda etapa rechaza el inicio o finalización mientras su predecesora no haya terminado.
3. Registrar cantidad producida y finalizar la fabricación. Para producción parcial, conservar el remanente mediante el asistente nativo. Las operaciones deben estar terminadas antes de cerrar la orden.
4. Abrir WH/MO/00003: cincuenta unidades con faltantes. Revisar componentes y abastecer antes de completar; un cierre que deje existencias negativas se rechaza y revierte sus movimientos y valoración.
5. Consultar la valoración desde la orden y los tiempos desde las operaciones. La carga de centros y la lista de materiales usan las vistas nativas.

El motivo de pausa queda en el historial de la fabricación. Se serializan las acciones del temporizador por orden y se conserva el reintento transaccional nativo: dos solicitudes HTTP concurrentes del mismo usuario generaron un solo intervalo abierto.

## Validación realizada

Se detuvo la demo para obtener un respaldo consistente de base, filestore y módulos. Se restauró una copia para instalar y probar antes de tocar la demo original. Cuatro pruebas transaccionales terminaron con cero fallos y cero errores:

- Producción parcial de una unidad y remanente de otra; consumo de cuatro componentes, valoración de veinte dólares, desperdicio de un componente por cinco dólares y desmontaje de una unidad con devolución de dos componentes.
- Rechazo y reversión del cierre por faltantes; reposición, nueva reserva y cierre sin existencias negativas.
- Dos operaciones dependientes, inicio repetido, pausa y reanudación, veinte minutos de tiempos sintéticos y costo total de treinta dólares incluido el material.
- Acceso entre empresas rechazado, acciones de navegación existentes y vista de fabricación compilada.

Después se preparó el escenario comercial en la copia y se probaron dos peticiones HTTP simultáneas: ambas terminaron, quedó un solo temporizador abierto y ninguno tras pausar. Los archivos probados se verificaron por SHA256 antes de instalar. La demo instalada se autenticó y compiló la vista nueva; mantiene RUC vacío y no incluye Enterprise. No hubo emisión fiscal, nuevo pago ni despliegue cloud.

La inspección visual del navegador no terminó: el control del navegador agotó sus tiempos de respuesta. No se presenta la compilación de vistas como revisión visual completa.

## Recuperación y límites

Respaldo previo a instalar: `.cache/windows/backups/manufacturing-install-20260911-093239`, que contiene `database.dump`, `filestore` y `addons`. No borrar la base ni los archivos actuales para ensayar una reversión.

```powershell
.venv/Scripts/python.exe scripts/restore-manufacturing-demo.py --backup '.cache/windows/backups/manufacturing-install-20260911-093239'
```

El script recupera el estado anterior en una base nueva, con rol propio sin privilegios administrativos, filestore separado y cron detenido; verifica que la empresa siga sin RUC y no tenga instalado el incremento de fabricación. No reemplaza la demo actual. La ruta de configuración recuperada se informa al terminar. Una sustitución del servicio debe hacerse solo después de revisar el resultado y conservar el estado nuevo si hubo operaciones posteriores al respaldo.

La valoración de este escenario es AVCO periódica: no se acredita contabilización automática del inventario ni cierre fiscal. Desmontar devuelve componentes y producto en el ensayo; no borra tiempos históricos ni equivale a deshacer costos laborales, desperdicios o documentos contables publicados. Lotes/series, secuencias parciales con operaciones, abastecimiento completo compra/venta/fabricación, roles operario/supervisor de extremo a extremo, calendario/capacidad avanzada, pausas improductivas con duración separada y costo contable automático requieren ensayos adicionales antes del cierre íntegro OP01/OP02. No se retiran del alcance.

Este incremento no cierra las fases históricas 04–08 ni todo OP01/OP02. OP03 Importaciones y OP04 Nómina mantienen sus prompts y requisitos. PAYPHONE ya tenía prueba externa registrada; Render sigue aplazado conforme a la instrucción del usuario.
