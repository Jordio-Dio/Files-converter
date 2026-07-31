"""
Extraction de texte par OCR sur les pages scannées, via docTR.

Conserve la position de chaque mot (bounding box normalisée), nécessaire
pour la reconstruction géométrique de tableaux (voir table_builder.py).
"""

import fitz
import cv2
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

from app.core.logging import get_logger
from app.domain.value_objects.ocr_result import OcrPageResult, OcrWord
from app.infrastructure.pdf.preprocessor import deskew_image, pdf_page_to_cv_image

logger = get_logger(__name__)

_predictor = None


def _get_predictor():
    global _predictor
    if _predictor is None:
        logger.info("Chargement du modèle docTR (peut être long la 1ère fois)...")
        _predictor = ocr_predictor(pretrained=True)
    return _predictor


def run_ocr_on_pages(document: fitz.Document, page_numbers: list[int]) -> list[OcrPageResult]:
    predictor = _get_predictor()

    preprocessed_bytes = []
    for page_num in page_numbers:
        page = document[page_num - 1]
        cv_image = pdf_page_to_cv_image(page)
        deskewed = deskew_image(cv_image)
        preprocessed_bytes.append(cv2.imencode(".png", deskewed)[1].tobytes())

    doctr_doc = DocumentFile.from_images(preprocessed_bytes)
    result = predictor(doctr_doc)

    page_results = []
    for i, page_result in enumerate(result.pages):
        words: list[OcrWord] = []
        for block in page_result.blocks:
            for line in block.lines:
                for word in line.words:
                    # geometry docTR = ((x_min, y_min), (x_max, y_max)), déjà normalisé 0-1
                    (x_min, y_min), (x_max, y_max) = word.geometry
                    words.append(
                        OcrWord(
                            text=word.value,
                            confidence=word.confidence,
                            x_center=(x_min + x_max) / 2,
                            y_center=(y_min + y_max) / 2,
                            height=y_max - y_min,
                            width=x_max - x_min,
                        )
                    )

        text = " ".join(w.text for w in words)
        confidences = [w.confidence for w in words]
        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        low_conf_ratio = (
            sum(1 for c in confidences if c < 0.5) / len(confidences) if confidences else 1.0
        )

        page_results.append(
            OcrPageResult(
                page_number=page_numbers[i],
                text=text,
                mean_confidence=mean_confidence,
                word_count=len(words),
                words=words,
                low_confidence_word_ratio=low_conf_ratio,
            )
        )
        logger.info(
            "Page %d OCR : %d mots, confiance moyenne %.2f",
            page_numbers[i], len(words), mean_confidence,
        )

    return page_results