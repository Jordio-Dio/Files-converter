"""
Value Objects liés à la classification d'une page de document.

Ces objets représentent un concept métier ("cette page est scannée ou non")
et ne dépendent d'aucun outil technique — PyMuPDF n'est jamais importé ici.
"""

from dataclasses import dataclass
from enum import Enum


class PageType(str, Enum):
    NATIVE_TEXT = "native_text"       # Texte sélectionnable, extraction directe possible
    SCANNED_IMAGE = "scanned_image"   # Aucun texte exploitable -> passera par l'OCR


@dataclass(frozen=True)
class PageClassification:
    """Résultat de la classification d'une page."""
    page_number: int          # numérotation à partir de 1 (plus lisible pour l'utilisateur)
    page_type: PageType
    extracted_char_count: int  # signal brut, réutilisé plus tard dans le score de confiance