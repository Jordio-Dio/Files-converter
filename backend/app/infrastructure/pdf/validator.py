"""
Validation d'un fichier PDF avant tout traitement lourd.

But : rejeter vite et clairement les fichiers inexploitables (corrompus,
trop lourds, trop de pages) AVANT de dépenser du temps CPU ou des appels
API dessus. C'est la première ligne de défense du pipeline.
"""

import fitz  # PyMuPDF

from app.core.config import get_settings


class InvalidPdfError(Exception):
    """Levée quand le fichier n'est pas un PDF exploitable."""


def validate_pdf(file_bytes: bytes) -> fitz.Document:
    """Valide le fichier et retourne le document PyMuPDF ouvert s'il est valide.

    Lève InvalidPdfError avec un message explicite sinon.
    """
    settings = get_settings()

    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise InvalidPdfError(
            f"Fichier trop volumineux ({len(file_bytes) / 1_000_000:.1f} Mo, "
            f"max {settings.max_upload_size_mb} Mo)."
        )

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise InvalidPdfError("Le fichier n'est pas un PDF valide ou est corrompu.") from exc

    if document.page_count == 0:
        raise InvalidPdfError("Le PDF ne contient aucune page.")

    if document.page_count > settings.max_pages_per_pdf:
        raise InvalidPdfError(
            f"Trop de pages ({document.page_count}, max {settings.max_pages_per_pdf})."
        )

    return document