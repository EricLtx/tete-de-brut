"""Radar des récits (rempli par S05)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.erreurs import ErreurApi
from app.modeles import Radar, Recit
from app.recits import calculer_radar, calculer_recits
from app.routes import erreurs

routeur = APIRouter(tags=["radar"])


@routeur.get(
    "/radar",
    response_model=Radar,
    summary="Radar des récits : récits, mesures, requête en clair, mode et date du calcul",
    responses=erreurs(501),
)
async def lire_radar(request: Request) -> Radar:
    """Un récit par phrase surveillée, avec ses mesures (méthode et fenêtre) et ce qui n'a pas été cherché."""
    config = request.app.state.config
    return calculer_radar(config.mode, config.raison)


@routeur.get(
    "/recits/{id}",
    response_model=Recit,
    summary="Un récit, ses vidéos et ses mesures",
    responses=erreurs(404, 422, 501),
)
async def lire_recit(id: str, request: Request) -> Recit:
    """Récit `recit.v1` : phrase surveillée, requête en clair, plus ancienne version, non cherché."""
    recits, _ = calculer_recits(request.app.state.config.mode)
    for recit in recits:
        if recit.identifiant == id:
            return recit
    raise ErreurApi("introuvable", f"Aucun récit « {id} » dans le radar.", 404)
