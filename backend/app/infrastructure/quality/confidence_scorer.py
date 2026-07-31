"""
Calcul du score de confiance composite d'un tableau extrait.

Combine trois signaux indépendants (cf. conception validée du pipeline) :
1. Confiance OCR brute (si disponible -- Camelot n'en fournit pas).
2. Proportion de cellules individuellement peu fiables.
3. Cohérence des colonnes détectées comme numériques (une colonne de
   montants où 90% des cellules ne contiennent QUE des chiffres est un
   signal fort de bonne extraction ; des lettres qui s'y glissent trahissent
   une erreur OCR ou de découpage de colonne).
"""

import re

from app.domain.entities.extracted_table import ExtractedTable
from app.domain.value_objects.confidence_score import TableConfidenceScore

# Seuil EN DESSOUS DUQUEL une cellule individuelle est signalée comme
# suspecte -- distinct des seuils globaux de routage du pipeline.
CELL_CONFIDENCE_THRESHOLD = 0.80

NUMERIC_PATTERN = re.compile(r"^[\d\s.,\-]+$")

WEIGHTS = {
    "mean_word_confidence": 0.4,
    "low_confidence_penalty": 0.3,
    "numeric_consistency": 0.3,
}


def _numeric_consistency_ratio(rows: list[list[str]]) -> float:
    if not rows or not rows[0]:
        return 1.0

    column_count = len(rows[0])
    ratios = []

    for col_index in range(column_count):
        cells = [row[col_index] for row in rows if col_index < len(row) and row[col_index].strip()]
        if not cells:
            continue

        numeric_matches = sum(1 for c in cells if NUMERIC_PATTERN.match(c.strip()))
        column_is_numeric = numeric_matches / len(cells) >= 0.6

        if column_is_numeric:
            ratios.append(numeric_matches / len(cells))

    return sum(ratios) / len(ratios) if ratios else 1.0  # pas de colonne numérique = neutre


def score_table(table: ExtractedTable) -> TableConfidenceScore:
    numeric_consistency = _numeric_consistency_ratio(table.rows)

    if table.cell_confidences is not None:
        flat_confidences = [c for row in table.cell_confidences for c in row]
        mean_confidence = sum(flat_confidences) / len(flat_confidences) if flat_confidences else 0.0
        low_confidence_ratio = (
            sum(1 for c in flat_confidences if c < CELL_CONFIDENCE_THRESHOLD) / len(flat_confidences)
            if flat_confidences else 1.0
        )
    else:
        # Cas Camelot : pas de confiance par mot, on utilise son propre
        # score de précision interne comme proxy raisonnable.
        mean_confidence = table.camelot_accuracy / 100
        low_confidence_ratio = 0.0 if table.camelot_accuracy >= 80 else 0.3

    overall = (
        WEIGHTS["mean_word_confidence"] * mean_confidence
        + WEIGHTS["low_confidence_penalty"] * (1 - low_confidence_ratio)
        + WEIGHTS["numeric_consistency"] * numeric_consistency
    )

    return TableConfidenceScore(
        mean_word_confidence=mean_confidence,
        low_confidence_cell_ratio=low_confidence_ratio,
        numeric_consistency_ratio=numeric_consistency,
        overall_score=round(overall, 3),
    )


def find_flagged_cells(table: ExtractedTable) -> list[tuple[int, int]]:
    """Retourne les coordonnées (ligne, colonne) des cellules sous le seuil
    -- utilisées ensuite pour la correction ciblée ET pour le surlignage
    dans le fichier Excel final."""
    if table.cell_confidences is None:
        return []
    flagged = []
    for row_idx, row in enumerate(table.cell_confidences):
        for col_idx, confidence in enumerate(row):
            if confidence < CELL_CONFIDENCE_THRESHOLD:
                flagged.append((row_idx, col_idx))
    return flagged