"""
Correction ciblée des cellules peu fiables, par règles déterministes.

N'intervient QUE sur les cellules déjà flaggées par le score de confiance,
dans les colonnes identifiées comme numériques -- jamais sur du texte libre
(un nom mal orthographié n'a pas de règle de correction fiable ; un montant
avec un caractère ambigu, si).
"""

import re

from app.domain.entities.extracted_table import ExtractedTable

NUMERIC_PATTERN = re.compile(r"^[\d\s.,\-]+$")

# Confusions OCR classiques chiffre <-> lettre, observées sur des scans
# de mauvaise qualité (glyphes similaires en typographie).
DIGIT_CONFUSION_MAP = {
    "O": "0", "o": "0",
    "l": "1", "I": "1", "|": "1",
    "S": "5", "s": "5",
    "B": "8",
    "Z": "2",
    "G": "6",
}


def _try_correct_numeric(cell: str) -> str:
    corrected = "".join(DIGIT_CONFUSION_MAP.get(ch, ch) for ch in cell)
    return corrected


def _is_numeric_column(rows: list[list[str]], col_index: int) -> bool:
    cells = [row[col_index] for row in rows if col_index < len(row) and row[col_index].strip()]
    if not cells:
        return False
    numeric_matches = sum(1 for c in cells if NUMERIC_PATTERN.match(c.strip()))
    return numeric_matches / len(cells) >= 0.6


def post_process_table(
    table: ExtractedTable, flagged_cells: list[tuple[int, int]]
) -> tuple[ExtractedTable, list[tuple[int, int]]]:
    """Retourne le tableau corrigé + la liste des cellules TOUJOURS
    problématiques après correction (celles-ci sont les candidates au
    fallback LLM, étape suivante du pipeline)."""
    if not flagged_cells:
        return table, []

    numeric_columns = {
        col for col in range(table.column_count) if _is_numeric_column(table.rows, col)
    }

    corrected_rows = [row[:] for row in table.rows]
    still_flagged = []

    for row_idx, col_idx in flagged_cells:
        if row_idx >= len(corrected_rows) or col_idx >= len(corrected_rows[row_idx]):
            continue

        original = corrected_rows[row_idx][col_idx]

        if col_idx in numeric_columns and not NUMERIC_PATTERN.match(original.strip()):
            corrected = _try_correct_numeric(original)
            corrected_rows[row_idx][col_idx] = corrected
            if not NUMERIC_PATTERN.match(corrected.strip()):
                still_flagged.append((row_idx, col_idx))
        else:
            # Cellule flaggée mais hors colonne numérique (ex. un nom) --
            # pas de règle de correction fiable, on la laisse telle quelle
            # et on la marque pour révision humaine ou LLM.
            still_flagged.append((row_idx, col_idx))

    corrected_table = ExtractedTable(
        page_number=table.page_number,
        rows=corrected_rows,
        extraction_method=table.extraction_method,
        camelot_accuracy=table.camelot_accuracy,
        cell_confidences=table.cell_confidences,
    )
    return corrected_table, still_flagged