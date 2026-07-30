"""
Détection automatique du type de chaque page (texte natif vs scannée).

Heuristique volontairement simple et gratuite (voir conception validée) :
si l'extraction de texte native de la page renvoie quasi rien, la page est
considérée comme une image à envoyer vers l'OCR. Pas de modèle IA ici --
inutile de payer en temps ou en argent pour un problème déjà résolu par
une règle simple.
"""

import fitz  # PyMuPDF

from app.domain.value_objects.page_classification import PageClassification, PageType

# Seuil empirique : en dessous de ce nombre de caractères extraits,
# on considère qu'il n'y a pas de couche texte exploitable.
MIN_CHAR_COUNT_FOR_NATIVE_TEXT = 20


def classify_page(page: fitz.Page) -> PageClassification:
    text = page.get_text().strip()
    char_count = len(text)

    page_type = (
        PageType.NATIVE_TEXT
        if char_count >= MIN_CHAR_COUNT_FOR_NATIVE_TEXT
        else PageType.SCANNED_IMAGE
    )

    return PageClassification(
        page_number=page.number + 1,  # PyMuPDF indexe à partir de 0
        page_type=page_type,
        extracted_char_count=char_count,
    )


def classify_document(document: fitz.Document) -> list[PageClassification]:
    """Classifie chaque page du document, un par un."""
    return [classify_page(page) for page in document]