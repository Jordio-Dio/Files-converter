import sys

from app.domain.value_objects.page_classification import PageType
from app.infrastructure.ocr.doctr_extractor import run_ocr_on_pages
from app.infrastructure.pdf.type_detector import classify_document
from app.infrastructure.pdf.validator import validate_pdf
from app.infrastructure.tables.geometric_table_builder import (
    _estimate_line_height,
    _group_words_into_rows,
    _split_into_blocks,
    _is_table_like,
    ROW_TOLERANCE_RATIO,
    BLOCK_GAP_RATIO,
)

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    with open(pdf_path, "rb") as f:
        document = validate_pdf(f.read())

    classifications = classify_document(document)
    scanned = [c.page_number for c in classifications if c.page_type == PageType.SCANNED_IMAGE]
    results = run_ocr_on_pages(document, scanned)

    for r in results:
        line_height = _estimate_line_height(r.words)
        row_tolerance = line_height * ROW_TOLERANCE_RATIO
        block_gap = line_height * BLOCK_GAP_RATIO
        print(f"Page {r.page_number} : hauteur de ligne médiane estimée = {line_height:.4f}")
        print(f"   -> row_tolerance = {row_tolerance:.4f} / block_gap = {block_gap:.4f}\n")

        rows = _group_words_into_rows(r.words, row_tolerance)
        print(f"{len(rows)} lignes détectées au total\n")

        blocks = _split_into_blocks(rows, block_gap)
        print(f"-> {len(blocks)} bloc(s) après segmentation verticale\n")

        for i, block in enumerate(blocks):
            lengths = [len(row) for row in block]
            status = "✅ TABLEAU" if _is_table_like(block) else "❌ rejeté"
            print(f"Bloc {i} : {len(block)} lignes -- {status} -- longueurs : {lengths}")