"""
Extraction de texte par OCR sur les pages scannées, via docTR.
Ne s'applique qu'aux pages déjà identifiées comme PageType.SCANNED_IMAGE par le module de classification.
"""
import fitz
import cv2
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

from app.core.logging import get_logger
from app.domain.value_objects.ocr_result import OcrPageResult
from app.infrastructure.pdf.preprocessor import deskew_image, pdf_page_to_cv_image

logger = get_logger(__name__)

_predictor = None


def _get_predictor():
    global _predictor
    if _predictor is None:
        logger.info("Chargement du modèle docTR...")
        _predictor = ocr_predictor(pretrained=True)
    return _predictor


def run_ocr_on_pages(document: fitz.Document, page_numbers: list[int]) -> list[OcrPageResult]:
    """page_numbers : numéros de page à partir de 1."""
    predictor = _get_predictor()
    preprocessed_bytes = []

    for page_num in page_numbers:
        page = document[page_num - 1]
        cv_image = pdf_page_to_cv_image(page)
        deskewed = deskew_image(cv_image)
        
        # Encodage en PNG (bytes) pour compatibilité avec docTR
        success, encoded_img = cv2.imencode(".png", deskewed)
        if success:
            preprocessed_bytes.append(encoded_img.tobytes())

    # docTR accepte une liste d'images sous forme de bytes
    doctr_doc = DocumentFile.from_images(preprocessed_bytes)
    result = predictor(doctr_doc)

    page_results = []
    for i, page_result in enumerate(result.pages):
        words_text = []
        confidences = []
        for block in page_result.blocks:
            for line in block.lines:
                for word in line.words:
                    words_text.append(word.value)
                    confidences.append(word.confidence)

        text = " ".join(words_text)
        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        low_conf_ratio = (
            sum(1 for c in confidences if c < 0.5) / len(confidences)
            if confidences
            else 1.0
        )

        page_results.append(
            OcrPageResult(
                page_number=page_numbers[i],
                text=text,
                mean_confidence=mean_confidence,
                word_count=len(words_text),
                low_confidence_word_ratio=low_conf_ratio,
            )
        )
        logger.info(
            "Page %d OCR : %d mots, confiance moyenne %.2f",
            page_numbers[i],
            len(words_text),
            mean_confidence,
        )

    return page_results