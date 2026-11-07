"""Barre d'état, journal des appels et actualisation du radar (rempli par S04)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.modeles import Etat, Journal, Radar
from app.routes import erreurs, non_implemente

routeur = APIRouter(tags=["état"])


@routeur.get(
    "/etat",
    response_model=Etat,
    summary="État du service : mode, raison, crédits du jour, version et contrat",
    responses=erreurs(501),
)
async def lire_etat() -> Etat:
    """Mode (`direct` ou `enregistre`) et sa raison, date du cas rejoué, crédits du jour sur plafond."""
    raise non_implemente("GET /v1/etat")


@routeur.get(
    "/journal",
    response_model=Journal,
    summary="Journal des appels, le plus récent d'abord",
    responses=erreurs(422, 501),
)
async def lire_journal(
    limite: int = Query(default=100, ge=1, le=1000, description="Nombre de lignes rendues."),
) -> Journal:
    """Chaque appel Oriane et chaque geste, sans réponse brute ni clé."""
    raise non_implemente("GET /v1/journal")


@routeur.post(
    "/radar/actualiser",
    response_model=Radar,
    summary="Actualiser le radar par une requête Oriane en direct",
    responses=erreurs(401, 501),
)
async def actualiser_radar() -> Radar:
    """Une requête Oriane en direct (coût affiché avant le geste) ; bascule en mode enregistré si besoin."""
    raise non_implemente("POST /v1/radar/actualiser")
