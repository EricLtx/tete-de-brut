"""Clé de démonstration : protège les crédits Oriane d'un appel de curiosité (pas d'un attaquant)."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.erreurs import mode_courant, reponse_erreur

EN_TETE_CLE_DEMO = "X-Cle-Demo"
METHODES_PROTEGEES = {"POST", "PATCH", "PUT", "DELETE"}


async def exiger_cle_demo(request: Request, suite: Callable[[Request], Awaitable[Response]]) -> Response:
    """Intergiciel : si `CLE_DEMO` est renseignée, exige `X-Cle-Demo` sur les écritures sous `/v1`."""
    config = request.app.state.config
    if config.cle_demo and request.method in METHODES_PROTEGEES and request.url.path.startswith("/v1"):
        fournie = request.headers.get(EN_TETE_CLE_DEMO, "")
        if not secrets.compare_digest(fournie.encode(), config.cle_demo.encode()):
            return reponse_erreur(
                "cle_demo_invalide",
                f"L'en-tête {EN_TETE_CLE_DEMO} est absent ou incorrect.",
                401,
                mode_courant(request),
            )
    return await suite(request)
