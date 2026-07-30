"""
Value Objects représentant le résultat d'une reconnaissance OCR.

Indépendants de docTR -- si on change de moteur OCR plus tard (ex. PaddleOCR
en remplacement), ces objets ne bougent pas, seule l'infrastructure change.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OcrPageResult:
    page_number: int
    text: str                    # texte reconstruit, lignes séparées par \n
    mean_confidence: float       # moyenne des scores de confiance mot par mot (0 à 1)
    word_count: int
    low_confidence_word_ratio: float = field(default=0.0)  # signal utile pour le score global plus tard