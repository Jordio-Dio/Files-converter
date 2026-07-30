"""
Configuration centralisée de l'application.

Toute variable qui change entre environnements (dev / prod) ou toute donnée
sensible (clés API) passe par ici, jamais en dur dans le code. Les valeurs
sont lues depuis un fichier .env (non versionné, voir .env.example).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Général ---
    app_name: str = "FILES-CONVERTER"
    environment: str = "development"  # development | staging | production
    debug: bool = True

    # --- Stockage local (V1 : disque local, évoluera vers S3-compatible plus tard) ---
    upload_dir: str = "storage/uploads"
    output_dir: str = "storage/outputs"
    max_upload_size_mb: int = 50
    max_pages_per_pdf: int = 200

    # --- Redis (file d'attente) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Mistral (LLM, utilisé UNIQUEMENT en fallback ciblé, jamais systématique) ---
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"

    # --- Seuils du pipeline (score de confiance) ---
    confidence_threshold_ok: float = 0.85
    confidence_threshold_llm_fallback: float = 0.60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique (mise en cache) des settings.
    Utiliser cette fonction partout dans le code plutôt que d'instancier
    Settings() directement, pour ne lire le .env qu'une seule fois."""
    return Settings()