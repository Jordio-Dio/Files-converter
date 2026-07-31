"""
Script manuel : test de la branche OCR (docTR) sur les pages scannées
d'un PDF. N'écrit pas encore d'Excel -- juste le texte extrait et le
score de confiance, pour valider ce module isolément avant de le
brancher au reste du pipeline.

Usage :
    python tests/manual/test_ocr.py storage/uploads/mon_fichier_scanne.pdf
"""

import sys

from app.domain.value_objects.page_classification import PageType
from app.infrastructure.ocr.doctr_extractor import run_ocr_on_pages
from app.infrastructure.pdf.type_detector import classify_document
from app.infrastructure.pdf.validator import InvalidPdfError, validate_pdf
from app.infrastructure.tables.geometric_table_builder import build_tables_from_words


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tests/manual/test_ocr.py <chemin_du_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    try:
        document = validate_pdf(file_bytes)
    except InvalidPdfError as e:
        print(f"❌ PDF invalide : {e}")
        sys.exit(1)

    classifications = classify_document(document)
    scanned_page_numbers = [
        c.page_number for c in classifications if c.page_type == PageType.SCANNED_IMAGE
    ]

    if not scanned_page_numbers:
        print("⚠️  Aucune page scannée détectée -- ce PDF relève de la branche "
              "texte natif (étape 8), pas de cette branche OCR.")
        sys.exit(0)

    print(f"🖼️  {len(scanned_page_numbers)} page(s) scannée(s) détectée(s) : "
          f"{scanned_page_numbers}\n")
    print("--- Lancement de l'OCR (peut prendre un peu de temps) ---\n")

    results = run_ocr_on_pages(document, scanned_page_numbers)

    for r in results:
        confidence_icon = "✅" if r.mean_confidence >= 0.85 else "⚠️"
        print(f"{confidence_icon} Page {r.page_number} — {r.word_count} mots — "
              f"confiance moyenne : {r.mean_confidence:.2f} — "
              f"mots peu fiables : {r.low_confidence_word_ratio * 100:.0f}%")
        print(f"   Aperçu texte : {r.text[:200]}...\n")


    from app.infrastructure.quality.cell_corrector import post_process_table
    from app.infrastructure.quality.confidence_scorer import find_flagged_cells, score_table
    from app.infrastructure.tables.geometric_table_builder import build_tables_from_words

    print("\n--- Reconstruction + score de confiance ---\n")
    for r in results:
        tables = build_tables_from_words(r.page_number, r.words)
        if not tables:
            print(f"Page {r.page_number} : aucun tableau détecté.")
            continue

        for i, table in enumerate(tables, start=1):
            score = score_table(table)
            flagged = find_flagged_cells(table)
            corrected_table, still_flagged = post_process_table(table, flagged)

            print(f"Page {r.page_number}, tableau {i} : {table.row_count} lignes x "
                  f"{table.column_count} colonnes")
            print(f"   Score global : {score.overall_score:.2f} "
                  f"(fiable={score.is_reliable}, revue LLM={score.needs_llm_review}, "
                  f"fallback OCR={score.needs_ocr_fallback})")
            print(f"   Confiance OCR moyenne : {score.mean_word_confidence:.2f}")
            print(f"   Cellules peu fiables détectées : {len(flagged)}")
            print(f"   Corrigées automatiquement : {len(flagged) - len(still_flagged)}")
            print(f"   Toujours suspectes après correction : {len(still_flagged)}")
            print("   Aperçu (3 premières lignes, après correction) :")
            for row in corrected_table.rows[:3]:
                print(f"      {row}")
            print()