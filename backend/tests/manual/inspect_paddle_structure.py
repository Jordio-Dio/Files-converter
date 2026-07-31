"""
Script d'INSPECTION uniquement -- pas encore le module final.
But : voir la forme exacte des résultats renvoyés par PP-StructureV3 sur ta
version installée, avant d'écrire le code d'extraction définitif. L'API de
PaddleOCR a changé plusieurs fois ces derniers mois, mieux vaut vérifier
que supposer.

Usage :
    python tests/manual/inspect_paddle_structure.py storage/uploads/mon_scan.pdf
"""

import sys

from paddleocr import PPStructureV3

from app.infrastructure.pdf.preprocessor import deskew_image, pdf_page_to_cv_image
from app.infrastructure.pdf.type_detector import classify_document
from app.infrastructure.pdf.validator import validate_pdf
from app.domain.value_objects.page_classification import PageType

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    with open(pdf_path, "rb") as f:
        document = validate_pdf(f.read())

    classifications = classify_document(document)
    scanned = [c.page_number for c in classifications if c.page_type == PageType.SCANNED_IMAGE]
    if not scanned:
        print("Aucune page scannée dans ce PDF.")
        sys.exit(0)

    page = document[scanned[0] - 1]
    image = deskew_image(pdf_page_to_cv_image(page))

    print("Chargement du pipeline PP-StructureV3 (peut être long)...")
    pipeline = PPStructureV3(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_formula_recognition=False,
        use_seal_recognition=False,
        use_chart_recognition=False
    )

    print("Analyse de la page en cours...")
    results = list(pipeline.predict(image))

    print(f"\nNombre de résultats renvoyés : {len(results)}")
    for i, res in enumerate(results):
        print(f"\n--- Résultat {i} ---")
        print(f"Type Python : {type(res)}")
        print(f"Clés/attributs disponibles : {dir(res)}")
        res.save_to_json(f"storage/outputs/paddle_inspection_{i}.json")
        print(f"-> Détail complet sauvegardé dans storage/outputs/paddle_inspection_{i}.json")