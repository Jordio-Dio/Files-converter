"""
Point d'entrée de l'application FastAPI.

Ce fichier reste volontairement minimal : il assemble l'application et
enregistre les routes. Toute la logique métier vit ailleurs (application/,
domain/, infrastructure/) — c'est le principe central de la Clean Architecture.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging

setup_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de conversion intelligente PDF -> Excel",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Endpoint de santé, utile pour le monitoring et les plateformes
    d'hébergement gratuites qui vérifient que le service est up."""
    return {"status": "ok", "environment": settings.environment}