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
    sorted_words = sorted(words, key=lambda w: w.y_center)
    rows: list[list[OcrWord]] = []
    for word in sorted_words:
        if rows:
            row_anchor = sum(w.y_center for w in rows[-1]) / len(rows[-1])
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


def _detect_column_segments(
    rows: list[list[OcrWord]], line_height: float
) -> list[tuple[float, float]]:
    coverage = [False] * COLUMN_GRID_BINS

    for row in rows:
        for word in row:
            # On utilise 50% de la largeur du mot (son cœur) pour éviter
            # qu'un mot sur-estimé ne bave sur la colonne voisine
            effective_half_width = max((word.width * 0.5) / 2, 0.001)
            x_min = max(0.0, word.x_center - effective_half_width)
            x_max = min(0.999, word.x_center + effective_half_width)
            start_bin = int(x_min * COLUMN_GRID_BINS)
            end_bin = int(x_max * COLUMN_GRID_BINS)
            for b in range(start_bin, end_bin + 1):
                if 0 <= b < COLUMN_GRID_BINS:
                    coverage[b] = True

    # Seuil dynamique adapté à la taille relative de la ligne
    min_gap_bins = max(1, int(line_height * COLUMN_GAP_MIN_RATIO * COLUMN_GRID_BINS))

    merged = coverage[:]
    i = 0
    while i < COLUMN_GRID_BINS:
        if not merged[i]:
            j = i
            while j < COLUMN_GRID_BINS and not merged[j]:
                j += 1
            gap_length = j - i
            if gap_length < min_gap_bins:
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
        # Colonne = segment dont le CENTRE est le plus proche du mot --
        # robuste même si le mot déborde légèrement sur un segment voisin.
        closest_index = min(
            range(len(segments)),
            key=lambda i: abs(word.x_center - (segments[i][0] + segments[i][1]) / 2),
        )
        cells[closest_index] = f"{cells[closest_index]} {word.text}".strip()
    return cells


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
        tables.append(
            ExtractedTable(
                page_number=page_number,
                rows=table_rows,
                extraction_method=ExtractionMethod.GEOMETRIC_CLUSTERING,
                camelot_accuracy=0.0,
            )
        )
    return tables