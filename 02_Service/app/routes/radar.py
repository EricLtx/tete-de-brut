"""Radar des récits (rempli par S05)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modeles import Radar, Recit
from app.routes import erreurs, non_implemente

routeur = APIRouter(tags=["radar"])


@routeur.get(
    "/radar",
    response_model=Radar,
    summary="Radar des récits : récits, mesures, requête en clair, mode et date du calcul",
    responses=erreurs(501),
)
async def lire_radar() -> Radar:
    """Un récit par phrase surveillée, avec ses mesures (méthode et fenêtre) et ce qui n'a pas été cherché."""
    raise non_implemente("GET /v1/radar")


@routeur.get(
    "/recits/{id}",
    response_model=Recit,
    summary="Un récit, ses vidéos et ses mesures",
    responses=erreurs(404, 422, 501),
)
async def lire_recit(id: str) -> Recit:
    """Récit `recit.v1` : phrase surveillée, requête en clair, plus ancienne version, non cherché."""
    raise non_implemente("GET /v1/recits/{id}")
