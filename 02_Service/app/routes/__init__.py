"""Routes du contrat `api.v1`, un fichier par module ; toutes branchées sous `/v1` dans `app/main.py`.

Chaque mandat ne remplit que son propre fichier de routes ; tant qu'une route n'est pas
implémentée, elle répond 501 `non_implemente` dans l'enveloppe d'erreur.
"""

from __future__ import annotations

from typing import Any

from app.erreurs import ErreurApi
from app.modeles import Erreur

# Codes de l'enveloppe d'erreur, par statut HTTP, tels que le contrat les documente.
CODES_ERREUR: dict[int, str] = {
    401: "cle_demo_invalide : l'en-tête X-Cle-Demo est absent ou incorrect.",
    404: "introuvable : la ressource demandée n'existe pas.",
    409: (
        "decision_manquante, version_non_tranchee ou constat_manquant : "
        "un geste du journaliste manque avant l'export."
    ),
    422: "validation : la requête ne respecte pas le contrat.",
    501: "non_implemente : route prévue au contrat, pas encore implémentée.",
}


REF_ERREUR = "#/components/schemas/Erreur"


def erreurs(*statuts: int, route_html: bool = False) -> dict[int | str, dict[str, Any]]:
    """Réponses d'erreur documentées d'une route, toutes dans l'enveloppe JSON `Erreur`.

    Pour une route qui rend du HTML, le schéma est posé en `application/json` par référence :
    sinon FastAPI documenterait l'erreur sous le type de la route.
    """
    if route_html:
        contenu = {"application/json": {"schema": {"$ref": REF_ERREUR}}}
        return {s: {"description": CODES_ERREUR[s], "content": contenu} for s in statuts}
    return {s: {"model": Erreur, "description": CODES_ERREUR[s]} for s in statuts}


def non_implemente(route: str) -> ErreurApi:
    """Erreur 501 d'une route du contrat pas encore implémentée."""
    return ErreurApi(
        "non_implemente", f"La route {route} est prévue au contrat api.v1, pas encore implémentée.", 501
    )
