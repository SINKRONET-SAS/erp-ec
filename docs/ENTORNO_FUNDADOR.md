# Entorno del Fundador (SINKRONET S.A.S.)

Instancia dedicada `erpec_fundador` (`.cache/windows/fundador`, http://127.0.0.1:8199, usuario `fundador`; la clave está en `.cache/windows/fundador/credentials.json`, fuera de git).

## Configuración aplicada (19-09-2026), con respaldo previo `backups/fundador-fiscal-config-20260919-083747`
- Empresa: SINKRONET S.A.S., RUC 1793235327001, dirección LOS CARDENALES SN Y AZULEJOS, país Ecuador.
- Régimen fiscal: **General** (campo nuevo `ec_tax_regime`). Los regímenes RIMPE quedan bloqueados para emitir hasta que el motor genere la leyenda `contribuyenteRimpe`.
- Obligada a llevar contabilidad: **Sí** (sociedad; dato legal para S.A.S., confirmar contra el RUC).
- Módulos fiscales instalados: `erpec_fiscal_native`, `erpec_fiscal_sri`, `erpec_fiscal_withholding_sri`, `erpec_fiscal_guide_sri` (y dependencias).
- El usuario `fundador` no tenía grupos contables y no veía los menús fiscales: se le agregaron (contable y responsable contable). El worker de aprovisionamiento ahora hace lo mismo con el administrador de cada cliente nuevo.

## Pendiente de datos del titular (no se inventaron)
1. Confirmar en la empresa el "perfil ordinario" (sin contribuyente especial, agente de retención, exportación ni transporte). Sin esa casilla el sistema no emite.
2. Establecimiento y punto de emisión registrados en el RUC (la simulación de migración propone 001-001 tomando la dirección de la empresa, sin aplicar).
3. Certificado de firma **de SINKRONET**: el certificado disponible pertenece a otra identidad (RUC 1709053506001) y no puede firmar por el RUC 1793235327001.
