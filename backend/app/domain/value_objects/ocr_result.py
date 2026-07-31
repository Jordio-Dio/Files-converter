"""
Value Objects représentant le résultat d'une reconnaissance OCR.

Indépendants de docTR -- si on change de moteur OCR plus tard, ces objets
ne bougent pas, seule l'infrastructure change.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OcrWord:
    """Un mot reconnu, avec sa position normalisée (0 à 1) sur la page.
    Position normalisée = indépendante de la résolution de l'image,
    ce qui simplifie tous les calculs géométriques en aval."""
    text: str
    confidence: float
    x_center: float   # 0.0 = bord gauche, 1.0 = bord droit
    y_center: float    # 0.0 = haut, 1.0 = bas
    height: float   # hauteur normalisée du mot -- sert de référence pour
                     # calculer dynamiquement l'espacement entre lignes
    width: float   # nécessaire pour la détection de colonnes par zones vides


@dataclass(frozen=True)
class OcrPageResult:
    page_number: int
    text: str
    mean_confidence: float
    word_count: int
    words: list[OcrWord] = field(default_factory=list)
    low_confidence_word_ratio: float = field(default=0.0)