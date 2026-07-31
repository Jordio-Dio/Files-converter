"""Value Object représentant le score de confiance global d'un tableau extrait."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TableConfidenceScore:
    mean_word_confidence: float       # moyenne des confiances OCR (0-1)
    low_confidence_cell_ratio: float  # part des cellules sous le seuil (0-1)
    numeric_consistency_ratio: float  # cohérence des colonnes numériques (0-1)
    overall_score: float              # score composite final (0-1)

    @property
    def is_reliable(self) -> bool:
        return self.overall_score >= 0.85

    @property
    def needs_llm_review(self) -> bool:
        return 0.60 <= self.overall_score < 0.85

    @property
    def needs_ocr_fallback(self) -> bool:
        return self.overall_score < 0.60