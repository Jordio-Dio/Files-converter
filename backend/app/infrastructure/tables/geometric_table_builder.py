"""
Reconstruction de tableau à partir de mots OCR positionnés (docTR).

Version 4 -- remplace le clustering de colonnes par point (fragile : la
position centrale d'un mot varie avec sa longueur, ex. "247150" vs "7414")
par une détection basée sur les ZONES VIDES de la page (technique standard
de reconnaissance de tableaux par alignement, indépendante de la largeur
de chaque mot).
"""

import statistics

from app.domain.entities.extracted_table import ExtractedTable, ExtractionMethod
from app.domain.value_objects.ocr_result import OcrWord

ROW_TOLERANCE_RATIO = 0.6
BLOCK_GAP_RATIO = 1.8
MIN_TABLE_ROWS = 4

# Résolution de la grille utilisée pour repérer les zones vides -- plus
# c'est fin, plus la détection de colonnes proches est précise.
COLUMN_GRID_BINS = 500
# Une zone vide n'est considérée comme un VRAI séparateur de colonne que si
# elle est plus large que ce multiple de la hauteur de ligne -- un simple
# espace entre deux mots d'une même cellule ("GILBERT NOEL") est plus étroit
# qu'un séparateur de colonne dans un tableau imprimé.
COLUMN_GAP_MIN_RATIO = 0.15


def _estimate_line_height(words: list[OcrWord]) -> float:
    heights = [w.height for w in words if w.height > 0]
    return statistics.median(heights) if heights else 0.01


def _group_words_into_rows(words: list[OcrWord], row_tolerance: float) -> list[list[OcrWord]]:
    """Regroupe les mots par ligne en ancrant chaque comparaison sur le
    PREMIER mot de la ligne en cours (référence fixe), et non sur une
    moyenne mobile -- une moyenne mobile dérive progressivement à mesure
    qu'on ajoute des mots légèrement décalés, jusqu'à finir par avaler le
    premier mot de la ligne suivante (bug observé : deux lignes de
    personnes différentes fusionnées avec valeurs dupliquées)."""
    sorted_words = sorted(words, key=lambda w: w.y_center)
    rows: list[list[OcrWord]] = []

    for word in sorted_words:
        if rows:
            row_anchor = rows[-1][0].y_center  # référence FIXE, pas de dérive possible
            if abs(word.y_center - row_anchor) <= row_tolerance:
                rows[-1].append(word)
                continue
        rows.append([word])

    for row in rows:
        row.sort(key=lambda w: w.x_center)
    return rows


def _split_into_blocks(
    rows: list[list[OcrWord]], block_gap: float
) -> list[list[list[OcrWord]]]:
    blocks: list[list[list[OcrWord]]] = []
    current_block: list[list[OcrWord]] = []
    previous_y = None
    for row in rows:
        row_y = sum(w.y_center for w in row) / len(row)
        if previous_y is not None and (row_y - previous_y) > block_gap:
            if current_block:
                blocks.append(current_block)
            current_block = []
        current_block.append(row)
        previous_y = row_y
    if current_block:
        blocks.append(current_block)
    return blocks


# Une bande verticale compte comme "séparateur de colonne" si elle est
# vide sur au moins cette proportion des lignes du bloc -- au lieu
# d'exiger qu'elle soit vide sur 100% des lignes (bien trop fragile face
# à un nom exceptionnellement long qui déborde sur une seule ligne).
COLUMN_GAP_SUPPORT_RATIO = 0.70


