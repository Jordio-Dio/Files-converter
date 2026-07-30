"""
Script manuel pour verifier validation + detection de type + extraction
de tableaux (branche PDF texte natif uniquement pour l'instant).

Usage :
    python -m tests.manual.test_pdf_detection storage/uploads/mon_fichier.pdf
"""

import sys

from app.domain.value_objects.page_classification import PageType
from app.infrastructure.pdf.type_detector import classify_document
from app.infrastructure.pdf.validator import InvalidPdfError, validate_pdf
from app.infrastructure.tables.camelot_extractor import extract_tables_from_native_pdf

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m tests.manual.test_pdf_detection <chemin_du_pdf>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "rb") as f:
        file_bytes = f.read()

    try:
        document = validate_pdf(file_bytes)
    except InvalidPdfError as e:
        print(f"❌ PDF invalide : {e}")
        sys.exit(1)

    print(f"✅ PDF valide — {document.page_count} page(s)\n")

    classifications = classify_document(document)
    has_native_pages = False
    for c in classifications:
        icon = "📄" if c.page_type == PageType.NATIVE_TEXT else "🖼️"
        print(f"{icon} Page {c.page_number}: {c.page_type.value} "
              f"({c.extracted_char_count} caracteres extraits)")
        if c.page_type == PageType.NATIVE_TEXT:
            has_native_pages = True

    if not has_native_pages:
        print("\n⚠️ Aucune page en texte natif -- rien a tester pour Camelot "
              "(ce PDF ira entierement vers l'OCR, module de l'etape suivante).")
        sys.exit(0)

    print("\n--- Extraction des tableaux (Camelot) ---\n")
    tables = extract_tables_from_native_pdf(path)

    if not tables:
        print("Aucun tableau detecte.")
    for i, table in enumerate(tables, start=1):
        print(f"Tableau {i} — page {table.page_number} — "
              f"{table.row_count} lignes x {table.column_count} colonnes — "
              f"methode: {table.extraction_method.value} — "
              f"precision Camelot: {table.camelot_accuracy:.1f}%")
        print("  Apercu (2 premieres lignes) :")
        for row in table.rows[:2]:
            print(f"    {row}")
        print()