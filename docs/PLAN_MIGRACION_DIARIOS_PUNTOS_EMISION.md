# Migración de diarios existentes a puntos de emisión SRI (propuesta para aprobación)

Estado: **propuesta detallada, NO ejecutada.** Requiere la aprobación del titular antes de tocar datos.
Fecha del análisis: 19-09-2026. Fuente: inventario de solo lectura de la demo (`erpec_demo`).

## 1. Situación real encontrada (demo)

| Diario | Tipo | Numeración | Punto SRI | Movimientos |
|---|---|---|---|---|
| `INV` "001-001 Facturas de cliente" (empresa 1) | ventas | entidad 001, emisión 001, con documentos | ninguno | 3 facturas contabilizadas, 0 emisiones SRI |
| `INV` (empresa 2, autoservicio) | ventas | 001-001 | ninguno | 0 |
| `FP001` "Facturación 001-001 Caja 1 (pruebas)" | ventas | 001-001, creado automáticamente por el punto 001-001 | Caja 1 | 0 |
| `BILL` "Vendor Bills" (x2 empresas) | compras | sin entidad/emisión | ninguno | 4 contabilizadas y 2 borradores (empresa 1) |
| Diarios de nómina, importación y sistema | general | no aplican a comprobantes | ninguno | no se tocan |

Hallazgo: para el mismo 001-001 conviven `INV` (con historial) y `FP001` (vacío). Sin migración, un cliente real tendría dos diarios de pruebas para el mismo punto y podría numerar dos veces.

## 2. Principios (no negociables)

1. Nunca se renumera ni se modifica un comprobante ya contabilizado ni una emisión existente.
2. Un diario pertenece a un solo punto y a un solo ambiente para toda su vida; el consecutivo de pruebas nunca se reutiliza en producción.
3. Todo es reversible y se hace con respaldo previo de la base y el filestore (mismo procedimiento que las instalaciones).
4. Primero simulación (dry-run) con listado exacto de cambios; solo se aplica con aprobación explícita.

## 3. Cambios propuestos (en orden)

**A. Adoptar diarios de ventas existentes** (sin tocar movimientos)
- Para cada diario de ventas con `l10n_ec_entity` y `l10n_ec_emission` válidos y sin punto: buscar o crear el punto (empresa + establecimiento + emisión) y asignar `ec_point_id`.
- El ambiente del diario se conserva (hoy todos son pruebas). Los 3 comprobantes de `INV` quedan como historial de pruebas.
- Datos que faltan y hay que pedir: nombre del establecimiento y **dirección del establecimiento** (obligatoria para `dirEstablecimiento`); nombre del punto (p. ej. "Caja 1").

**B. Resolver el duplicado 001-001**
- Opción recomendada: el punto 001-001 adopta `INV` como su diario de pruebas y `FP001` (0 movimientos) se archiva. Cambio de código asociado: `_ensure_journal()` debe adoptar primero un diario de ventas sin punto con la misma entidad/emisión antes de crear uno nuevo.
- Alternativa: mantener `FP001` como diario de pruebas y archivar `INV`; se pierde continuidad visual con las 3 facturas.

**C. Compras**
- `BILL` no se modifica (numeración manual de facturas de proveedores; no debe llevar punto).
- Para liquidaciones de compra: crear un diario de compras dedicado ("Liquidaciones 001-001") vinculado al punto, con `l10n_latam_use_documents`, porque el consecutivo lo asigna el sistema y no el usuario.
- Los 2 borradores y 4 contabilizadas de `BILL` no se tocan.

**D. Retenciones**
- Vincular el diario de retenciones (diario general) al punto correspondiente para que use su establecimiento, punto y dirección; hasta entonces usa los valores por defecto de la empresa (001-001).

**E. Punto por usuario/caja (opcional, segunda fase)**
- Campo `Punto de emisión predeterminado` en el usuario; las guías, retenciones y liquidaciones lo proponen al crearse. Un usuario sin punto usa el único punto de la empresa si solo hay uno; con varios debe elegirlo.

## 4. Simulación y verificación previas
- Script de solo lectura ya disponible (inventario usado para este documento) y un modo `dry-run` que imprimirá: puntos a crear, diarios a vincular, diarios a archivar y datos faltantes. No escribe nada.
- Después de aplicar: comprobar que (1) ningún comprobante cambió de número, (2) cada diario de ventas/compras de comprobantes tiene exactamente un punto, (3) no quedan dos diarios activos del mismo ambiente para un mismo punto, (4) pruebas automáticas fiscales en verde.

## 5. Reversión
Restaurar el respaldo (base + filestore) tomado justo antes; como no se modifican movimientos, también es posible revertir solo con: desvincular `ec_point_id` y reactivar el diario archivado.

## 6. Riesgos y decisiones que necesito de usted
1. ¿Se conserva `INV` (recomendado) o `FP001` como diario de pruebas del punto 001-001?
2. Nombre y dirección reales del establecimiento 001 y nombre del punto 001.
3. ¿Hay más establecimientos o cajas reales que deban crearse ahora?
4. ¿Se habilita ya el punto por usuario (E) o se deja para después?
5. Una empresa real que ya emita facturas en producción con numeración propia: se necesita el último secuencial usado por punto y comprobante para iniciar los consecutivos sin repetir. En la demo no aplica.