def _detect_column_segments(
    rows: list[list[OcrWord]], line_height: float
) -> list[tuple[float, float]]:
    """Détecte les colonnes par consensus de zones vides à travers les
    lignes du bloc, plutôt que par un simple OU logique (une seule ligne
    qui déborde ne doit plus pouvoir fusionner deux colonnes à elle seule)."""
    n_rows = len(rows)
    if n_rows == 0:
        return []

    occupied_row_count = [0] * COLUMN_GRID_BINS

    for row in rows:
        row_occupied = [False] * COLUMN_GRID_BINS
        for word in row:
            half_width = max(word.width * 0.25, 0.002)  # noyau du mot (50% de sa largeur)
            x_min = max(0.0, word.x_center - half_width)
            x_max = min(0.999, word.x_center + half_width)
            start_bin = int(x_min * COLUMN_GRID_BINS)
            end_bin = int(x_max * COLUMN_GRID_BINS)
            for b in range(start_bin, end_bin + 1):
                if 0 <= b < COLUMN_GRID_BINS:
                    row_occupied[b] = True
        for b in range(COLUMN_GRID_BINS):
            if row_occupied[b]:
                occupied_row_count[b] += 1

    # Une bande est un "vrai" séparateur si elle est vide dans au moins
    # COLUMN_GAP_SUPPORT_RATIO des lignes (consensus), pas dans 100% d'entre elles.
    is_gap = [
        (occupied_row_count[b] / n_rows) <= (1 - COLUMN_GAP_SUPPORT_RATIO)
        for b in range(COLUMN_GRID_BINS)
    ]

    min_gap_bins = max(1, int(line_height * COLUMN_GAP_MIN_RATIO * COLUMN_GRID_BINS))

    # Fusionne les petits trous (espaces intra-cellule, ex. "GILBERT NOEL")
    # dans les zones occupées -- ne garde que les vrais séparateurs larges.
    merged = [not g for g in is_gap]  # True = occupé
    i = 0
    while i < COLUMN_GRID_BINS:
        if not merged[i]:
            j = i
            while j < COLUMN_GRID_BINS and not merged[j]:
                j += 1
            if (j - i) < min_gap_bins:
                for b in range(i, j):
                    merged[b] = True
            i = j
        else:
            i += 1

    segments: list[tuple[float, float]] = []
    i = 0
    while i < COLUMN_GRID_BINS:
        if merged[i]:
            j = i
            while j < COLUMN_GRID_BINS and merged[j]:
                j += 1
            segments.append((i / COLUMN_GRID_BINS, j / COLUMN_GRID_BINS))
            i = j
        else:
            i += 1

    return segments


def _is_table_like(rows: list[list[OcrWord]]) -> bool:
    if len(rows) < MIN_TABLE_ROWS:
        return False
    lengths = sorted(len(row) for row in rows)
    median_len = lengths[len(lengths) // 2]
    if median_len < 2:
        return False
    tolerance = max(3, median_len * 0.5)
    close_to_median = sum(1 for row in rows if abs(len(row) - median_len) <= tolerance)
    return close_to_median / len(rows) >= 0.6


def _assign_to_segments(row: list[OcrWord], segments: list[tuple[float, float]]) -> list[str]:
    cells = ["" for _ in segments]
    for word in row:
        closest_index = min(
            range(len(segments)),
            key=lambda i: abs(word.x_center - (segments[i][0] + segments[i][1]) / 2),
        )
        cells[closest_index] = f"{cells[closest_index]} {word.text}".strip()
    return cells


def _assign_confidences_to_segments(
    row: list[OcrWord], segments: list[tuple[float, float]]
) -> list[float]:
    """Confiance d'une cellule = confiance MINIMALE des mots qui la composent
    -- un seul mot peu fiable suffit à rendre toute la cellule suspecte
    (ex. "24715O" avec un seul caractère mal reconnu fausse toute la valeur)."""
    sums: list[list[float]] = [[] for _ in segments]
    for word in row:
        closest_index = min(
            range(len(segments)),
            key=lambda i: abs(word.x_center - (segments[i][0] + segments[i][1]) / 2),
        )
        sums[closest_index].append(word.confidence)
    return [min(c) if c else 1.0 for c in sums]


def build_tables_from_words(page_number: int, words: list[OcrWord]) -> list[ExtractedTable]:
    if not words:
        return []

    line_height = _estimate_line_height(words)
    row_tolerance = line_height * ROW_TOLERANCE_RATIO
    block_gap = line_height * BLOCK_GAP_RATIO

    rows = _group_words_into_rows(words, row_tolerance)
    blocks = _split_into_blocks(rows, block_gap)

    tables = []
    for block_rows in blocks:
        if not _is_table_like(block_rows):
            continue

        segments = _detect_column_segments(block_rows, line_height)
        if len(segments) < 2:
            continue

        table_rows = [_assign_to_segments(row, segments) for row in block_rows]
        confidence_rows = [_assign_confidences_to_segments(row, segments) for row in block_rows]
        tables.append(
            ExtractedTable(
                page_number=page_number,
                rows=table_rows,
                extraction_method=ExtractionMethod.GEOMETRIC_CLUSTERING,
                camelot_accuracy=0.0,
                cell_confidences=confidence_rows,
            )
        )
    return tables