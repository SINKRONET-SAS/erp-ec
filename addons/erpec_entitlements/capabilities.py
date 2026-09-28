"""Lista técnica autorizada; un único mapa para catálogo y trabajador."""
CAPABILITIES = {
    'assets': ('Activos fijos', ('erpec_assets',)),
    'sales': ('Ventas', ('sale_management',)),
    'purchases': ('Compras', ('purchase',)),
    'inventory': ('Inventario', ('stock',)),
    'payroll': ('Nómina ERP EC', ('erpec_payroll',)),
    'fiscal': ('Facturación electrónica ERP EC', ('erpec_fiscal_sri', 'erpec_fiscal_withholding_sri', 'erpec_fiscal_guide_sri', 'erpec_fiscal_ats')),
    'manufacturing': ('Fabricación', ('mrp',)),
    'treasury': ('Tesorería', ('erpec_treasury',)),
    'routes': ('Rutas de campo', ('erpec_field_routes',)),
}

# Fabricación registra movimientos de inventario; ese derecho debe estar contratado.
REQUIREMENTS = {'manufacturing': {'inventory'}}

def missing_requirements(codes):
    selected=set(codes)
    return sorted({required for code in selected for required in REQUIREMENTS.get(code,set())}-selected)
