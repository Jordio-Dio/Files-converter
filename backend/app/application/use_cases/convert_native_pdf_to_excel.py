"""
Cas d'usage : convertir un PDF texte natif en fichier Excel.

Version V1 -- branche simple uniquement (pas d'OCR, pas de LLM ici, ce sera
ajouté aux étapes suivantes). Ce fichier orchestre les couches infrastructure
sans jamais contenir lui-même de logique technique (pas d'appel direct à
fitz ou camelot) -- il délègue tout aux modules déjà créés.
"""

from dataclasses import dataclass

from app.core.logging import get_logger
from app.domain.value_objects.page_classification import PageType
from app.infrastructure.excel.excel_writer import write_tables_to_excel
from app.infrastructure.pdf.type_detector import classify_document
from app.infrastructure.pdf.validator import validate_pdf
from app.infrastructure.tables.camelot_extractor import extract_tables_from_native_pdf

logger = get_logger(__name__)


class NoNativeTextPageError(Exception):
    """Levée quand le PDF n'a aucune page en texte natif -- il doit passer
    par la branche OCR (module de l'étape suivante), pas par ce cas d'usage."""


class NoTableFoundError(Exception):
    """Levée quand aucun tableau n'a été détecté sur les pages natives."""


@dataclass
class ConversionResult:
    output_path: str
    table_count: int
    page_count: int


def convert_native_pdf_to_excel(pdf_path: str, output_path: str) -> ConversionResult:
    logger.info("Début de conversion : %s", pdf_path)

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    document = validate_pdf(file_bytes)
    classifications = classify_document(document)

    native_pages = [c for c in classifications if c.page_type == PageType.NATIVE_TEXT]
    if not native_pages:
        raise NoNativeTextPageError(
            "Ce PDF ne contient aucune page en texte natif -- "
            "il doit être traité par la branche OCR."
        )

    tables = extract_tables_from_native_pdf(pdf_path)
    if not tables:
        raise NoTableFoundError("Aucun tableau détecté sur les pages en texte natif.")

    write_tables_to_excel(tables, output_path)
    logger.info("Excel généré : %s (%d tableau(x))", output_path, len(tables))

    return ConversionResult(
        output_path=output_path,
        table_count=len(tables),
        page_count=document.page_count,
    )