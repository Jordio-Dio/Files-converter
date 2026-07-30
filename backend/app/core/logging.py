"""
Configuration du logging de l'application.

Un logging correct dès le départ évite beaucoup de douleur en production :
quand un utilisateur signale qu'un PDF a mal été converti, ce sont ces logs
qui permettront de comprendre quelle étape du pipeline a échoué.
"""

import logging
import sys

from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)