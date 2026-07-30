"""
Génération du fichier Excel final à partir des tableaux extraits.

Ne dépend que de l'entité domaine ExtractedTable -- ne sait jamais si les
données viennent de Camelot, de l'OCR, ou d'autre chose. Un onglet par
tableau détecté, nommé par page, pour rester lisible même sur un PDF
multi-pages avec plusieurs tableaux.
"""

from openpyxl import Workbook
from openpyxl.styles import Font

from app.domain.entities.extracted_table import ExtractedTable


def write_tables_to_excel(tables: list[ExtractedTable], output_path: str) -> None:
    if not tables:
        raise ValueError("Aucun tableau à écrire -- liste vide.")

    workbook = Workbook()
    # openpyxl crée une feuille par défaut ("Sheet") -- on la supprime,
    # on va créer une feuille par tableau nous-mêmes.
    workbook.remove(workbook.active)

    for i, table in enumerate(tables, start=1):
        sheet_name = f"Page{table.page_number}_Tableau{i}"[:31]  # limite Excel : 31 caractères
        sheet = workbook.create_sheet(title=sheet_name)

        for row in table.rows:
            sheet.append(row)

        # Mise en forme minimale : en-tête en gras (on suppose que la
        # première ligne extraite est l'en-tête -- hypothèse V1, à affiner
        # plus tard si besoin avec le score de confiance).
        for cell in sheet[1]:
            cell.font = Font(bold=True)

        # Largeur de colonnes auto-approximative, pour un résultat lisible
        # sans que l'utilisateur ait à tout réajuster à la main.
        for column_cells in sheet.columns:
            max_length = max((len(str(c.value)) for c in column_cells if c.value), default=10)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 50)

    workbook.save(output_path)