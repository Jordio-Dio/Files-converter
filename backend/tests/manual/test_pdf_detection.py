"""
Script manuel pour verifier la validation et la detection du type de PDF.
Usage : python tests/manual/test_pdf_detection.py storage/uploads/mon_fichier.pdf
"""
import sys
from app.infrastructure.pdf.validator import validate_pdf, InvalidPdfError
from app.infrastructure.pdf.type_detector import classify_document

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tests/manual/test_pdf_detection.py <chemin_du_pdf>")
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
    for c in classifications:
        icon = "📄" if c.page_type.value == "native_text" else "🖼️"
        print(f"{icon} Page {c.page_number} : {c.page_type.value} ({c.extracted_char_count} caracteres extraits)")