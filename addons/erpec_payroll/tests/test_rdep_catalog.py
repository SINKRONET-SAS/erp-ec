"""D5: fija por huella el catálogo RDEP oficial (docs/evidencias, aportado por el titular el 21-09-2026)
y comprueba que los códigos y la regla de derogación de 2024 que usa el motor coinciden con su hoja
TABLAS. Si el SRI publica un catálogo distinto, esta prueba debe fallar hasta que el código se ajuste:
no se debe suponer nunca una compatibilidad no verificada."""
import hashlib
from datetime import date
from pathlib import Path
import openpyxl
from odoo.tests import TransactionCase, tagged
from ..engine import resolve_exemption_claims

CATALOG = Path(__file__).resolve().parent.parent / 'reference/Catalogo_RDEP_2024.xlsx'


@tagged('post_install', '-at_install')
class RdepCatalogCase(TransactionCase):
    def test_bundled_catalog_is_the_file_the_project_owner_provided(self):
        self.assertEqual(hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
                          '26230c6217dd3ba60db750c91c49edb5af80775b69f96b08b8c7b6b56977dc7e')

    def test_disability_codes_match_the_catalog_tablas_sheet(self):
        # Hoja TABLAS, tabla "CONDICIÓN DEL TRABAJADOR RESPECTO A DISCAPACIDADES": columnas 1 (código) y 2 (descripción).
        wb = openpyxl.load_workbook(CATALOG, data_only=True)
        rows = list(wb['TABLAS'].iter_rows(min_row=16, max_row=20, values_only=True))
        codes = {str(row[1]).strip(): str(row[2]).strip() for row in rows if row[1] is not None}
        self.assertEqual(codes, {
            '00': 'Sin dato para el período (anteriores al 2013)',
            '01': 'No aplica',
            '02': 'Trabajador con discapacidad',
            '03': 'Trabajador que actúa en calidad de sustituto de una persona con discapacidad',
            '04': 'Trabajador tiene cónyuge, pareja en unión de hecho o hijo con discapacidad y se encuentra '
                  'bajo su cuidado y/o responsabilidad (vigente hasta el periodo 2023)',
        })

    def test_code_04_is_rejected_from_2024_and_never_grants_the_exemption(self):
        # Catálogo, hoja CATÁLOGO: <tipoTrabajDiscap> debe excluir 00 y 04 desde el período 2024; y <exoDiscap>
        # solo es aplicable a los códigos 02 (discapacidad) o 03 (sustituto), nunca a 01 o 04.
        claims, issues, _ = resolve_exemption_claims(
            2023, None, '04', 50, 'N', '', 2023, 'DOC-1', date(2023, 1, 10))
        self.assertFalse(claims)
        self.assertTrue(issues)
        claims, issues, _ = resolve_exemption_claims(
            2024, None, '04', 50, 'N', '', 2024, 'DOC-1', date(2024, 1, 10))
        self.assertFalse(claims)
        self.assertTrue(issues)

    def test_code_01_no_aplica_never_creates_a_condition_or_a_notice(self):
        # Sin acreditación, el código 01 (no aplica) no genera ni reclamo ni aviso: a diferencia de un
        # código de discapacidad real, no hay ninguna condición detectada que avisar.
        claims, issues, notes = resolve_exemption_claims(2026, None, '01', 0, 'N', '', None, '', None)
        self.assertEqual((claims, issues, notes), ([], [], []))
        claims, issues, notes = resolve_exemption_claims(2026, None, '02', 50, 'N', '', None, '', None)
        self.assertEqual((claims, issues), ([], []))
        self.assertTrue(notes)
