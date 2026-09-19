"""Catálogo de conceptos de retención de renta vigentes (codigoRetencion del comprobante 07).
Generado desde la localización de Odoo (l10n_ec, account.tax-ec.csv, solo impuestos activos, grupo
withhold_income_purchase): código ATS -> tarifas vigentes. Fuente secundaria: el SRI es la autoridad y
valida código y tarifa al autorizar (p. ej. 312 vigente = 2%). Regenerar cuando cambie la normativa.
La ficha técnica del SRI remite al Catálogo ATS para estas tarifas."""
INCOME = {
    '303': {'rates': (10.0,), 'label': '303 10% Honorarios Profesionales'},
    '303A': {'rates': (5.0,), 'label': '303A 5% Servicios Profesionales Prestados por Sociedades Residentes'},
    '304': {'rates': (10.0,), 'label': '304 10% Servicios Predomina el Intelecto No Relacionados con el Titulo Profesional'},
    '304A': {'rates': (10.0,), 'label': '304A 10% Comisiones y Demas Pagos por Servicios Predomina Intelecto No Relacionados con el Titulo Profesional'},
    '304B': {'rates': (10.0,), 'label': '304B 10% Pagos a Notarios y Registradores de la Propiedad y Mercantil por sus Actividades Ejercidas Como Tales'},
    '304C': {'rates': (10.0,), 'label': '304C 10% Deportistas'},
    '304D': {'rates': (10.0,), 'label': '304D 10% Artistas'},
    '304E': {'rates': (8.0,), 'label': '304E 8% Docencia'},
    '307': {'rates': (3.0,), 'label': '307 3% Servicios Mano de Obra'},
    '308': {'rates': (10.0,), 'label': '308 10% Imagen/Renombre'},
    '309': {'rates': (3.0,), 'label': '309 3% Servicios Prestados por Medios de Comunicación y Agencias de Publicidad'},
    '310': {'rates': (1.0,), 'label': '310 1% Transporte'},
    '311': {'rates': (3.0,), 'label': '311 3% Compra'},
    '312': {'rates': (2.0,), 'label': '312 2% Transferencia Bienes'},
    '312A': {'rates': (1.0,), 'label': '312A 1% Compras al Productor'},
    '312C': {'rates': (1.75,), 'label': '312C 1.75% Compras al Comercializador: de Bienes de Origen Bioacuático, Forestal y los Descritos el Art.27.1 de LRTI'},
    '314A': {'rates': (10.0,), 'label': '314A 10% Regalías por Concepto de Franquicias de Acuerdo al Código INGENIOS (COESCCI) - Pago a Personas Naturales'},
    '314B': {'rates': (10.0,), 'label': '314B 10% Cánones, Derechos de Autor, Marcas, Patentes y Similares de Acuerdo al Código INGENIOS (COESCCI) – Pago a Personas Naturales'},
    '314C': {'rates': (10.0,), 'label': '314C 10% Regalias por Concepto de Franquicias de Acuerdo al Código INGENIOS (COESCCI) - Pago a Sociedades'},
    '314D': {'rates': (10.0,), 'label': '314D 10% Cánones, Derechos de Autor, Marcas, Patentes y Similares de Acuerdo al Código INGENIOS (COESCCI)'},
    '319': {'rates': (2.0,), 'label': '319 2% Cuotas de Arrendamiento Mercantil'},
    '320': {'rates': (10.0,), 'label': '320 10% Por Arrendamiento Bienes Inmuebles'},
    '322': {'rates': (2.0,), 'label': '322 2% Seguros y Reaseguros (Primas y Cesiones)'},
    '323O': {'rates': (1.0,), 'label': '323O 1% Intereses y Demás Rendimientos Financieros Pagados a Bancos y Otras Entidades Sometidas al Control de la Superintendencia de Bancos y de la Economía Popular y Solidaria'},
    '332': {'rates': (0.0,), 'label': '332 0% Otras Compras'},
    '332A': {'rates': (0.0,), 'label': '332A 0% Enajenacion'},
    '332B': {'rates': (0.0,), 'label': '332B 0% Compra Inmuebles'},
    '332C': {'rates': (0.0,), 'label': '332C 0% Transporte Pasajeros'},
    '332D': {'rates': (0.0,), 'label': '332D 0% Pagos Transporte'},
    '332G': {'rates': (0.0,), 'label': '332G 0% Pagos Tarjeta'},
    '332I': {'rates': (0.0,), 'label': '332I 0% Pagos Débito'},
    '343': {'rates': (1.0,), 'label': '343 1% Otras Retenciones'},
    '343A': {'rates': (2.0,), 'label': '343A 2% Energia Electrica'},
    '343B': {'rates': (2.0,), 'label': '343B 2% Por Actividades de Construccion de Obra Material Inmueble, Urbanizacion, Lotizacion o Actividades Similares'},
    '343C': {'rates': (2.0,), 'label': '343C 2% Recepción de Botellas Plásticas no Retornables de PET'},
    '3440': {'rates': (3.0,), 'label': '3440-344 3% Otras Retenciones'},
    '346': {'rates': (1.75,), 'label': '346 1.75% Microempresas'},
    '347': {'rates': (2.0,), 'label': '347-346 2% Donaciones'},
    '3482': {'rates': (5.0,), 'label': '3482 5% Comisiones a sociedades, nacionales o extranjeras residentes y establecimientos permanentes domiciliados en el país'},
    '352': {'rates': (22.0,), 'label': '302 En rel. de Dep. que Supera o no la Base Desg.'},
    '501': {'rates': (22.0,), 'label': '501-411 22% Pago al Ext. Benef. Emp. (C/ Conv. D. T.)'},
    '502': {'rates': (22.0,), 'label': '502-411 22% Pago al Ext. Serv. Emp. (C/ Conv. D. T.)'},
    '509': {'rates': (22.0,), 'label': '509-411 22% Pago al Ext. Casales (C/ Conv. D. T.)'},
    '511': {'rates': (22.0,), 'label': '511-411 22% Pago al Ext. Serv. Prof. Ind. (C/ Conv. D. T.)'},
    '512': {'rates': (22.0,), 'label': '512-411 22% Pago al Ext. Serv. Prof. Dep. (C/ Conv. D. T.)'},
    '517': {'rates': (22.0,), 'label': '517-411 22% Pago al Ext. Reem. Gastos (C/ Conv. D. T.)'},
    '520D': {'rates': (22.0,), 'label': '520D-411 22% Pago al Ext. Comis. Export. y Promoc. Tur. Rec. (C/ Conv. D. T.)'},
    '522A': {'rates': (22.0,), 'label': '522A-410 22% Pago al Ext. Serv. Téc., Admin. o Consult. y Regalias (C/ Conv. D. T.)'},
}

VAT = {'10': '9', '20': '10', '30': '1', '50': '11', '70': '2', '100': '3', '0': '7'}  # % IVA retenido -> código (Tabla 20, ficha técnica 2.34)


def income_label(code):
    entry = INCOME.get(code or '')
    return entry['label'] if entry else ''


def income_rates(code):
    entry = INCOME.get(code or '')
    return entry['rates'] if entry else ()
