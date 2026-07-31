"""
Client Mistral avec retry/backoff automatique.

Le tier gratuit "Experiment" est rate-limité (pas de coût, mais un nombre
de requêtes par minute plafonné) -- une erreur 429 est donc un événement
NORMAL en développement, pas une panne. On retente avec un délai croissant
plutôt que d'abandonner à la première erreur.
"""

import json
import time

from mistralai.client.sdk import Mistral

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 3


def call_mistral_json(system_prompt: str, user_prompt: str) -> dict:
    """Appelle Mistral en mode JSON forcé, avec retry/backoff sur rate-limit.
    Retourne le JSON déjà parsé (dict), ou {} si l'appel échoue définitivement
    -- volontairement silencieux en échec : le pipeline doit continuer avec
    les cellules non corrigées plutôt que de planter tout le job."""
    settings = get_settings()
    client = Mistral(api_key=settings.mistral_api_key)

    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.complete(
                model=settings.mistral_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,  # déterministe -- on veut une correction, pas de créativité
            )
            raw_content = response.choices[0].message.content
            return json.loads(raw_content)

        except Exception as exc:
            is_rate_limit = "429" in str(exc) or "rate limit" in str(exc).lower()
            if is_rate_limit and attempt < MAX_RETRIES:
                logger.warning(
                    "Rate limit Mistral (tentative %d/%d), attente %ds...",
                    attempt, MAX_RETRIES, backoff,
                )
                time.sleep(backoff)
                backoff *= 2
                continue
            logger.error("Échec de l'appel Mistral : %s", exc)
            return {}

    return {}