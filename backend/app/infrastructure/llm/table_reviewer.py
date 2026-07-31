"""
Revue ciblée des cellules peu fiables par le LLM Mistral.

N'intervient que sur les cellules déjà flaggées (score de confiance ou
correction Regex ayant échoué) -- jamais sur le tableau entier. Traite par
lots de lignes pour limiter le nombre d'appels API et rester dans les
limites du tier gratuit.
"""

from app.core.logging import get_logger
from app.domain.entities.extracted_table import ExtractedTable
from app.infrastructure.llm.mistral_client import call_mistral_json

logger = get_logger(__name__)

ROWS_PER_BATCH = 15

SYSTEM_PROMPT = """Tu es un assistant de saisie de données spécialisé dans la \
correction d'erreurs OCR sur des tableaux administratifs/financiers scannés.

On te donne un extrait de tableau avec des cellules marquées comme incertaines \
(balise <?>valeur_ocr</?>). En te basant sur le contexte (en-têtes de colonnes, \
valeurs des cellules voisines, cohérence du type de donnée dans la colonne), \
propose une correction pour chaque cellule marquée.

Règles strictes :
- Si tu n'es pas raisonnablement confiant dans la correction, renvoie null pour \
cette cellule plutôt que de deviner au hasard.
- Ne modifie JAMAIS une cellule qui n'est pas marquée <?>...</?>.
- Réponds UNIQUEMENT en JSON, format : \
{"corrections": [{"row": <index ligne>, "col": <index colonne>, "value": "..." ou null}]}
"""


def _build_batch_prompt(
    header_row: list[str], rows: list[list[str]], row_offset: int,
    flagged_in_batch: set[tuple[int, int]],
) -> str:
    lines = ["En-têtes de colonnes : " + " | ".join(header_row), "", "Lignes du tableau :"]
    for local_idx, row in enumerate(rows):
        global_idx = row_offset + local_idx
        cells = []
        for col_idx, value in enumerate(row):
            if (global_idx, col_idx) in flagged_in_batch:
                cells.append(f"<?>{value}</?>")
            else:
                cells.append(value)
        lines.append(f"Ligne {global_idx} : " + " | ".join(cells))
    return "\n".join(lines)


def review_flagged_cells(
    table: ExtractedTable, flagged_cells: list[tuple[int, int]]
) -> tuple[ExtractedTable, list[tuple[int, int]]]:
    """Retourne le tableau avec les corrections LLM appliquées, et la liste
    des cellules toujours non résolues (candidates à un simple signalement
    visuel dans l'Excel final, cf. étape contrôle qualité)."""
    if not flagged_cells or not table.rows:
        return table, flagged_cells

    corrected_rows = [row[:] for row in table.rows]
    flagged_set = set(flagged_cells)
    still_flagged = set(flagged_cells)

    header_row = corrected_rows[0] if corrected_rows else []
    data_rows = corrected_rows  # on inclut la ligne d'en-tête dans l'indexation globale

    for batch_start in range(0, len(data_rows), ROWS_PER_BATCH):
        batch_rows = data_rows[batch_start:batch_start + ROWS_PER_BATCH]
        batch_flagged = {
            (r, c) for (r, c) in flagged_set
            if batch_start <= r < batch_start + ROWS_PER_BATCH
        }
        if not batch_flagged:
            continue  # ne pas dépenser d'appel API sur un lot sans cellule suspecte

        logger.info(
            "Revue LLM : lignes %d-%d, %d cellule(s) suspecte(s)",
            batch_start, batch_start + len(batch_rows), len(batch_flagged),
        )

        prompt = _build_batch_prompt(header_row, batch_rows, batch_start, batch_flagged)
        result = call_mistral_json(SYSTEM_PROMPT, prompt)

        for correction in result.get("corrections", []):
            row_idx = correction.get("row")
            col_idx = correction.get("col")
            value = correction.get("value")

            if (row_idx, col_idx) not in batch_flagged:
                continue  # sécurité : on ignore toute correction hors périmètre demandé
            if value is None:
                continue  # le modèle n'était pas confiant -- reste flaggé

            if row_idx < len(corrected_rows) and col_idx < len(corrected_rows[row_idx]):
                corrected_rows[row_idx][col_idx] = str(value)
                still_flagged.discard((row_idx, col_idx))

    corrected_table = ExtractedTable(
        page_number=table.page_number,
        rows=corrected_rows,
        extraction_method=table.extraction_method,
        camelot_accuracy=table.camelot_accuracy,
        cell_confidences=table.cell_confidences,
    )
    return corrected_table, sorted(still_flagged)