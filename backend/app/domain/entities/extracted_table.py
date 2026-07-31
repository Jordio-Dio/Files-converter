"""
Entité métier représentant un tableau extrait d'un document.

Ne dépend d'aucun outil technique (ni Camelot, ni pdfplumber) -- c'est le
rôle de la couche infrastructure/ de produire cet objet à partir d'un outil
concret. Si demain on change d'outil de détection, cette entité ne bouge pas.
"""

from dataclasses import dataclass, field
from enum import Enum


class ExtractionMethod(str, Enum):
    CAMELOT_LATTICE = "camelot_lattice"   # tableau avec bordures visibles
    CAMELOT_STREAM = "camelot_stream"     # tableau détecté par alignement (sans bordures)
    GEOMETRIC_CLUSTERING = "geometric_clustering"


@dataclass
class ExtractedTable:
    page_number: int
    rows: list[list[str]]                  # données brutes, ligne par ligne
    extraction_method: ExtractionMethod
    # Score natif renvoyé par Camelot (0 à 100), PAS encore le score de
    # confiance final du pipeline (celui-ci combinera plusieurs signaux,
    # voir la conception validée à l'étape "score de confiance").
    camelot_accuracy: float = field(default=0.0)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(self.rows[0]) if self.rows else 0