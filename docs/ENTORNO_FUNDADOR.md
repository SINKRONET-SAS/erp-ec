# Entorno del Fundador (SINKRONET S.A.S.)

Instancia dedicada `erpec_fundador` (`.cache/windows/fundador`, http://127.0.0.1:8199, usuario `fundador`; la clave está en `.cache/windows/fundador/credentials.json`, fuera de git).

## Configuración aplicada (19-09-2026), con respaldo previo `backups/fundador-fiscal-config-20260919-083747`
- Empresa: SINKRONET S.A.S., RUC 1793235327001, dirección LOS CARDENALES SN Y AZULEJOS, país Ecuador.
- Régimen fiscal: **General** (campo nuevo `ec_tax_regime`). Los regímenes RIMPE quedan bloqueados para emitir hasta que el motor genere la leyenda `contribuyenteRimpe`.
- Obligada a llevar contabilidad: **Sí** (sociedad; dato legal para S.A.S., confirmar contra el RUC).
- Módulos fiscales instalados: `erpec_fiscal_native`, `erpec_fiscal_sri`, `erpec_fiscal_withholding_sri`, `erpec_fiscal_guide_sri` (y dependencias).
- El usuario `fundador` no tenía grupos contables y no veía los menús fiscales: se le agregaron (contable y responsable contable). El worker de aprovisionamiento ahora hace lo mismo con el administrador de cada cliente nuevo.

## Confirmado por el titular (19-09-2026)
- Perfil ordinario: **confirmado** (casilla marcada en la empresa).
- Establecimiento **001** y punto de emisión **004**: creados en el Fundador. Nombres tomados del ejemplo ya decidido para la demo (establecimiento PRINCIPAL, punto PRUEBAS) y dirección de la empresa; son editables en Fiscal > Establecimientos y puntos de emisión. Diario de ventas `FP001` "Facturación 001-004 PRUEBAS (pruebas)" con su propio consecutivo de pruebas.
- El diario `INV` 001-001 que trae el plan contable por defecto queda sin uso y sin movimientos (la auditoría lo señala); puede archivarse.

## Pendiente
1. Certificado de firma **de SINKRONET**: el disponible pertenece a otra identidad (RUC 1709053506001) y no puede firmar por el RUC 1793235327001. Se carga en Fiscal > Certificado de firma (SRI).
